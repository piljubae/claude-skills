---
name: feature-plan
description: Jira 티켓 기반 피처 개발 전체 플랜 생성 — 문서 수집 → PRD 정리 → 코드 영향 분석 → 이벤트 Delta → 다각도 검토 → 구현 플랜 + 테스트 시나리오 산출. 사용자가 "/feature-plan KMA-XXXX", "피처 플랜", "구현 플랜 짜줘" 표현을 쓸 때 이 스킬을 사용한다.
argument-hint: [KMA-XXXX | Jira URL] [--help]
---

# Feature Plan Skill

Jira 티켓 하나를 받아 **6단계 플로우**로 구현 플랜과 테스트 시나리오를 생성한다.

## 0. `--help`

`$ARGUMENTS` 에 `--help` 포함 시 `guide.md` 를 Read 해 "## 사용법" 섹션만 출력하고 종료.

## 1. 인수 파싱

`$ARGUMENTS` 파싱:

| 입력 형태 | 처리 |
|----------|------|
| URL (`.../browse/KMA-7275`) | 마지막 segment를 티켓 키로 사용 |
| 키 형식 (`{UPPERCASE}-{DIGITS}`) | 그대로 사용 |
| `{TICKET_KEY} --resume` | 티켓 키 추출 + `RESUME_MODE = true` |
| 티켓 키 없음 | `"티켓 번호를 입력해주세요: /feature-plan KMA-XXXX"` 출력 후 종료 |

### --resume 처리

`RESUME_MODE = true` 인 경우:

1. `docs/plans/{YYYY-MM-DD}-{TICKET_KEY}-draft.md` 읽기 (없으면 `"저장된 초안이 없습니다. /feature-plan {TICKET_KEY} 로 새로 시작하세요."` 출력 후 종료)
2. `RESUME_PHASE` (cp1 / cp2), 저장된 DOC_* 변수 복원
3. Confluence 재수집 여부 확인:

   ```
   Confluence나 슬랙으로 업데이트된 내용이 있나요?
   [Enter] 저장된 스펙 그대로 사용
   [r] Confluence 재수집 후 재개
   ```

   `[r]` 선택 시 드래프트의 Confluence URL로 재fetch → 변경된 DOC_* 변수 업데이트

4. ❓ 항목 순서대로 질문 → 답변 입력 받아 컨텍스트 반영:
   - 텍스트 → 그대로 반영
   - 슬랙 URL (`slack.com/archives/...`) → `mcp__claude_ai_Slack__slack_read_thread` fetch → 관련 내용 추출 후 반영
   - Confluence URL → `mcp__claude_ai_Atlassian__getConfluencePage` fetch → 관련 섹션 추출 후 반영

5. 모든 답변 완료 → `RESUME_PHASE` CP 출력으로 점프 (Phase 1~2/3 재실행 없음)

> CP1/CP2 인라인 답변 시에도 슬랙/Confluence URL 입력 → 자동 fetch 동일 적용.

---

## Phase 1. 문서 수집

### 1-1. Jira 티켓 읽기

`mcp__claude_ai_Atlassian__getJiraIssue`:
- cloudId: `kurly0521.atlassian.net`
- issueIdOrKey: `{TICKET_KEY}`
- responseContentFormat: `markdown`

`TICKET_SUMMARY`, `TICKET_DESCRIPTION` 에 보존.

### 1-2. 연결 문서 수집 → 4개 변수로 분리 저장

`TICKET_DESCRIPTION` 에서 URL 추출 후 fetch. **단일 변수에 합산하지 않고** 개발 관점 4개 변수로 분리:

| 변수 | 내용 | 출처 |
|------|------|------|
| `DOC_API_SPEC` | 엔드포인트, 요청 파라미터, 응답 신규 필드, nullable 여부, **서버 사전 설정**(섹션 ID, 피처플래그 등) | Confluence PRD |
| `DOC_SCREEN_SPEC` | 화면별 UI 요구사항, 로딩/에러/Empty 상태 정의 | Confluence PRD + Figma |
| `DOC_EVENT_SPEC` | 이벤트명, 필수/선택 프로퍼티, 트리거, 조건부 여부 | 이벤트 로그 설계서 |
| `DOC_POLICY` | 트리거 조건, 판별 기준, 분기 규칙, 고정값 | Confluence PRD |

