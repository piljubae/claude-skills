---
name: design-validate
description: Compose 마이그레이션 디자인 검증 — origin/develop|production|Figma 기준으로 Compose 코드의 시각적 차이를 자동 분석·수정
argument-hint: <ScreenName> [--before=develop|production|figma:<url>] [--package=<appId>] [--build-cmd=<cmd>] [--screenshot]
---

# Design Validate Skill

Compose 마이그레이션 후 시각적 차이를 자동으로 찾아 수정한다.

**Announce at start:** "I'm using the design-validate skill."

---

## 사용법

```
/design-validate <ScreenName> [--before=develop|production|figma:<url>] [--package=<appId>] [--build-cmd=<cmd>] [--screenshot]
```

**예시:**
```
/design-validate ListProfileActivity
/design-validate ListProfileActivity --before=production
/design-validate ListProfileActivity --before=figma:https://figma.com/design/xxx --screenshot
/design-validate ListProfileActivity --package=com.example.app.debug --build-cmd="./gradlew :app:compileDebugKotlin"
```

---

## Step 0: 사전 준비

### 0-1. 인자 파싱

arguments에서 추출:
- `SCREEN_NAME` — 첫 번째 positional 인자 (예: `ListProfileActivity`)
- `BEFORE_MODE` — `--before=` 값 (기본값: `develop`)
  - `develop` — origin/develop 코드 분석
  - `production` — production 앱 스크린샷 + 코드 분석
  - `figma:<url>` — Figma 디자인
- `USE_SCREENSHOT` — `--screenshot` 플래그 존재 여부 (true/false)
- `PACKAGE_OVERRIDE` — `--package=` 값 (없으면 자동 탐지)
- `BUILD_CMD_OVERRIDE` — `--build-cmd=` 값 (없으면 자동 탐지)

### 0-2. Upstream remote 탐지

```bash
git remote -v
```

- `upstream` remote가 있으면 → `UPSTREAM_REMOTE=upstream`
- `upstream` 없고 `origin`만 있으면 → `UPSTREAM_REMOTE=origin`
- 그 외: 사용자에게 "어느 remote가 upstream인가요?" 확인

### 0-3. 앱 패키지명 탐지

`PACKAGE_OVERRIDE`가 없으면 프로젝트에서 자동 탐지:

```bash
# 방법 1: app/build.gradle.kts
grep -r "applicationId" app/build.gradle* 2>/dev/null | head -5

# 방법 2: AndroidManifest.xml
grep "package=" app/src/main/AndroidManifest.xml 2>/dev/null | head -3
```

탐지된 applicationId에 `.debug` 또는 `.beta` suffix를 추가하여 `APP_PACKAGE` 결정.
탐지 불가 시 사용자에게 확인:
```
앱 패키지명을 알려주세요 (예: com.example.app.debug):
```

### 0-4. 빌드 검증 명령 탐지

`BUILD_CMD_OVERRIDE`가 없으면 프로젝트에서 자동 탐지:

```bash
# gradlew 존재 확인
ls gradlew 2>/dev/null

# 사용 가능한 compile 태스크 확인 (상위 5개)
./gradlew tasks --all 2>/dev/null | grep -iE "compile.*kotlin|compile.*debug" | head -10
```

결과 기반으로 `BUILD_CMD` 결정. 탐지 불가 시 `./gradlew assembleDebug` 사용.

### 0-5. 작업 폴더 설정

```bash
BRANCH=$(git branch --show-current)
WORK_DIR="docs/plans/${BRANCH}"
mkdir -p "${WORK_DIR}"
```

모든 산출물(report, 스크린샷, 스크립트)은 `${WORK_DIR}/`에 저장.

### 0-6. production fallback 처리

`--before=production`인 경우:
```bash
adb devices | grep -v "List of devices" | grep "device$"
```
- 기기 연결 확인 후 앱 설치 여부 확인:
  ```bash
  adb shell pm list packages | grep "${APP_PACKAGE_PROD}$"
  ```
- production 앱 없으면:
  ```
  ⚠️  production 앱이 설치되어 있지 않습니다.
     before 기준을 origin/develop 코드 분석으로 대체합니다.
  ```
  → `BEFORE_MODE=develop`으로 변경

---

## Step 1: Code Analyzer 에이전트 호출

