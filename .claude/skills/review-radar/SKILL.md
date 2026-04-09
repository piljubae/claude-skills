---
name: review-radar
description: 지정 기간 PR의 AI·사람 코멘트를 비교해 /code-review 스킬의 누락·오탐 패턴을 분석하고 에이전트 파일별 개선안을 도출한다
argument-hint: [--days N] [--repo owner/repo]
---

# Review Radar

## 개요

최근 N일간 머지된 PR의 AI 코드리뷰 코멘트와 사람 코멘트를 비교 분석해
`/code-review` 스킬의 누락(false negative)과 오탐(false positive) 패턴을 파악하고
에이전트 파일별 구체적인 개선안을 도출한다.

## 인자

| 인자 | 기본값 | 설명 |
|------|--------|------|
| `--days N` | 14 | 분석 기간 (일) |
| `--repo owner/repo` | 현재 git remote | 대상 레포지토리 |
| `--help` | — | 사용법 출력 |

---

## 실행 순서

### 0. --help 처리

`$ARGUMENTS`에 `--help` 포함 시 위 인자 표를 출력하고 종료.

### 1. 인자 파싱

```
DAYS  = --days 값 (없으면 14)
SINCE = 오늘 날짜 - DAYS 일 (YYYY-MM-DD)
TODAY = 오늘 날짜 (YYYY-MM-DD)
REPO  = --repo 값이 있으면 사용, 없으면:
          gh repo view --json nameWithOwner --jq '.nameWithOwner' 2>/dev/null
        실패 시 "분석할 레포를 --repo owner/repo 로 지정해주세요." 출력 후 종료
```

### 2. Phase 1 — 데이터 수집 (순차)

Read tool로 `~/.claude/agents/review-radar-collector.md`를 읽어 `COLLECTOR_PROMPT`에 저장.

Agent tool 실행:
```
subagent_type: "general-purpose"
description: "PR 코멘트 데이터 수집"
prompt: |
  {COLLECTOR_PROMPT 전체}

  ---

  ## 파라미터
  SINCE: {SINCE}
  REPO: {REPO}
  OUTPUT_FILE: /tmp/review_radar_pr_data.json
```

에이전트가 `/tmp/review_radar_pr_data.json` 파일에 데이터를 저장한다.

완료 후 파일 존재 여부 확인:
```bash
[ -f /tmp/review_radar_pr_data.json ] && echo "ok" || echo "fail"
```
파일이 없거나 비어있으면 "데이터 수집에 실패했습니다." 출력 후 종료.

PR 수 확인:
```bash
python3 -c "import json; d=json.load(open('/tmp/review_radar_pr_data.json')); print(len(d))"
```
0이면 "분석할 PR이 없습니다." 출력 후 종료.

### 3. Phase 2 — 병렬 분석 (2 에이전트 동시 실행)

2개 에이전트를 **동시에** 호출한다.
각 에이전트는 `/tmp/review_radar_pr_data.json`을 직접 읽어서 분석한다.

**공통 프롬프트 패턴:**
```
{ANALYST_PROMPT 전체}

---

## 데이터 파일
/tmp/review_radar_pr_data.json
```

| 에이전트 파일 | 결과 변수 |
|---|---|
| `~/.claude/agents/review-radar-false-positive.md` | `FP_RESULT` |
| `~/.claude/agents/review-radar-coverage-gap.md` | `GAP_RESULT` |

### 4. 리포트 작성 및 저장

FP_RESULT와 GAP_RESULT를 바탕으로 직접 아래 형식의 리포트를 작성한다.

```markdown
# Review Radar — {SINCE} ~ {TODAY} ({DAYS}일간)

- **레포**: {REPO}
- **분석일**: {TODAY}

## 📊 종합 분석 요약

| 항목 | 건수 |
|------|------|
| 분석 PR 수 | N개 |
| AI 리뷰 있는 PR | N개 |
| 오탐 (AI 코멘트 거절) | N건 |
| 누락 — 사람이 잡은 것 | N건 |
| 누락 — growth만 잡은 실질 이슈 | N건 |
| growth-code-review 코멘트 (priority=null) | N건 |

---

## 🔧 개선 우선순위

### High 🔴
(3건 이상 반복 또는 P1/P2 오탐·누락)

**{에이전트 파일명}**
- 문제: {패턴 설명}
- 개선안: {구체적 rule 또는 예시 코드}
- 근거: PR #{번호} ...

### Medium 🟡
(2건 반복 또는 P3 패턴)

### Low ⚪
(1건, 단발성)

---

## ✅ 잘 작동하는 영역

---

## 🔄 growth-code-review 비교
(growth-code-review가 있는 PR에서만 작성)

- 우리만 잡은 것: N건
- growth만 잡은 실질 이슈: N건
- 둘 다 잡은 것: N건

growth 누락 중 강화 검토 대상: {카테고리·패턴 요약}

---

## ⚠️ 스킬 자체 이슈
(데이터 수집/분류 오류가 발견된 경우만)

---

## 📝 다음 스텝

1. ...
```

리포트 파일 저장:
```
REPORT_PATH = $HOME/Documents/Claude Cowork/review-radar/{TODAY}-review-radar.md
```

Write tool로 저장 후 터미널에 리포트 전체 출력, 마지막에:
```
📄 리포트 저장됨: {REPORT_PATH}
```
