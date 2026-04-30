# Code Review Pre-Validator Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** code-review 스킬에 자동 오탐 필터링 단계(4.6)를 추가하여 GitHub POST 전에 false positive를 제거하고, 제거된 항목을 PR의 접힌 코멘트로 리뷰어에게만 노출한다.

**Architecture:**
새 에이전트 `code-reviewer-validator.md`가 이슈 목록을 받아 각 파일을 직접 읽고 기술적 주장을 검증한다. 기존 오탐 패턴 파일 4개를 context로 참조하며, `{ valid, discarded }` JSON을 반환한다. SKILL.md의 step 4.5 이후 step 4.6을 삽입하고, step 5에서 valid 항목만 POST한다. discarded가 있으면 `<details>` 접힌 PR 코멘트를 별도 등록한다.

**Tech Stack:** Markdown (agent prompt), Python (JSON 가공), GitHub CLI (`gh api`)

---

### Task 1: code-reviewer-validator.md 생성

**Files:**
- Create: `.claude/agents/code-reviewer-validator.md`

**Step 1: 에이전트 파일 작성**

아래 전체 내용으로 파일 생성:

```markdown
# Code Reviewer — Validator (Pre-Post 오탐 필터)

## 역할

code-review 스킬이 GitHub에 코멘트를 등록하기 전, 이슈 목록의 기술적 주장이 실제로 타당한지 검증한다.
오탐으로 판정된 이슈는 discarded로 분류하여 PR 작성자에게 노출되지 않도록 한다.

## 판정 원칙

- **명확히 틀림** → `discarded`에 이유와 함께 추가
- **불확실** → `valid` 유지 (보수적)
- **타당함** → `valid` 유지

판단이 조금이라도 불확실하면 반드시 `valid`에 유지한다. 오탐 필터는 확실한 경우에만 작동한다.

## 입력

이 프롬프트 뒤에 다음이 첨부된다:
1. **이슈 목록** — issues JSON 배열 (각 item에 `_verified: true/false` 필드 포함)
2. **원본 diff** — 전체 변경 내용

## 오탐 패턴 참조

검증 시작 전, 아래 에이전트 파일들을 **반드시 Read** 한다 (오탐 패턴 파악용):
- `.claude/agents/code-reviewer-compose.md`
- `.claude/agents/code-reviewer-architecture.md`
- `.claude/agents/code-reviewer-quality.md`
- `.claude/agents/code-reviewer-test.md`

각 파일에서 `### 오탐 방지` 또는 `### 우선순위 보정` 섹션의 내용을 읽어 알려진 패턴을 파악한다.

## 검증 절차 (각 이슈에 대해)

1. `issue.file` 경로를 Read tool로 읽는다 (`issue.line` 기준 ±30줄)
2. `issue.title`과 `issue.body`의 기술적 주장을 실제 코드와 대조한다
3. 읽어둔 오탐 패턴과 비교한다
4. 필요하면 Grep tool로 추가 탐색한다

**`good` 항목은 검증 대상이 아니다** — 입력에 포함되지 않는다.

## 당신이 사용할 수 있는 도구

- **Read tool** — 소스 파일 읽기, 오탐 패턴 파일 읽기
- **Grep tool** — 관련 코드 패턴 탐색

## 출력 JSON 형식

```json
{
  "valid": [
    {
      // 입력받은 issue 필드 모두 그대로 유지 (_verified 포함)
    }
  ],
  "discarded": [
    {
      "file": "features/foo/src/main/FooViewModel.kt",
      "line": 45,
      "title": "MutableState stale capture 위험",
      "reason": "`by` delegate 사용으로 읽을 때마다 fresh value가 보장됨 — stale capture 없음"
    }
  ]
}
```

**규칙:**
- JSON 외의 텍스트는 출력하지 않는다
- 판단이 불확실한 이슈는 반드시 `valid`에 유지한다
- `discarded.reason`은 한국어로, 한 줄로 작성한다
- `valid` 배열의 각 item은 입력받은 모든 필드(`_verified` 포함)를 그대로 유지한다
```

**Step 2: 커밋**

```bash
git add .claude/agents/code-reviewer-validator.md
git commit -m "KMA-7277 code-reviewer-validator 에이전트 추가 (pre-post 오탐 필터)"
```

---

### Task 2: SKILL.md — step 4.6 삽입

**Files:**
- Modify: `.claude/skills/code-review/SKILL.md`

삽입 위치: `## 4.5. diff 기반 라인 번호 검증` 섹션 끝 ~ `## 5. 결과 출력` 섹션 직전

**Step 1: SKILL.md에 step 4.6 블록 추가**

`## 5. 결과 출력` 바로 앞에 아래 섹션을 삽입한다:

````markdown
## 4.6. 오탐 필터링 (PR 모드 전용)

4.5단계의 검증 결과를 validator 에이전트에 전달하여 false positive를 GitHub POST 전에 제거한다.

### 4-6-1. validator 에이전트 프롬프트 로드

```
Read tool:
  .claude/agents/code-reviewer-validator.md
  → VALIDATOR_PROMPT에 저장
```

### 4-6-2. 이슈 목록 준비

verified와 unverified 이슈에 `_verified` 필드를 추가하여 하나의 목록으로 합친다:

```python
# /tmp/prepare_validation.py
import json

with open('/tmp/verified_results.json') as f:
    results = json.load(f)

all_issues = []
for issue in results['verified']:
    issue['_verified'] = True
    all_issues.append(issue)
for issue in results['unverified']:
    issue['_verified'] = False
    all_issues.append(issue)

with open('/tmp/all_issues_for_validation.json', 'w') as f:
    json.dump(all_issues, f, ensure_ascii=False)

print(json.dumps(all_issues, ensure_ascii=False))
```