fetch 대상:

| 타입 | 패턴 | 처리 |
|------|------|------|
| Confluence PRD | `kurly0521.atlassian.net/wiki/...` | `getConfluencePage` → 4개 변수로 분류 |
| Figma | `figma.com/design/{fileKey}/...?node-id={nodeId}` | `get_metadata` → `DOC_SCREEN_SPEC` 에 추가 |
| 이벤트 로그 설계서 | `docs.google.com/spreadsheets/...` + anchor에 "이벤트"·"tracking"·"분석" 포함 | `WebFetch` → `DOC_EVENT_SPEC` |
| 화면설계서 | `docs.google.com/presentation/...` | `WebFetch` → `DOC_SCREEN_SPEC` 에 추가 |
| WBS | `docs.google.com/spreadsheets/...` + anchor에 "WBS"·"일정"·"스프린트" 포함 | `TICKET_SUMMARY` 에 일정/담당자만 추가 |

anchor 텍스트가 없거나 판단 불가 시 → WebFetch 후 내용 기반으로 분류.

링크가 없거나 접근 불가 시 해당 타입은 skip, 티켓 내용만으로 진행.

---

## Phase 2. 교차 검증 + ❓ 발굴

PRD를 재합산하지 않는다. `DOC_API_SPEC` / `DOC_SCREEN_SPEC` / `DOC_EVENT_SPEC` / `DOC_POLICY` 4개 변수를 교차 비교해 불일치·누락·모순을 찾고 ❓ 항목을 생성한다.

### 교차 검증 기준

- `DOC_API_SPEC` ↔ `DOC_EVENT_SPEC`: API 신규 필드와 이벤트 프로퍼티 간 대응 누락
- `DOC_SCREEN_SPEC` ↔ `DOC_POLICY`: 화면 상태(Empty/Error)와 트리거 조건 간 불일치
- `DOC_API_SPEC` ↔ `DOC_POLICY`: 판별 기준과 API 필드 정의 간 모순
- `DOC_SCREEN_SPEC`(PRD 텍스트) ↔ `DOC_SCREEN_SPEC`(Figma 프레임 목록): PRD에 명시된 화면 상태(로딩/에러/Empty 등)에 대응하는 Figma 프레임이 없는 경우
- 두 문서 간 같은 사항을 다른 표현으로 기술한 경우

### ✋ CP1: 사용자 확인

❓ 항목이 없으면 자동으로 진행한다.

```
## Phase 2 완료 — 수집 문서 확인

| 변수 | 출처 | 상태 |
|------|------|------|
| DOC_API_SPEC | Confluence PRD §API | ✅ |
| DOC_SCREEN_SPEC | Confluence PRD §화면 + Figma | ✅ |
| DOC_EVENT_SPEC | 이벤트 로그 설계서 | ✅ |
| DOC_POLICY | Confluence PRD §정책 | ✅ |

---
❓ 외부 확인 필요 항목 (있는 경우만)

**Q1. {항목 제목}** | 확인 대상: 서버팀/기획/디자인
- 출처: {출처 문서 + 섹션}
- 원문: {해당 문서의 실제 문구}
- 문제: {다른 문서와 어떻게 충돌/불명확한지}
- 필요한 답: {어떤 결정이 필요한지}

---
[Enter] 계속  [s] 초안 저장 후 종료  [q] 종료
```

`[s]` 선택 시 초안 저장 후 종료:

```markdown
<!-- feature-plan draft — /feature-plan {TICKET_KEY} --resume 으로 재개 -->
RESUME_PHASE: cp1

## ❓ 확인 필요 항목
- Q1 | {항목} | {확인 대상} | 출처: ... / 원문: ... / 문제: ...

---
## DOC_API_SPEC
{API 스펙 원문}
## DOC_SCREEN_SPEC
{화면 스펙 원문}
## DOC_EVENT_SPEC
{이벤트 스펙 원문}
## DOC_POLICY
{정책 원문}
```