`compose-design-analyzer` 에이전트를 호출한다.

```
Agent tool:
  subagent_type: "compose-design-analyzer"
  prompt: |
    ## 분석 대상
    Screen: {SCREEN_NAME}
    Before 기준: {BEFORE_MODE}
    Upstream remote: {UPSTREAM_REMOTE}
    작업 폴더: {WORK_DIR}

    ## 작업
    {SCREEN_NAME}의 {UPSTREAM_REMOTE}/develop 코드와 현재 feature 브랜치 Compose 코드를 비교하여
    {WORK_DIR}/design-diff-report.md 를 생성하라.

    Figma URL (before=figma인 경우): {FIGMA_URL or "없음"}
```

에이전트 완료 후 `{WORK_DIR}/design-diff-report.md` 존재 확인.

---

## Step 2: [--screenshot] Before 스크린샷

`USE_SCREENSHOT=true`인 경우에만 실행.

`compose-screenshot-writer` 에이전트를 호출한다.

```
Agent tool:
  subagent_type: "compose-screenshot-writer"
  prompt: |
    ## 대상
    Screen: {SCREEN_NAME}
    앱 패키지 (debug/beta): {APP_PACKAGE}
    Production 패키지: {APP_PACKAGE_PROD} (before=production인 경우만)
    작업 폴더: {WORK_DIR}
    캡처 모드: before

    ## 작업
    1. {WORK_DIR}/capture_{SCREEN_NAME}.py 생성 (없으면)
    2. before.png 캡처 → {WORK_DIR}/before.png
    3. before=production이면 before_production.png도 캡처 → {WORK_DIR}/before_production.png
```

---

## Step 3: Fix Applier 에이전트 호출

`compose-design-fixer` 에이전트를 호출한다.

```
Agent tool:
  subagent_type: "compose-design-fixer"
  prompt: |
    ## 입력
    design-diff-report: {WORK_DIR}/design-diff-report.md
    작업 폴더: {WORK_DIR}
    빌드 검증 명령: {BUILD_CMD}

    ## 작업
    design-diff-report.md의 "수정 필요" 항목을 모두 수정하라.
    KPDS 근사치 사용 시 {WORK_DIR}/non-kpds-values.md에 기록하라.
    완료 후 빌드 확인: {BUILD_CMD}
```

---

## Step 4: [--screenshot] After 스크린샷

`USE_SCREENSHOT=true`인 경우에만 실행.

```bash
# 프로젝트에 맞는 install 명령 사용
# 예: ./gradlew :app:installDebug 또는 ./gradlew :app:installBetaDebug
```

설치 후 `compose-screenshot-writer` 에이전트 재호출:

```
Agent tool:
  subagent_type: "compose-screenshot-writer"
  prompt: |
    ## 대상
    Screen: {SCREEN_NAME}
    앱 패키지: {APP_PACKAGE}
    작업 폴더: {WORK_DIR}
    캡처 모드: after
    스크립트 경로: {WORK_DIR}/capture_{SCREEN_NAME}.py

    ## 작업
    after.png 캡처 → {WORK_DIR}/after.png
```

---

## Step 5: 완료 요약

```
✅ design-validate 완료

📁 {WORK_DIR}/
  ├── design-diff-report.md    (분석 결과)
  ├── non-kpds-values.md       (KPDS 근사치 목록)
  ├── before.png               (--screenshot 시)
  ├── after.png                (--screenshot 시)
  └── capture_{SCREEN}.py      (--screenshot 시)

📋 수정된 항목: N개
⚠️  KPDS 근사치 사용: M개 (non-kpds-values.md 참고)

💡 PR 생성 시 스크린샷 첨부: /create-pr
```

---

## 에러 처리

| 상황 | 처리 |
|------|------|
| SCREEN_NAME 없음 | "사용법: /design-validate <ScreenName>" 출력 후 종료 |
| upstream remote 탐지 실패 | 사용자에게 remote 이름 확인 |
| 패키지명 탐지 실패 | 사용자에게 직접 입력 요청 |
| production 앱 없음 | develop으로 fallback + 알림 |
| 빌드 실패 | 에러 출력 후 중단, Fix Applier가 수정하지 않은 상태로 보존 |
| Figma URL 접근 실패 | 사용자에게 URL 재확인 요청 |
