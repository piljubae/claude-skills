# Crash Fix Skill Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 두 개의 독립 스킬로 크래시 대응 자동화.
- `/report-crash` — BigQuery에서 크래시 정보 조회 → Jira 티켓 본문 자동 작성
- `/fix-crash` — 단일 세션 TDD 흐름으로 크래시 수정 (탐색 → 분석 → 실패 테스트 → 수정 → PR)

**Architecture:** 에이전트 없음. 두 스킬 모두 단일 세션에서 직접 실행. 컨텍스트가 단계 간 유지됨.

**실행 순서 (`/fix-crash`):** 티켓 읽기 → 탐색 → 분석 → ✋CP1 → 실패 테스트(FAIL) → ✋CP2 → 수정(PASS) → ✋CP3 → 커밋 + PR

**Tech Stack:** Claude Code skills (markdown), Jira MCP (claude_ai_Atlassian), Python + google-cloud-bigquery, `/write-test` 스킬, Gradle compileDebugKotlin/testDebugUnitTest

---

## Task 1: /report-crash 스킬 생성

**Files:**
- Create: `.claude/skills/report-crash/SKILL.md`

**Step 1: 스킬 파일 작성**

```markdown
# /report-crash 스킬

Firebase 크래시 URL 또는 Jira 티켓 키를 받아 BigQuery에서 통계·스택·재현 경로를
한 번에 조회하고 Jira 티켓 본문을 자동으로 채운다.

---

## 사용법

```
# Firebase 크래시 URL (가장 간단 — URL 안에 issue_id 포함)
/report-crash https://console.firebase.google.com/project/market-kurly/crashlytics/app/android:com.dbs.kurly.m2/issues/ISSUE_ID

# Jira 키 (티켓 본문에서 Firebase URL 자동 탐색)
/report-crash KMA-XXXX
```

---

## 전제 조건

- Python 3 + `google-cloud-bigquery`: `pip install google-cloud-bigquery`
- BigQuery ADC 설정: `gcloud auth application-default login`
- Jira MCP: `claude_ai_Atlassian`
- BigQuery 테이블: `market-kurly.firebase_crashlytics.com_dbs_kurly_m2_ANDROID`

---

## 실행 흐름

```
[Step 1] issue_id 확보
    Firebase URL 있으면 → 정규식으로 직접 추출
    Jira 키만 있으면  → 티켓 본문에서 Firebase URL 탐색
    못 찾으면         → 사용자에게 URL 요청

[Step 2] Jira 티켓 결정 (Firebase URL만 입력 시)
    JQL로 issue_id 포함 티켓 탐색
    1건  → 확인 후 업데이트
    복수 → 목록 출력 후 선택
    0건  → 신규 Bug 티켓 생성

[Step 3] BigQuery 3-in-1 쿼리 (Python)

[Step 4] 결과 포맷팅 → Jira 본문 업데이트
```

---

## 상세 절차

### Step 1: issue_id 파싱

Firebase Console URL 정규식:
```
https://console\.firebase\.google\.com/project/.*/crashlytics/app/.*/issues/([a-f0-9]+)
```

Firebase URL 없으면 `getJiraIssue` (cloudId: `kurly0521.atlassian.net`)로 description 전체에서 같은 정규식 적용.

### Step 2: Jira 티켓 결정

Firebase URL만 입력된 경우 `searchJiraIssuesUsingJql`:
```
project = KMA AND description ~ "ISSUE_ID" ORDER BY created DESC
```
- 1건 → "KMA-XXXX 에 업데이트할까요? [Enter/s]"
- 복수 → 목록 출력 후 선택
- 0건 → `createJiraIssue` 신규 생성
  - projectKey: `KMA`, issueTypeName: `Bug`
  - summary: BigQuery `issue_title: issue_subtitle`
  - contentFormat: `markdown`

### Step 3: BigQuery 3-in-1 쿼리

`/tmp/report_crash_ISSUEID.py` 생성 후 실행:

```python
from google.cloud import bigquery
import json, sys, warnings
warnings.filterwarnings("ignore")

ISSUE_ID = sys.argv[1]
TABLE = "market-kurly.firebase_crashlytics.com_dbs_kurly_m2_ANDROID"
client = bigquery.Client(project="market-kurly")

stats_query = f"""
SELECT issue_title, issue_subtitle,
  COUNT(*) AS total_crashes,
  COUNT(DISTINCT installation_uuid) AS affected_users,
  MIN(event_timestamp) AS first_seen,
  MAX(event_timestamp) AS last_seen,
  ARRAY_AGG(DISTINCT application.display_version IGNORE NULLS ORDER BY application.display_version DESC LIMIT 5) AS versions,
  ARRAY_AGG(DISTINCT CONCAT(device.manufacturer, ' ', device.model) IGNORE NULLS LIMIT 5) AS devices
FROM `{TABLE}`
WHERE issue_id = '{ISSUE_ID}'
  AND DATE(event_timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
GROUP BY issue_title, issue_subtitle
"""