저장 경로: `docs/plans/{YYYY-MM-DD}-{TICKET_KEY}-draft.md`

---

## Phase 3. 1차 구현 스텝

### 3-1. 레이어별 영향 분석

`DOC_API_SPEC`, `DOC_POLICY` 에서 키워드(API path, 모델명, 이벤트명, 화면명) 추출 후 코드베이스 탐색 (Glob/Grep 사용).

결과를 아래 표로 정리 → `LAYER_ANALYSIS` 에 저장:

| 레이어 | 파일 | 변경 이유 |
|--------|------|-----------|
| Data | ... | ... |
| Domain | ... | ... |
| Features | ... | ... |

### 3-2. 1차 구현 스텝 초안

레이어별 변경 대상을 기반으로 커밋 단위 스텝 초안 작성 → `IMPL_STEPS_DRAFT` 에 저장:
- Step N: {레이어} — {변경 내용} (파일: {경로})

> `/event-snapshot` 및 이벤트 Delta 분석은 이 단계에서 실행하지 않는다.
> Phase 4에서 4-1/4-2/4-3 서브에이전트와 병렬로 실행하고 4-4 직전에 완료한다.

### ✋ CP2: 사용자 확인

❓ 항목이 없으면 자동으로 진행한다.

```
## Phase 3 완료 — 1차 구현 스텝

### 레이어별 영향 분석
{LAYER_ANALYSIS}

### 1차 구현 스텝
{IMPL_STEPS_DRAFT}

---
❓ 코드 탐색 중 발견된 불명확 항목 (있는 경우만)

**Q1. {항목 제목}** | 확인 대상: 서버팀/기획
- 출처: {파일 경로:라인 + PRD 섹션}
- 원문: {코드 현재 구현 + PRD 해당 내용}
- 문제: {어떻게 충돌하는지}
- 필요한 답: {어떤 결정이 필요한지}

---
[Enter] 계속  [s] 초안 저장 후 종료  [e] 수정  [q] 종료
```

**불명확 항목 발굴 조건:**
- PRD API 스펙과 코드베이스 기존 필드 구조 불일치
- 기존 로직과 PRD 요구사항 충돌
- event-snapshot 결과와 PRD 이벤트 스펙 간 차이가 의도적인지 불명확한 경우

`[s]` 선택 시 초안 저장 후 종료:

```markdown
<!-- feature-plan draft — /feature-plan {TICKET_KEY} --resume 으로 재개 -->
RESUME_PHASE: cp2

## ❓ 확인 필요 항목
- Q1 | {항목 설명} | {확인 대상} | 출처: ... / 원문: ... / 문제: ...

---
## DOC_API_SPEC
{저장된 API 스펙}
## DOC_SCREEN_SPEC
{저장된 화면 스펙}
## DOC_EVENT_SPEC
{저장된 이벤트 스펙}
## DOC_POLICY
{저장된 정책/판별 기준}
## LAYER_ANALYSIS
{레이어 분석 표}
## IMPL_STEPS_DRAFT
{구현 스텝 초안}
```

저장 경로: `docs/plans/{YYYY-MM-DD}-{TICKET_KEY}-draft.md`

---

## Phase 4. 다각도 검토

4-1/4-2/4-3 서브에이전트를 **병렬 실행**하고, 동시에 `/event-snapshot` 을 실행한다.
4-1/4-2/4-3 완료 + `EVENT_DELTA` 준비 완료 후 4-4 BI 서브에이전트를 실행한다.

서브에이전트별 입력 — 필요한 변수만 전달:

