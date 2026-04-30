# Code Review Agent 개선 리서치

**날짜**: 2026-03-27
**관련 티켓**: KMA-7277
**목적**: 현재 kurly-android `/code-review` 멀티 에이전트 시스템 개선을 위한 외부 원칙 및 내부 스킬 분석

---

## 1. 외부 코드리뷰 원칙 리서치

### 1.1 Conventional Comments

출처: [conventionalcomments.org](https://conventionalcomments.org)

코드 리뷰 코멘트에 레이블을 붙여 의도를 명확히 하는 규격.

| 레이블 | 의미 |
|--------|------|
| `praise` | 칭찬 (행동 불필요) |
| `nitpick` | 사소한 선호 차이 (non-blocking) |
| `suggestion` | 개선 제안 (non-blocking) |
| `issue` | 반드시 수정해야 할 문제 (blocking) |
| `question` | 의도 확인 요청 |
| `thought` | 즉흥적 아이디어 (non-blocking) |
| `chore` | 단순 작업 지시 |

**핵심 인사이트**: blocking vs non-blocking 구분을 코멘트에 명시해야 작성자가 우선순위를 알 수 있다.

**우리 시스템에 적용**: P4/P5 이슈에 `optional:` prefix 추가 → merge 전 필수 처리 항목과 선택 항목 구분

---

### 1.2 Google Engineering Practices

출처: [google.github.io/eng-practices](https://google.github.io/eng-practices/review/)

구글 내부에서 수십 년간 발전시켜온 코드 리뷰 가이드.

**리뷰어 원칙 (핵심):**

- **코드에 대해 말하고 사람에 대해 말하지 않는다** — "이 변수명은 불명확합니다" O, "당신의 명명은 불명확합니다" X
- **칭찬은 좋은 실천을 강화하지만 코드를 대상으로 한다** — "이 패턴 선택이 훌륭합니다" O, "잘 하셨습니다" X
- **명확성이 친절함이다** — 모호한 코멘트보다 직접적인 코멘트가 더 도움됨
- **의도가 불명확하면 단언하지 않고 질문한다** — "이 경우 X가 발생할 수 있는데 의도한 동작인가요?"
- **리뷰어는 설명 책임이 있다** — "왜 이것이 문제인지" 항상 설명

**우리 시스템에 적용**:
- body 작성 가이드에 "의도 불명확 시 질문 형식" 추가
- 추상 표현 대신 결과 직접 묘사 (기존 적용 완료)

---

### 1.3 GitHub Copilot Code Review 원칙

출처: GitHub 공식 문서 / GitHub Next 리서치

AI 코드 리뷰 에이전트 설계 원칙.

**핵심 원칙:**

- **80% 확신 임계값** — 해당 코드에서 실제 문제가 발생한다는 것을 80% 이상 확신할 때만 이슈 제기. 낮으면 올리지 않는다.
- **근거 중심** — 모든 이슈에 diff에서 직접 확인 가능한 근거 필요
- **False positive 비용** — 잘못된 이슈 1개가 맞는 이슈 3개의 신뢰도를 떨어뜨린다
- **컨텍스트 우선** — AI가 모르는 맥락이 있을 수 있음을 항상 인지

**우리 시스템에 적용**:
- `공통 검증 원칙`에 이슈 제기 절제 원칙 추가
- "이럴 수도 있다" 수준은 이슈가 아님 명시

---

### 1.4 Microsoft Research — AI Code Review

출처: Microsoft Research 논문 (2024)

AI 코드 리뷰 도구의 실사용자 반응 연구.

**핵심 발견:**

- **작성자는 AI의 칭찬 코멘트를 가치 있게 여기지 않는다** — 칭찬은 불필요하거나 오히려 방해
- **작성자가 가장 가치 있게 여기는 것**: P1/P2 실제 버그 발견
- **신뢰도**: AI가 칭찬을 많이 할수록 전체 신뢰도 하락 ("칭찬만 하는 AI"로 인식)
- **PR 당 코멘트 밀도**: 너무 많은 코멘트는 작성자의 집중력을 분산시킴 (파일 당 평균 1~2개 권장)

**우리 시스템에 적용**:
- `[Good]` 코멘트 대폭 축소: PR 전체 최대 1건, 단순 패턴 준수는 해당 없음
- 이슈 수 절제

---

### 1.5 PR 코멘트 밀도 벤치마크

리서치에서 수집된 실제 데이터:

| 지표 | 권장 |
|------|------|
| PR 당 총 코멘트 | 5~10개 이하 |
| 파일 당 평균 코멘트 | 1~2개 |
| P1/P2 비율 | 전체의 20~30% |
| `[Good]` 코멘트 | PR 당 0~1개 |

---

## 2. 내부 스킬 분석 (superpowers)

### 2.1 분석 대상

superpowers marketplace의 `code-reviewer` 관련 스킬 파일들 분석.

### 2.2 발견된 비대칭 문제

**`receiving-code-review` 스킬 (리뷰 받는 쪽):**
- "AI 리뷰어는 틀릴 수 있다 — 기술적 사실부터 확인하라"
- "칭찬 코멘트는 무시해도 된다"
- "AI 제안을 무조건 따르지 마라"
- 엄격한 no-praise 규칙 포함

**`code-reviewer` 스킬 (리뷰 하는 쪽):**
- `[Good]` 코멘트 횟수 제한 없음
- 칭찬 기준 불명확
- false positive 방지 규칙 미흡

→ **결론**: 받는 쪽은 AI 칭찬을 신뢰하지 말라고 하면서, 하는 쪽은 칭찬을 많이 생성했다. 구조적 모순.

### 2.3 적용 사항

이 비대칭을 해소하기 위해 code-reviewer 측을 강화.

---

## 3. 적용 결과 요약

### 3.1 이번 세션에서 변경된 파일

| 파일 | 변경 내용 |
|------|-----------|
| `code-reviewer-master.md` | 공통 검증 원칙 + 이슈 절제 / body 가이드 + optional: / 질문 형식 / good[] 예시 교체 / Step 5 필터링 로직 |
| `code-reviewer-adversary.md` | good[] 판단 기준 강화 (방어 코드만) |
| `code-reviewer-architecture.md` | good[] 주의사항 강화 / 예시 → `"good": []` |
| `code-reviewer-compose.md` | good[] 주의사항 강화 / 예시 → `"good": []` |
| `code-reviewer-test.md` | good[] 주의사항 강화 / 예시 → `"good": []` |

### 3.2 변경 원칙 매핑

| 변경 | 원칙 출처 |
|------|-----------|
| `[Good]` PR 당 최대 1건 | Microsoft Research + 내부 비대칭 분석 |
| `optional:` prefix (P4/P5) | Conventional Comments non-blocking |
| 이슈 제기 절제 원칙 | GitHub Copilot 80% confidence |
| 질문 형식 (의도 불명확 시) | Google Engineering Practices |
| 단순 패턴 준수 good 금지 | Microsoft Research (AI praise 가치 없음) |
| good[] 예시 교체 | 예시가 기준과 모순되어 LLM 오학습 방지 |

---

## 4. 미적용 항목 (향후 검토)

### 4.1 PR 코멘트 밀도 제어

현재는 이슈 수 제한 없음. 추후 "파일 당 최대 X건" 규칙 추가 고려.

리스크: 실제 P1/P2가 많은 PR에서 제한이 걸리는 문제 → 우선순위 기반 제한 (P3 이하만 제한) 검토.

### 4.2 Conventional Comments 완전 적용

현재는 P4/P5에만 `optional:` 적용. Conventional Comments 전체 레이블 체계 도입은 출력 포맷 변경이 필요하여 별도 검토.

### 4.3 "코드 vs 사람" 언어 규칙

body 작성 가이드에 "코드를 지적하고 사람을 지적하지 않는다" 명시적 규칙 추가 검토.

---

## 5. 다음 단계

- [ ] 실제 PR에서 개선된 리뷰 품질 검증 (PR #7294 기준)
- [ ] 프롬프트 개발자 루프 설계: 리뷰 결과 → 문제 진단 → 프롬프트 개선 → 반복
- [ ] PR 당 코멘트 밀도 측정 및 벤치마크 수립
