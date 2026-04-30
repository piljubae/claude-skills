# Design: `/code-review` 코멘트 트리거 추가

- **Date**: 2026-04-16
- **File**: `.github/workflows/code_review.yml`

## 배경

서브피처 브랜치(feature → feature) PR은 `code_review.yml`이 없는 head 브랜치를 참조하므로
자동 트리거가 누락된다. 코멘트로 온디맨드 재실행이 가능해야 한다.

## 변경 범위

`code_review.yml` 단일 파일 수정 (4곳).

---

## 1. 트리거 & Concurrency

```yaml
on:
    pull_request:
        types: [opened, synchronize]
    issue_comment:
        types: [created]

concurrency:
    group: claude-review-${{ github.event.pull_request.number || github.event.issue.number }}
    cancel-in-progress: true
```

- `issue_comment` 트리거 추가
- concurrency group에 `|| github.event.issue.number` fallback 추가

## 2. Job `if` 조건

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

## 3. PR 번호 추출

```yaml
PR_NUMBER="${{ github.event.pull_request.number || github.event.issue.number }}"
```

## 4. Review step `if` 조건

```yaml
if: |
    github.event.action == 'opened' ||
    env.REVIEW_MODE == '1' ||
    env.REVIEW_MODE == '2' ||
    github.event_name == 'issue_comment'
```

`checkout` step은 변경 없음 (issue_comment는 GitHub API로 diff 처리).

---

## 서브피처 브랜치 문제 자동 해결

`issue_comment` 이벤트는 항상 default 브랜치(develop)의 workflow 파일을 읽으므로,
head 브랜치에 `code_review.yml`이 없어도 코멘트 트리거로 실행 가능.