| 서브에이전트 | 모델 | 전달 변수 |
|-------------|------|----------|
| 4-1. 기획자 | sonnet | `DOC_SCREEN_SPEC` + `DOC_POLICY` + `IMPL_STEPS_DRAFT` |
| 4-2. Architect | opus | `DOC_API_SPEC` + `LAYER_ANALYSIS` + `IMPL_STEPS_DRAFT` |
| 4-3. QA | sonnet | `DOC_POLICY` + `DOC_SCREEN_SPEC` + `IMPL_STEPS_DRAFT` |
| 4-4. BI | haiku | `DOC_EVENT_SPEC` + `EVENT_DELTA` |

### 4-1/4-2/4-3 와 병렬: /event-snapshot 실행

`DOC_EVENT_SPEC`가 비어있으면 event-snapshot + 4-4 BI 서브에이전트를 skip하고 `EVENT_DELTA = N/A` 로 기록한다.

`LAYER_ANALYSIS` Features 레이어에서 특정된 ViewModel 파일들을 대상으로 `/event-snapshot` 스킬 실행.
결과 `SNAPSHOT_EVENTS` 저장 → `DOC_EVENT_SPEC` vs `SNAPSHOT_EVENTS` 비교 → `EVENT_DELTA` 생성:

| 구분 | 이벤트명 | 변경 내용 |
|------|----------|-----------|
| 🆕 신규 | ... | PRD에 있고 snapshot에 없음 |
| ✏️ 변경 | ... | 프로퍼티 추가/수정 필요 |
| ✅ 유지 | ... | 변경 없음 |

### 4-1. 기획자 관점 서브에이전트

```
subagent_type: general-purpose
model: sonnet
prompt: |
  아래 PRD와 구현 스텝을 기획자 관점으로 검토하라.

  ## 체크리스트 — 기획서/피그마/API 3축 교차 검증
  - 기획서의 모든 화면 케이스가 구현 스텝에 포함되어 있는가
  - 피그마 디자인에서 정의된 상태(로딩/에러/빈화면)가 구현 스텝에 반영되어 있는가
  - API 스펙의 모든 신규/변경 필드가 PRD 요구사항과 대응되는가
  - 트리거 조건 분기가 모두 구현 스텝에 커버되는가
  - 예외/에러 케이스(네트워크 실패, null 응답 등)가 정의되어 있는가
  - 정책 조건(노출 규칙, 고정값, 우선순위 등)이 반영되어 있는가

  ## 자유 발굴
  DOC_SCREEN_SPEC·DOC_POLICY 2축을 교차 비교하며 구현 스텝에서 누락된 항목 발굴

  ## 출력 형식
  - 🔴 확인필요: [이슈 설명] (사람 판단/기획 의도 불명확)
  - 🟢 즉시반영: [이슈 설명] → [반영 방법]

  {DOC_SCREEN_SPEC}
  {DOC_POLICY}
  {IMPL_STEPS_DRAFT}
```

### 4-2. Android Architect 관점 서브에이전트

```
subagent_type: general-purpose
model: opus
prompt: |
  아래 구현 스텝을 Android Architect 관점으로 검토하라.
  먼저 아래 rule 파일들을 Read 해 기준으로 삼아라:
  - .claude/rules/android-architecture.md
  - .claude/rules/data-layer.md
  - .claude/rules/jetpack-compose.md
  - .claude/rules/performance.md

  ## 체크리스트 (rule 기반)

  **ViewModel/UiState:**
  - UiState는 data class, 도메인 의미 값만 노출 (View.VISIBLE/GONE, R.drawable.* 금지)
  - MutableStateFlow는 private, .asStateFlow()로 외부 노출
  - 일회성 이벤트는 Channel 사용, StateFlow 혼용 금지
  - 상태 업데이트는 _uiState.update { } 람다 사용 (thread-safe)
  - @HiltViewModel + @Inject constructor 사용
  - ViewModel에서 Repository 직접 주입 금지 (UseCase 경유)
  - sealed interface로 Event / Action 정의되어 있는가

  **Data Layer:**
  - DTO 모든 프로퍼티 nullable 선언
  - @SerializedName 누락 없는가
  - Repository 반환값 Result<T>로 감싸져 있는가
  - Domain 모듈에 Android/직렬화 어노테이션 없는가

  **Compose:**
  - collectAsStateWithLifecycle 사용 (collectAsState 금지)
  - State Hoisting 준수
  - Fragment ComposeView에 DisposeOnViewTreeLifecycleDestroyed 설정

  **Performance:**
  - 루프 내 indexOf/contains → Set/Map 변환 여부
  - 독립적 suspend 함수는 async/await 병렬 처리

  ## 자유 발굴
  기존 코드 패턴과의 정합성, 신규 모델/UseCase 네이밍 일관성

  ## 출력 형식
  - 🔴 확인필요: [이슈]
  - 🟢 즉시반영: [이슈] → [반영 방법]

  {DOC_API_SPEC}
  {LAYER_ANALYSIS}
  {IMPL_STEPS_DRAFT}
```