```bash
ALL_ISSUES=$(python3 /tmp/prepare_validation.py)
```

all_issues가 비어 있으면 이 단계를 건너뛴다.

### 4-6-3. validator 에이전트 호출

```
Agent tool 파라미터:
  subagent_type: "general-purpose"
  description: "Pre-post false positive filtering"
  prompt: |
    {VALIDATOR_PROMPT 전체 내용}

    ---

    ## 이슈 목록

    {ALL_ISSUES JSON}

    ## 원본 diff

    {DIFF 변수 내용}
```

### 4-6-4. 결과 파싱 및 재분류

에이전트 응답에서 `{ valid, discarded }` JSON을 추출한다.

valid 목록을 `_verified` 필드 기준으로 재분류한다:

```python
# /tmp/reclassify_valid.py
import json, sys

data = json.loads(sys.argv[1])
valid = data.get('valid', [])
discarded = data.get('discarded', [])

valid_verified   = [i for i in valid if i.get('_verified')]
valid_unverified = [i for i in valid if not i.get('_verified')]

# _verified 필드 제거 (GitHub POST 시 불필요)
for i in valid_verified + valid_unverified:
    i.pop('_verified', None)

print(json.dumps({
    'valid_verified': valid_verified,
    'valid_unverified': valid_unverified,
    'discarded': discarded,
}, ensure_ascii=False))
```

```bash
VALIDATION_RESULT=$(python3 /tmp/reclassify_valid.py '{validator 응답 JSON}')
VALID_VERIFIED=$(echo $VALIDATION_RESULT | python3 -c "import json,sys; print(json.dumps(json.load(sys.stdin)['valid_verified']))")
VALID_UNVERIFIED=$(echo $VALIDATION_RESULT | python3 -c "import json,sys; print(json.dumps(json.load(sys.stdin)['valid_unverified']))")
DISCARDED=$(echo $VALIDATION_RESULT | python3 -c "import json,sys; print(json.dumps(json.load(sys.stdin)['discarded']))")
DISCARDED_COUNT=$(echo $DISCARDED | python3 -c "import json,sys; print(len(json.load(sys.stdin)))")
```

이후 step 5에서:
- `verified` 대신 `VALID_VERIFIED` 사용
- `unverified` 대신 `VALID_UNVERIFIED` 사용

validator 에이전트 응답 파싱에 실패하면 필터링 없이 기존 verified/unverified를 그대로 사용한다 (안전 fallback).
````

**Step 2: 커밋**

```bash
git add .claude/skills/code-review/SKILL.md
git commit -m "KMA-7277 code-review step 4.6 오탐 필터링 단계 추가"
```

---

### Task 3: SKILL.md — step 5 업데이트

**Files:**
- Modify: `.claude/skills/code-review/SKILL.md`

step 5에서 두 가지를 변경한다:
1. `verified` / `unverified` → `VALID_VERIFIED` / `VALID_UNVERIFIED` 로 교체
2. DISCARDED_COUNT > 0 이면 `<details>` 코멘트 POST 추가

**Step 1: step 5 — 인라인 코멘트 등록 후 discarded 코멘트 추가**

`**2단계: verified 항목을 인라인 코멘트로 개별 등록**` 블록 다음에 아래를 삽입:

````markdown
**3단계: 오탐 필터링 내역 코멘트 등록 (DISCARDED_COUNT > 0인 경우만)**

```bash
# DISCARDED JSON 배열을 마크다운 테이블 행으로 변환
FILTER_TABLE_ROWS=$(echo $DISCARDED | python3 -c "
import json, sys
items = json.load(sys.stdin)
for item in items:
    print(f'| \`{item[\"file\"]}:{item[\"line\"]}\` | {item[\"title\"]} | {item[\"reason\"]} |')
")

FILTER_BODY="<details>
<summary>🤖 AI 오탐 필터링 내역 (리뷰어 전용 — PR 작성자는 무시하셔도 됩니다)</summary>

아래 항목은 오탐으로 판단되어 자동 제거됐습니다.
패턴 등록이 필요하면 \`.claude/agents/\` 에이전트 파일에 추가해 주세요.

| 파일:라인 | 주장 | 제거 이유 |
|-----------|------|-----------|
${FILTER_TABLE_ROWS}

</details>"

# PR 레벨 코멘트로 등록 (인라인 아님)
gh api repos/${REPO}/issues/${PR_NUMBER}/comments \
  --method POST \
  --field body="${FILTER_BODY}"
```
````

**Step 2: step 5 — PR 모드 완료 후 터미널 출력에 필터링 건수 추가**

터미널 출력 섹션의 마지막 (> 🤖 AI Code Review by Claude 이후) 에 조건부 행 추가:

````markdown
{DISCARDED_COUNT > 0인 경우:}
🚫 오탐 필터링: {DISCARDED_COUNT}개 제거됨 (PR 내 접힌 코멘트 참고)
````

**Step 3: 커밋**

```bash
git add .claude/skills/code-review/SKILL.md
git commit -m "KMA-7277 code-review step 5 — discarded 코멘트 POST 및 터미널 요약 추가"
```

---

## 수동 검증 방법

1. 테스트용 PR에서 `/code-review {PR번호}` 실행
2. GitHub PR에서:
   - 인라인 코멘트에 오탐이 없는지 확인
   - `<details>` 접힌 코멘트가 등록됐는지 확인 (오탐이 있었을 경우)
3. 터미널 출력에 `🚫 오탐 필터링: N개` 라인이 표시되는지 확인
4. discarded가 0개인 PR에서는 `<details>` 코멘트가 없는지 확인
