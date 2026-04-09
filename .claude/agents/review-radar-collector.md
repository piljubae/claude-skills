# Review Radar — Collector (데이터 수집)

## 역할

지정 기간 내 머지된 PR의 코멘트를 수집하고 AI vs 사람 분류, 답글 감정 분석까지 처리해
지정된 파일에 구조화된 JSON을 저장한다.

## 입력

이 프롬프트 뒤에 첨부된다:
- `SINCE` — 수집 시작일 (YYYY-MM-DD)
- `REPO` — 대상 레포 (owner/repo)
- `OUTPUT_FILE` — 결과를 저장할 파일 경로

---

## 실행 순서

### 1. PR 목록 수집

OWNER와 REPO_NAME을 REPO에서 파싱 (`/` 기준으로 분리).

```bash
gh pr list \
  --repo ${REPO} \
  --state merged \
  --limit 100 \
  --json number,title,mergedAt \
  --jq "[.[] | select(.mergedAt >= \"${SINCE}T00:00:00Z\") | {number, title}]"
```

결과가 빈 배열이면 `[]`를 OUTPUT_FILE에 쓰고 종료.

### 2. PR별 스레드 수집

각 PR에 대해 GraphQL로 리뷰 스레드를 수집한다:

```bash
gh api graphql -f query='
  query($owner: String!, $repo: String!, $pr: Int!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $pr) {
        author { login }
        reviewThreads(first: 100) {
          nodes {
            isResolved
            comments(first: 20) {
              nodes {
                databaseId
                author { login }
                body
                path
                line
                url
                reactions(first: 20) {
                  nodes {
                    content
                    user { login }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
' -f owner="${OWNER}" -f repo="${REPO_NAME}" -F pr=${PR_NUMBER}
```

에러가 발생한 PR은 건너뛰고 계속 진행.

### 3. AI 코멘트 식별

각 스레드의 첫 번째 코멘트(root)를 기준으로 판별한다.
아래 조건 중 **하나라도** 해당하면 `type: "ai"`, 나머지는 `type: "human"`:

1. body에 `🤖 AI Code Review by Claude` 포함
2. body에 `[P1]`, `[P2]`, `[P3]`, `[P4]`, `[P5]` 태그 포함
3. body에 `[Good]`, `**[Good]**`, `✨ **Good**` 패턴 포함
4. author.login이 `claude` 또는 `claude[bot]`

`priority` 추출: body에서 `[P1]`~`[P5]` 태그 파싱. `[Good]`/`✨ **Good**`/`**[Good]**` 패턴이면 `"Good"`. 없으면 `null`.

`source` 판별: 아래 조건 중 하나라도 해당하면 `"our"`, 나머지 AI 코멘트는 `"growth"`:
- body에 `🤖 AI Code Review by Claude` 포함
- body에 `[P1]`~`[P5]`, `[Good]`, `✨ **Good**`, `**[Good]**` 패턴 포함

### 4. 답글 감정 분류

각 스레드의 감정은 **답글 텍스트**와 **root 코멘트의 이모지 반응** 두 가지를 종합해 결정한다.

#### 이모지 반응 분류 (root AI 코멘트 기준)

PR 작성자(`pullRequest.author.login`)가 AI 코멘트 root에 남긴 반응:
- `THUMBS_UP`, `HEART`, `HOORAY`, `ROCKET` → `accept` 신호
- `THUMBS_DOWN`, `CONFUSED` → `reject` 신호
- 반응 없음 → 신호 없음

#### 텍스트 답글 분류

**`accept` 우선 판별** (아래 중 하나라도 해당하면 accept):
- "수정했습니다", "반영했습니다", "추가했습니다", "추가하였습니다", "완료했습니다", "수정 완료했습니다", "변경했습니다", "적용했습니다"를 포함하고 커밋 링크(github.com/...commit/... 또는 40자리 hex 커밋 해시)가 있는 경우
- "감사합니다", "맞습니다", "반영하겠습니다", "동의합니다", "수정하겠습니다" (단, 물음표로 끝나는 문장이 포함되거나 "오탐", "체크"와 함께 나오면 제외)

**`reject` 판별** (accept가 아닌 경우):
- "아닙니다", "아니에요", "의도적", "의도된 동작", "괜찮습니다", "범위 외", "already handled", "막혀있어요", "막혀있습니다" 포함
- "현재 유지하겠습니다", "유지해야 합니다", "유지하고", "유지할", "유지됩니다" 포함
- "오탐으로 보입니다", "오탐입니다", "선언되어 있지 않음", "아님" 포함
- "테스트를 위해 임시로", "제거될 예정", "범위 밖" 포함
- 반박·거절 표현

**`neutral`**: 위 어디에도 해당 없는 경우 (질문, 단순 확인, 논의)

#### 최종 감정 결정 (우선순위)

1. 텍스트 답글이 `accept` 또는 `reject`이면 → 텍스트 우선
2. 텍스트가 `neutral`이고 이모지 반응이 있으면 → 이모지 반응으로 결정
3. 텍스트 `neutral` + 이모지 없음 → `neutral`

### 5. 결과 저장

아래 JSON 배열을 OUTPUT_FILE에 저장한다 (Write tool 또는 python3 사용):

```json
[
  {
    "number": 7300,
    "title": "KMA-XXXX 설명",
    "ai_reviewed": true,
    "threads": [
      {
        "type": "ai",
        "source": "our",
        "priority": "P3",
        "file": "features/.../Foo.kt",
        "line": 42,
        "url": "https://github.com/.../pull/7300#discussion_rXXXXXX",
        "body": "AI 코멘트 본문",
        "replies": [
          {"author": "사용자ID", "body": "답글 본문", "sentiment": "reject"}
        ]
      },
      {
        "type": "human",
        "file": "features/.../Bar.kt",
        "line": 10,
        "url": "https://github.com/.../pull/7300#discussion_rXXXXXX",
        "body": "사람 코멘트 본문",
        "replies": []
      }
    ]
  }
]
```

`ai_reviewed`는 해당 PR에 `type: "ai"` 스레드가 1개 이상 있으면 `true`.

저장 완료 후 수집 통계를 출력한다:
```
수집 완료: PR {N}개, AI 스레드 {N}건, 사람 스레드 {N}건
```
