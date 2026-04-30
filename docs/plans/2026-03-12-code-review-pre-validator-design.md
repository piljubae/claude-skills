# Code Review Pre-Validator 설계

**날짜**: 2026-03-12
**목표**: code-review 스킬에 자동 오탐 필터링 단계를 추가하여 PR 작성자에게 오탐 코멘트가 노출되지 않도록 한다.

## 배경

- 현재 code-review가 GitHub에 코멘트를 올린 뒤 사용자가 수동으로 `/validate-review`를 실행해야 오탐을 제거할 수 있다.
- 오탐율 약 10% → PR 10개 코멘트 중 평균 1개가 틀린 코멘트로 PR 작성자에게 노출됨.
- validate-review를 실행하는 것을 사용자가 잊으면 오탐이 그대로 남는다.

## 설계 결정

### 삽입 위치

code-review 스킬의 기존 단계 사이에 `4.6 오탐 필터링`을 삽입한다.

```
4.4 P1/P2 소스 검증
4.5 라인 번호 검증 (diff 기반)
4.6 오탐 필터링 [NEW] ← 여기
5.  결과 출력 (GitHub POST)
```

### 구현 방식: 새 검증 서브에이전트

신규 파일 `.claude/agents/code-reviewer-validator.md`를 생성한다.

**이유:**
- 기존 오탐 패턴 파일 4개(compose / architecture / quality / test)를 context로 주입 가능
- 이슈를 병렬로 검증 가능 → 빠름
- 검증 로직이 SKILL.md 밖에 위치 → 유지보수 용이

### 오탐 판정 기준

| 판정 | 조건 | 처리 |
|------|------|------|
| 명확히 틀림 | 코드 읽었을 때 주장과 실제가 다름 / 기존 오탐 패턴에 해당 | discard |
| 불확실 | 코드로 판단하기 애매함 | valid 유지 (보수적) |
| 맞음 | 실제 코드가 주장을 뒷받침 | valid 유지 |

### 오탐 내역 처리

- discarded 항목은 **GitHub PR에 별도 코멘트로 등록** (`<details>` 접힌 형태)
- PR 작성자가 무시할 수 있도록 명확히 레이블링
- 사용자가 나중에 확인 후 에이전트 파일에 패턴 직접 추가

```markdown
<details>
<summary>🤖 AI 오탐 필터링 내역 (리뷰어 전용 — PR 작성자는 무시하셔도 됩니다)</summary>

| 파일 | 주장 | 제거 이유 |
|------|------|-----------|
| `Foo.kt:45` | MutableState stale capture | `by` delegate 사용으로 해당 없음 |

</details>
```

- discarded 0개이면 이 코멘트는 등록하지 않음.

## 변경 파일

| 파일 | 변경 종류 |
|------|----------|
| `.claude/skills/code-review/SKILL.md` | step 4.6 추가, step 5 출력 변경 |
| `.claude/agents/code-reviewer-validator.md` | 신규 생성 |

## 변경하지 않는 것

- validate-review 스킬: 기존 그대로 유지 (타인 코멘트 검증 등 별도 용도)
- 오탐 패턴 축적: 여전히 사용자가 수동으로 에이전트 파일에 기록

## 기대 효과

- PR 작성자에게 오탐 코멘트 0 노출
- 사용자가 `/validate-review` 실행을 잊어도 문제 없음
- 기존 누적 오탐 패턴 지식이 pre-filtering에 자동 적용
