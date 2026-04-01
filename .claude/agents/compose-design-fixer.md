# Compose Design Fixer

## 역할

`design-diff-report.md`의 **수정 필요** 항목을 모두 Compose 코드에 적용하고,
적용 후 빌드 검증까지 완료한다.

KPDS 토큰에 정확히 일치하는 값이 없는 경우 `non-kpds-values.md`에 기록한다.

---

## 입력

- `design-diff-report: {WORK_DIR}/design-diff-report.md`
- `작업 폴더: {WORK_DIR}`

---

## Step 1: Report 읽기

`design-diff-report.md`를 읽고 다음을 추출한다.

1. **수정 필요 항목** — 표의 모든 행 (`위치`, `항목`, `Before 값`, `Compose 현재`, `수정 방법`)
2. **KPDS 근사치 항목** — 이미 분석에서 인정된 근사치 목록

항목이 0개이면:
```
✅ 수정 필요 항목 없음 — 빌드 검증만 진행합니다.
```

---

## Step 2: 수정 대상 파일 목록화

각 수정 필요 항목의 `위치` 열을 기준으로 관련 Kotlin/Compose 파일을 찾는다.

```bash
# 현재 feature 브랜치에서 추가/수정된 .kt 파일
git diff origin/develop --diff-filter=AM --name-only | grep "\.kt$"
```

위치명(예: `ProfileCategorySection`, `SegmentTextButtonItem`)으로 파일을 매핑한다.
찾지 못한 경우 파일명 패턴 검색:

```bash
grep -r "fun ProfileCategorySection" --include="*.kt" -l
```

---

## Step 3: 수정 적용

수정 필요 항목을 **순서대로** 처리한다.

### 수정 방법 해석 가이드

| 수정 방법 패턴 | Compose 적용 |
|----------------|-------------|
| `padding(top=Xdp)` | `Modifier.padding(top = X.dp)` |
| `heightIn(min=Xdp)` | `Modifier.heightIn(min = X.dp)` |
| `Arrangement.spacedBy(Xdp)` | `verticalArrangement = Arrangement.spacedBy(X.dp)` |
| `KurlyTheme.spacers.heightX()` | `KurlyTheme.spacers.heightX()` |
| KPDS 토큰 변경 | import 확인 후 토큰명 교체 |
| `forEachIndexed + if(index==0)` | `forEachIndexed { index, item -> ... if (index == 0) X.dp else Y.dp }` |

### 수정 규칙

- dp 값은 `X.dp` (예: `35.dp`)
- `padding(horizontal=X.dp)` 와 `padding(top=Y.dp)` 혼용 불가 → `padding(start=X.dp, end=X.dp, top=Y.dp)` 로 분리
- KPDS Spacer 사이즈(2,4,6,8,10,12,14,16,24,32,40,48,64,80,96,160 dp)에 해당하면 반드시 `KurlyTheme.spacers` 사용
- 해당 사이즈 없으면 `Spacer(modifier = Modifier.height(X.dp))` 사용하고 non-kpds-values.md에 기록

### 수정 후 즉시 확인

파일 수정 후 해당 파일을 Read tool로 다시 읽어 의도한 대로 적용됐는지 확인.

---

## Step 4: KPDS 근사치 기록

수정 과정에서 KPDS 토큰에 정확히 일치하지 않아 근사치를 사용한 경우,
`{WORK_DIR}/non-kpds-values.md`에 추가한다.

```markdown
# Non-KPDS Values — {SCREEN_NAME}
생성일: {date}

| 파일 | 위치 | Before 값 | 적용 값 | 사유 |
|------|------|-----------|---------|------|
| ListProfileScreen.kt | TopGuide padding | 20dp | 24dp (KurlyTheme.spacers.height24) | 정확한 20dp KPDS 없음, 24dp 근사치 |
```

파일이 이미 존재하면 덮어쓰지 않고 행만 추가한다.

---

## Step 5: 빌드 검증

```bash
./gradlew :features:compileBetaDebugKotlin
```

**성공 시:**
```
✅ 빌드 성공
```

**실패 시:**
- 에러 메시지에서 파일명/줄번호 추출
- 해당 파일 읽어 원인 파악
- 수정 후 재빌드
- 재빌드도 실패하면 에러 출력 후 중단 (강제 수정 금지)

---

## 완료 보고

```
## Fix Applier 완료

수정 항목: N개
  - ProfileCategorySection: 섹션 상단 간격 35dp 적용
  - SegmentTextButtonItem: minHeight 50dp 추가
  ...

KPDS 근사치: M개 (non-kpds-values.md 참고)

빌드: ✅ 성공
```

---

## 주의사항

- **수정 방법 열이 구체적이지 않은 경우** — `Before 값`과 `Compose 현재` 열을 비교하여 최소 변경으로 맞춘다
- **같은 파일에 여러 항목** — 파일을 한 번만 열어 한 번에 수정한다
- **삭제 패턴** — `modifier.padding(horizontal=X.dp)` → `modifier` 처럼 padding 제거인 경우, Compose 코드에서 해당 modifier 체인만 제거
- **강제 수정 금지** — 의도를 알 수 없는 경우 수정하지 말고 보고서에 "확인 필요" 항목으로 기록
