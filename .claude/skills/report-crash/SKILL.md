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
    ├─ 데이터 있음 → [Step 4] 포맷팅 (BigQuery)
    └─ 데이터 없음 → [Step 3-A] Firestore 조회

[Step 3-A] Datastore 조회 (Cloud Function이 트리거 시점에 저장한 메타)
    ├─ 데이터 있음 → [Step 4] 포맷팅 (Datastore — title/subtitle/version)
    └─ 데이터 없음 → [Step 3-B] Firebase Console fallback

[Step 3-B] Firebase Console 직접 수집 (AppleScript + Chrome)
    Chrome 실행 여부 확인
    ├─ 미실행 → open -a 로 Firebase URL 열기 → 로그인 유도
    └─ 실행 중 → AppleScript로 새 탭 열기
    sleep 15 → 로그인 체크 → 텍스트 추출 → 파싱

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
SELECT t.frames, t.crashed, t.blamed FROM `{TABLE}`, UNNEST(threads) AS t
WHERE issue_id = '{ISSUE_ID}' AND (t.crashed = TRUE OR t.blamed = TRUE)
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
    "stack_type":   "anr_blamed" if (stack_rows and stack_rows[0].blamed) else "crashed",
    "session_id":   bc_rows[0].firebase_session_id if bc_rows else None,
    "breadcrumbs":  [dict(b) for b in bc_rows[0].breadcrumbs] if bc_rows else [],
    "logs":         [dict(l) for l in bc_rows[0].logs] if bc_rows else [],
}
print(json.dumps(result, default=str))
```

```bash
python3 /tmp/report_crash_ISSUEID.py ISSUE_ID > /tmp/report_crash_ISSUEID_result.json
```

### Step 3-A: Datastore 조회

BigQuery `stats_rows`가 비어있으면 Datastore에서 Cloud Function이 저장한 메타데이터를 조회한다.

```python
from google.cloud import datastore
db = datastore.Client(project="market-kurly")
key = db.key("crashlytics_issues", ISSUE_ID)
entity = db.get(key)
if entity:
    # entity keys: issue_id, title, subtitle, app_version, url, event_type,
    #              created_at, jira_key, has_bigquery_data,
    #              stack_trace (있으면), device_info (있으면)
```

**Datastore 데이터가 있는 경우:**
- `has_bigquery_data == True` → stack_trace, device_info 포함 → 풀 데이터로 Step 4 진행
- `has_bigquery_data == False` → title, subtitle, app_version만 → 기본 정보로 Step 4 진행 (스택 트레이스 없음 표시)

**Datastore 데이터가 없는 경우:** Step 3-B (Firebase Console fallback) 진행.

### Step 3-B: Firebase Console Fallback

BigQuery, Datastore 모두 데이터가 없으면 Firebase Console에서 직접 수집한다.

**1. Chrome 실행 확인 + Firebase URL 열기**

```bash
FIREBASE_URL="https://console.firebase.google.com/project/market-kurly/crashlytics/app/android:com.dbs.kurly.m2/issues/${ISSUE_ID}"

if pgrep -x "Google Chrome" > /dev/null; then
  # 실행 중 → AppleScript로 새 탭
  osascript <<EOF
tell application "Google Chrome"
  set newTab to make new tab at end of tabs of front window
  set URL of newTab to "$FIREBASE_URL"
end tell
EOF
else
  # 미실행 → open으로 Chrome 시작 + URL 열기
  open -a "Google Chrome" "$FIREBASE_URL"
fi
```

**2. 페이지 로드 대기**

```bash
sleep 15
```

**3. 로그인 상태 확인**

```bash
LOGIN_CHECK=$(osascript <<EOF
tell application "Google Chrome"
  repeat with t in tabs of front window
    if URL of t contains "${ISSUE_ID}" or URL of t contains "accounts.google" then
      return title of t
    end if
  end repeat
  return "NOT_FOUND"
end tell
EOF
)
```

`LOGIN_CHECK`에 "로그인" 또는 "Sign in" 포함 시:
```
⚠️ Firebase Console 로그인이 필요합니다.
Chrome에서 로그인 완료 후 Enter를 눌러주세요.
```
→ 사용자 Enter → `sleep 10` → 재체크 → 여전히 미인증이면 중단.

**4. "스택 추적" 탭 클릭 + 텍스트 추출**

```bash
# 탭 클릭
osascript <<EOF
tell application "Google Chrome"
  repeat with t in tabs of front window
    if URL of t contains "${ISSUE_ID}" then
      execute t javascript "
        var buttons = document.querySelectorAll('button, [role=tab]');
        for (var b of buttons) {
          if (b.textContent.includes('스택 추적')) { b.click(); break; }
        }
      "
      exit repeat
    end if
  end repeat