### 4-3. QA 관점 서브에이전트

```
subagent_type: general-purpose
model: sonnet
prompt: |
  아래 PRD와 구현 스텝을 QA 관점으로 검토하라.

  ## 체크리스트
  - Happy path 커버
  - 판별 기준 분기 케이스 전체 (DOC_POLICY 조건 테이블 기준)
  - 네트워크 에러 케이스
  - 빈 목록 / null 케이스

  ## 자유 발굴
  테스트 시나리오 누락 케이스, 회귀 영향 범위

  ## 출력 형식
  - 🔴 확인필요: [이슈]
  - 🟢 즉시반영: [이슈] → [반영 방법 또는 테스트 시나리오 추가]

  {DOC_POLICY}
  {DOC_SCREEN_SPEC}
  {IMPL_STEPS_DRAFT}
```

### 4-4. BI 관점 서브에이전트

```
subagent_type: general-purpose
model: haiku
prompt: |
  아래 이벤트 원본 스펙과 Delta를 BI 관점으로 검토하라.

  ## 체크리스트
  - DOC_EVENT_SPEC의 모든 이벤트가 EVENT_DELTA에 반영되어 있는가
  - 필수 프로퍼티 누락 없는가
  - 광고/비광고 분기 이벤트 처리 정확한가
  - Optional 프로퍼티 null 처리 정의되어 있는가

  ## 자유 발굴
  이벤트 원본 스펙과 Delta 간 불일치

  ## 출력 형식
  - 🔴 확인필요: [이슈]
  - 🟢 즉시반영: [이슈] → [반영 방법]

  {DOC_EVENT_SPEC}
  {EVENT_DELTA}
```

4개 서브에이전트 완료 후 결과를 `REVIEW_RESULTS` 에 합산.

---

## Phase 5. 이슈 분류

`REVIEW_RESULTS` 에서:

| 구분 | 조건 | 처리 |
|------|------|------|
| 🔴 확인필요 | 기획 의도 불명확 / 서버팀·PM 확인 필요 / 정책 모순 | CP3에서 사용자에게 제시 |
| 🟢 즉시반영 | 명확한 구현 누락 / rule 위반 / 이벤트 프로퍼티 누락 | 자동으로 구현 스텝 보강 |

> **연쇄 이슈 처리:** 서로 다른 관점 에이전트가 발굴한 항목이 동일 근본 원인에서 비롯된 경우, 하나로 묶고 연쇄 관계를 명시한다.

🟢 즉시반영 항목은 `IMPL_STEPS_DRAFT` 에 자동 반영 → `IMPL_STEPS_FINAL` 생성.

### ✋ CP3: 사용자 확인 (🔴 항목만)

```
## Phase 5 — 확인이 필요한 이슈

아래 항목들은 기획/서버팀 확인 후 반영해주세요:

{🔴_ISSUES_LIST}

---
확인 후 내용을 입력하거나 [Enter] 로 건너뛰세요.
[Enter] 현재 상태로 진행  [입력] 이슈 해소 내용 직접 입력  [q] 종료
```

사용자 입력이 있으면 해당 내용을 `IMPL_STEPS_FINAL` 에 반영.

---