stack_query = f"""
SELECT t.frames FROM `{TABLE}`, UNNEST(threads) AS t
WHERE issue_id = '{ISSUE_ID}' AND t.crashed = TRUE
  AND DATE(event_timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
LIMIT 1
"""

breadcrumb_query = f"""
WITH ranked AS (
  SELECT firebase_session_id, breadcrumbs, logs,
    ROW_NUMBER() OVER (PARTITION BY issue_id ORDER BY ARRAY_LENGTH(breadcrumbs) DESC) AS rn
  FROM `{TABLE}`
  WHERE issue_id = '{ISSUE_ID}'
    AND DATE(event_timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
)
SELECT firebase_session_id, breadcrumbs, logs FROM ranked WHERE rn = 1
"""

stats_rows = list(client.query(stats_query).result())
stack_rows = list(client.query(stack_query).result())
bc_rows    = list(client.query(breadcrumb_query).result())

result = {
    "stats":        dict(stats_rows[0]) if stats_rows else {},
    "stack_frames": [dict(f) for f in stack_rows[0].frames] if stack_rows else [],
    "session_id":   bc_rows[0].firebase_session_id if bc_rows else None,
    "breadcrumbs":  [dict(b) for b in bc_rows[0].breadcrumbs] if bc_rows else [],
    "logs":         [dict(l) for l in bc_rows[0].logs] if bc_rows else [],
}
print(json.dumps(result, default=str))
```

```bash
python3 /tmp/report_crash_ISSUEID.py ISSUE_ID > /tmp/report_crash_ISSUEID_result.json
```

### Step 4: 결과 포맷팅 + Jira 업데이트

JSON을 아래 구조로 변환:

```markdown
## 크래시 분석 (BigQuery 자동 생성)

**Firebase Issue ID:** `ISSUE_ID`
**Firebase Console:** https://console.firebase.google.com/project/market-kurly/crashlytics/app/android:com.dbs.kurly.m2/issues/ISSUE_ID

### 📊 통계

| 항목 | 값 |
|------|----|
| 총 발생 건수 | N건 |
| 영향받은 사용자 | N명 |
| 최초 발생 | YYYY-MM-DD |
| 최근 발생 | YYYY-MM-DD |
| 발생 버전 | 3.x.x, ... |
| 주요 기기 | Samsung ..., ... |

### 🔥 스택 트레이스

\`\`\`
클래스.메서드 (파일:라인)
...
\`\`\`

### 🗺️ 재현 경로 (Breadcrumbs)

**세션 ID:** `SESSION_ID`

| 시각 | 이벤트 | 화면 |
|------|--------|------|
| HH:MM:SS | 세션 시작 | — |
| HH:MM:SS | 화면 진입 | ActivityName |
| HH:MM:SS | 커스텀이벤트 | ActivityName |

### 📍 재현 시나리오

1. 선행 상태
2. 트리거 동작
3. → 크래시 발생
```

breadcrumb 디코딩: `_s` → 세션 시작 / `_vs` + params `_sc` → 화면 진입 / 나머지 → 커스텀 이벤트

`editJiraIssue` 호출:
- `contentFormat: "markdown"` (ADF 자동 변환)
- 기존 description 보존, `## 크래시 분석 (BigQuery 자동 생성)` 섹션만 추가/교체 (멱등)

---

## 출력

```
✅ KMA-XXXX 티켓 본문 업데이트 완료

📊 총 N건 / 영향 사용자 N명
🔥 issue_id: ISSUE_ID
📍 https://console.firebase.google.com/...
```
```

**Step 2: 커밋**
```bash
git add .claude/skills/report-crash/SKILL.md
git commit -m "KMA-6390 report-crash 스킬 추가 (BigQuery → Jira 본문 자동 작성)"
```

---

## Task 2: /fix-crash 스킬 생성

**Files:**
- Create: `.claude/skills/fix-crash/SKILL.md`

**Step 1: 스킬 파일 작성**

```markdown
# /fix-crash 스킬

크래시 티켓을 단일 세션 TDD 방식으로 수정한다.
에이전트 없음 — 탐색부터 커밋까지 같은 세션에서 컨텍스트를 유지하며 진행.

---

## 사용법

```
/fix-crash KMA-XXXX
```

---

## 실행 흐름