end tell
EOF

sleep 3

# 텍스트 추출
RAW_TEXT=$(osascript <<EOF
tell application "Google Chrome"
  repeat with t in tabs of front window
    if URL of t contains "${ISSUE_ID}" then
      return execute t javascript "document.body.innerText"
    end if
  end repeat
  return ""
end tell
EOF
)
```

**5. 텍스트 파싱**

`RAW_TEXT`에서 추출 시도:
- 크래시 카운트 / 영향 사용자 수
- 영향 버전, 기기 정보
- 스택 트레이스 (Fatal Exception 이후 frame list)
- 로그 및 탐색경로

파싱 실패 시 → raw innerText를 원본 그대로 Jira에 첨부 (아래 Step 4 참조).

### Step 4: 결과 포맷팅 + Jira 업데이트

데이터 소스에 따라 헤더를 분기한다:
- BigQuery → `## 크래시 분석 (BigQuery 자동 생성)`
- Firestore (풀 데이터) → `## 크래시 분석 (BigQuery 자동 생성)` (BigQuery에서 온 데이터이므로 동일)
- Firestore (메타만) → `## 크래시 분석 (Crashlytics 트리거 수집)`
- Firebase Console fallback → `## 크래시 분석 (Firebase Console 직접 수집)`

#### 4-A. BigQuery 데이터 포맷 (기본)

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

#### 4-B. Firestore 메타 전용 포맷 (스택 트레이스 없음)

```markdown
## 크래시 분석 (Crashlytics 트리거 수집)

**Firebase Issue ID:** `ISSUE_ID`
**Firebase Console:** https://console.firebase.google.com/project/market-kurly/crashlytics/app/android:com.dbs.kurly.m2/issues/ISSUE_ID

### 📊 기본 정보

| 항목 | 값 |
|------|----|
| 크래시 제목 | issue.title |
| 부제 | issue.subtitle |
| 발생 버전 | issue.app_version |
| 이벤트 유형 | fatal / anr / regression / velocity |
| 트리거 시각 | created_at |

⚠️ BigQuery 적재 대기 중 — 스택 트레이스, 기기 정보, breadcrumbs는 적재 후 `/report-crash`를 다시 실행하면 풀 데이터로 업데이트됩니다.
```

#### 4-C. Firebase Console 파싱 성공 시

BigQuery와 동일한 마크다운 구조를 사용하되 헤더만 변경:

```markdown
## 크래시 분석 (Firebase Console 직접 수집)
```

나머지 섹션(통계, 스택 트레이스, 재현 경로, 재현 시나리오)은 파싱된 데이터로 동일 포맷 적용.

#### 4-D. Firebase Console 파싱 실패 시

```markdown
## 크래시 분석 (Firebase Console 직접 수집)

**Firebase Issue ID:** `ISSUE_ID`
**Firebase Console:** https://console.firebase.google.com/project/market-kurly/crashlytics/app/android:com.dbs.kurly.m2/issues/ISSUE_ID

⚠️ 자동 파싱 실패 — 원본 텍스트를 첨부합니다.

{panel:title=Raw Firebase Console 텍스트}
...innerText...
{panel}
```

#### Jira 업데이트

`editJiraIssue` 호출:
- `contentFormat: "markdown"` (ADF 자동 변환)
- **기존 description을 반드시 먼저 읽고(`getJiraIssue`), 원본 내용을 보존한 채 `## 크래시 분석` 섹션만 추가/교체**
- 기존 description에 Crashlytics 링크, 발생 기기 등 자동 생성 티켓 원본 정보가 있으므로 절대 덮어쓰지 않는다
- 원본 내용과 분석 섹션 사이에 `---` 구분선 삽입
- 멱등: `## 크래시 분석`으로 시작하는 섹션이 이미 있으면 해당 섹션만 교체
- 매칭 패턴: `## 크래시 분석 (BigQuery 자동 생성)` 또는 `## 크래시 분석 (Crashlytics 트리거 수집)` 또는 `## 크래시 분석 (Firebase Console 직접 수집)`

---

## 출력

```
✅ KMA-XXXX 티켓 본문 업데이트 완료

📊 총 N건 / 영향 사용자 N명
🔥 issue_id: ISSUE_ID
📍 https://console.firebase.google.com/...
```