## Phase 6. 최종 플랜 생성

### 6-1. write-test 호출 → 단위 테스트 시나리오

`write-test` 스킬 호출:
- 대상: `LAYER_ANALYSIS` 에서 특정된 ViewModel, UseCase, Repository 파일
- 컨텍스트: `IMPL_STEPS_FINAL`, `EVENT_DELTA`

결과를 `TEST_SCENARIOS` 에 저장.

### 6-2. /write-instrument-test 호출 → Instrumented Test 플랜

`LAYER_ANALYSIS`에 Features 레이어 변경이 없으면 이 단계를 skip하고 플랜 `## 5. Instrumented Test 플랜` 섹션을 생략한다.

`write-instrument-test` 스킬 호출:
- 대상: `LAYER_ANALYSIS` Features 레이어에서 변경된 Composable/Screen 파일
- 컨텍스트: `DOC_SCREEN_SPEC`, `EVENT_DELTA`

결과를 `INSTRUMENTED_TEST_PLAN` 에 저장.

Journey Test 해당 여부 판단 (아래 조건 중 하나라도 해당 시 플랜에 명시):
- 로그인/인증 플로우 변경
- 결제/주문 플로우 변경
- 멤버십 가입/해지 플로우 변경

### 6-3. writing-plans 호출 → 구현 스텝

`writing-plans` 스킬 호출:
- 입력: `IMPL_STEPS_FINAL`, `DOC_API_SPEC`, `DOC_POLICY`, `LAYER_ANALYSIS`

결과를 `WRITING_PLANS_RESULT` 에 저장.

### 6-4. 검증 플랜 생성

`LAYER_ANALYSIS`, `DOC_SCREEN_SPEC`, `DOC_POLICY`, `EVENT_DELTA` 기반으로 자동 생성:

**빌드/단위 테스트:** 변경 모듈 목록 → `compileDebugKotlin` + `testDebugUnitTest` 명령어

**PRD 요구사항 체크리스트:** `DOC_SCREEN_SPEC` 화면별 요구사항 + `DOC_POLICY` 분기 조건 → 확인 방법 매핑 표

**실기기/stg 검증:** `EVENT_DELTA` 신규/변경 이벤트 → `adb logcat` 필터 명령어, API 파라미터 확인 대상 명시

결과를 `VERIFICATION_PLAN` 에 저장.

### 6-5. 최종 플랜 파일 작성

저장 경로: `docs/plans/{YYYY-MM-DD}-{TICKET_KEY}-plan.md`

```markdown
# {TICKET_KEY} 구현 플랜

## 0. 티켓 요약
{TICKET_SUMMARY}

## 1. 스펙

### API 스펙
{DOC_API_SPEC}

### 화면 스펙
{DOC_SCREEN_SPEC}

### 이벤트 스펙
{DOC_EVENT_SPEC}

### 정책/판별 기준
{DOC_POLICY}

## 2. 레이어별 영향 분석
{LAYER_ANALYSIS}

## 3. 이벤트 Delta
{EVENT_DELTA}

## 4. 단위 테스트 시나리오
{TEST_SCENARIOS}

## 5. Instrumented Test 플랜
{INSTRUMENTED_TEST_PLAN}

## 6. 구현 스텝 (커밋 단위)
{WRITING_PLANS_RESULT}

## 7. 검증 플랜
{VERIFICATION_PLAN}

## 8. 검토 이슈 반영 내역
{REVIEW_APPLIED}
```

### 6-6. Jira description 업데이트

```
플랜이 저장되었습니다: docs/plans/{YYYY-MM-DD}-{TICKET_KEY}-plan.md

Jira {TICKET_KEY} description을 업데이트하시겠습니까?
[Enter] 업데이트  [s] 건너뛰기
```

`mcp__claude_ai_Atlassian__editJiraIssue` 호출.
기존 description을 덮어쓰지 않고 `---` 구분선 후 `## 기술 스펙 (feature-plan)` 섹션으로 append.
내용: 레이어 분석 표 + 이벤트 Delta.