```
[Phase 0] 티켓 읽기
    ↓
[Phase 1] 탐색 — Grep/Read로 크래시 위치 특정
    ↓
[Phase 2] 분석 — 근본 원인 + 재현 경로
    ↓
✋ CP1: 분석 승인
    ↓
[Phase 3] 실패 테스트 작성 (FAIL 확인)
    ↓
✋ CP2: 실패 테스트 확인
    ↓
[Phase 4] 수정 (PASS 확인 + 컴파일 검증)
    ↓
✋ CP3: diff 확인 → 커밋 + PR
```

---

## 상세 절차

### Phase 0: 티켓 읽기

`getJiraIssue` (cloudId: `kurly0521.atlassian.net`). 추출:
- 크래시 클래스/메서드명
- 수정 방향 (있는 경우)
- Firebase 크래시 URL (있는 경우 — `/report-crash` 미실행 시 참고용)

### Phase 1: 탐색

직접 도구 사용:
1. CRASH_SUMMARY에서 클래스명/메서드명 키워드 추출
2. Grep으로 코드베이스 검색
3. Read로 관련 파일 열어 문제 코드 블록 특정
4. Fragment/Activity 관계라면 상위 호출자까지 추적

### Phase 2: 분석

Phase 1 결과를 이어받아:
1. 크래시 발생 조건 특정
2. 인과관계 정리
3. 수정 가능 여부: **FIXABLE** / **ESCALATE**
4. 재현 경로 도출 (Given / When / Then)
5. 구체적 수정 방법 (파일:라인 + 변경 내용)

### ✋ CP1: 분석 승인

```
## 원인 분석 + 재현 경로

[근본 원인 / 발생 조건 / 재현 경로 / 수정 방법 요약]

[Enter] 진행  [e] 수정  [s] 중단
```

ESCALATE 시:
```
⚠️ 앱 레벨 수정 제한적: <이유>
[Enter] Jira 코멘트 등록 후 종료  [s] 그냥 종료
```

### Phase 3: 실패 테스트 작성

`.claude/rules/testing.md` 규칙:
- 한글 백틱 메서드명, Given-When-Then
- `BaseMockKTest` / `BaseContextMockkTest` 상속
- `runTest`, `advanceUntilIdle`

작성 후 실행:
```bash
./gradlew :<module>:testDebugUnitTest --tests "패키지.클래스명.테스트명"
```
FAIL → 정상 / PASS → 재현 실패, 테스트 수정 필요

### ✋ CP2: 실패 테스트 확인

```
## 크래시 재현 테스트 (현재 FAIL)

[테스트 코드 + 실행 결과]

[Enter] 확인, 수정으로 진행  [e] 테스트 재작성  [s] 중단
```

### Phase 4: 수정

1. 대상 파일 Read (필수) → Edit으로 최소 범위 수정
2. 테스트 재실행 → PASS 확인
3. 컴파일 검증: `./gradlew :<module>:compileDebugKotlin`
4. 실패 시 재수정 (최대 3회)

수정 원칙:
- 최소 변경 — 실패 테스트만 통과시킨다
- `as` → `as?` + null 처리
- YAGNI

### ✋ CP3: 수정 확인 + 커밋 + PR

```
## 수정 결과

[diff + 테스트 PASS + 컴파일 SUCCESS]

[Enter] 커밋 + PR  [c] 커밋만  [e] 수정 변경  [s] 중단
```

커밋:
```bash
git add <수정 파일> <테스트 파일>
git commit -m "<TICKET_KEY> <크래시 수정 요약>"
```
PR: `/create-pr` 실행

---

## 참고

- `/report-crash` — 수정 전 티켓 본문 채우기
- `/write-test` — 테스트 작성 규칙
- `/create-pr` — PR 생성
- `.claude/rules/testing.md`, `.claude/rules/android-architecture.md`
```

**Step 2: 커밋**
```bash
git add .claude/skills/fix-crash/SKILL.md
git commit -m "KMA-6390 fix-crash 스킬 추가 (단일 세션 TDD 흐름)"
```

---

## Task 3: KMA-7574 파일럿 실행

**전제:** Task 1~2 완료 후.

```
/report-crash KMA-7574   # 티켓 본문 먼저 채우기
/fix-crash KMA-7574      # TDD 수정
```

**검증 기준:**
- [ ] CP1에서 재현 경로가 명확히 표현됨
- [ ] CP2에서 테스트가 실제로 FAIL함
- [ ] CP3에서 동일 테스트가 PASS로 전환됨
- [ ] 컴파일 오류 없음

---

_계획 작성: 2026-04-16 (에이전트 → 단일 세션 스킬 기반으로 재설계)_
