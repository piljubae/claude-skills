# code-review 코멘트 트리거 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** PR 코멘트에 `/code-review`를 달면 GitHub Actions 코드리뷰가 트리거되도록 `code_review.yml`을 수정한다.

**Architecture:** 기존 `pull_request` 트리거에 `issue_comment` 트리거를 추가. 단일 파일(`.github/workflows/code_review.yml`) 4곳 수정. 이벤트 타입에 따라 job 조건과 PR 번호 추출 방식을 분기한다.

**Tech Stack:** GitHub Actions YAML

---

### Task 1: `code_review.yml` 수정

**Files:**
- Modify: `.github/workflows/code_review.yml`

**Step 1: `on:` 섹션에 `issue_comment` 트리거 추가**

```yaml
on:
    pull_request:
        types: [opened, synchronize]
    issue_comment:
        types: [created]
```

**Step 2: concurrency group fallback 추가**

```yaml
concurrency:
    group: claude-review-${{ github.event.pull_request.number || github.event.issue.number }}
    cancel-in-progress: true
```

**Step 3: job `if` 조건을 두 이벤트 타입으로 분기**

```yaml
        if: |
            (github.event_name == 'pull_request' &&
             !startsWith(github.head_ref, 'release/') &&
             !startsWith(github.base_ref, 'growth/') &&
             github.head_ref != 'master' &&
             github.head_ref != 'develop') ||
            (github.event_name == 'issue_comment' &&
             github.event.issue.pull_request != '' &&
             contains(github.event.comment.body, '/code-review'))
```

**Step 4: `Set review prompt` step — PR 번호 추출 변수화**

```yaml
            - name: Set review prompt
              id: prompt
              run: |
                  PR_NUMBER="${{ github.event.pull_request.number || github.event.issue.number }}"
                  if [[ "${{ github.event.action }}" == "synchronize" && "${{ env.REVIEW_MODE }}" == "2" ]]; then
                      echo "value=/code-review ${PR_NUMBER} --since ${{ github.event.before }}" >> $GITHUB_OUTPUT
                  else
                      echo "value=/code-review ${PR_NUMBER}" >> $GITHUB_OUTPUT
                  fi
```

**Step 5: `Claude Code Review` step — `issue_comment` 조건 추가**

```yaml
            - name: Claude Code Review
              if: github.event.action == 'opened' || env.REVIEW_MODE == '1' || env.REVIEW_MODE == '2' || github.event_name == 'issue_comment'
```

`checkout` step은 변경 없음.

**Step 6: YAML 문법 검증**

```bash
# yamllint 또는 actionlint가 있으면 실행
which actionlint && actionlint .github/workflows/code_review.yml || echo "actionlint not installed, skip"
```

**Step 7: 최종 파일 상태 확인 후 커밋**

```bash
cat .github/workflows/code_review.yml
git add .github/workflows/code_review.yml docs/plans/2026-04-16-code-review-comment-trigger-design.md docs/plans/2026-04-16-code-review-comment-trigger.md
git commit -m "KMA-7277 PR 코멘트 /code-review 트리거 추가"
```

---

## 검증 방법

1. develop에 머지 후 아무 PR 코멘트창에 `/code-review` 입력
2. GitHub Actions 탭에서 `Code Review` 워크플로우 실행 확인
3. 서브피처 PR(PR #7425 같은 케이스)에서도 동작 확인
