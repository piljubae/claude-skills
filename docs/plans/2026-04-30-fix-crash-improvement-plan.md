# fix-crash 스킬 개선 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** `~/.claude/skills/fix-crash/SKILL.md`를 설계 문서 기반으로 재작성하여 크래시 분석→재현→수정의 목적을 실제로 달성하도록 개선

**Architecture:** 타입 분기(T1~T5) + CP 필수 항목 템플릿 + CI 모드 추가. 기존 Phase 4/CP3는 변경 없음.

**Tech Stack:** Markdown, Jira MCP (`lookupJiraAccountId`, `editJiraIssue`), git CLI

**설계 문서:** `docs/plans/2026-04-30-fix-crash-improvement-design.md`

---

### Task 1: Phase 0 — 브래드크럼 추출 + 타입 판별

**Files:**
- Modify: `~/.claude/skills/fix-crash/SKILL.md` (Phase 0 섹션)

**Step 1:** 현재 Phase 0 Read로 읽기, 추출 항목 확인

**Step 2:** Phase 0를 아래 내용으로 교체

```markdown
### Phase 0: 티켓 읽기

getJiraIssue (cloudId: kurly0521.atlassian.net). 추출:
- 크래시 클래스/메서드명
- 스택 트레이스 전문
- 브래드크럼 (report-crash가 넣어둔 경우)
- Firebase 크래시 URL
- 수정 방향 힌트 (있는 경우)

#### 타입 판별 (T1~T5)
스택 트레이스 + 크래시 키워드로 결정:

| 타입 | 판별 키워드 |
|------|-----------|
| T1. Null/Type | NullPointerException, ClassCastException, `!!` |
| T2. 생명주기 | IllegalStateException, onSaveInstanceState, FragmentManager, ActivityNotFound |
| T3. 동시성/스레드 | CalledFromWrongThreadException, ConcurrentModificationException, MotionEvent |
| T4. ANR | ANR, Application Not Responding, blamed=TRUE |
| T5. Native/3rd-party | JNI, Chromium, NDK, 외부 SDK 패키지명 |

#### 브래드크럼 유무에 따른 Phase 1 출발점
- **있음**: 브래드크럼 → 재현 경로 가설 → 코드 탐색으로 검증
- **없음**: 스택 트레이스 → crash point → 역방향 탐색
```

**Step 3:** 저장 후 통독 — 기존 내용과 충돌 없는지 확인

---

### Task 2: Phase 1 — 타입별 탐색 체크리스트 + 담당자 식별

**Files:**
- Modify: `~/.claude/skills/fix-crash/SKILL.md` (Phase 1 섹션 전면 교체)

**Step 1:** 기존 Phase 1 섹션 전체를 아래로 교체

```markdown
### Phase 1: 탐색

#### 공통 (모든 타입)
- [ ] 스택 트레이스에서 crash point 특정 (파일:라인)
- [ ] `git blame <파일> -L <라인>,<라인>` → 최근 변경자 확인

#### 담당자 식별
최근 6개월 커밋 빈도 기준 상위 후보 도출:
```bash
git log --follow --pretty=format:"%ae" --since="6 months ago" <파일> \
  | sort | uniq -c | sort -rn | head -3
```
- **로컬**: 상위 3명 보여주고 사람이 선택
- **CI**: 커밋 빈도 1위 자동 선택 → Jira 담당자 변경 (Phase 2 완료 후)

#### T1. Null/Type
- [ ] null 유입 레이어 특정: 서버 응답? DI 주입 순서? 생명주기 타이밍?
- [ ] ClassCast: 실제 타입이 언제 바뀌는지 (다형성? 제네릭 erasure? BackStack 재사용?)
- [ ] `!!` 위치 + null이 될 수 있는 조건

#### T2. 생명주기
- [ ] crash point에서 생명주기 상태 확인 (`isStateSaved`, `isAdded`, `isDetached`)
- [ ] 호출을 트리거한 상위 원인 역추적 (코루틴? 콜백? 딜레이?)
- [ ] 관련 Fragment/AndroidX AOSP 소스 확인 (`cs.android.com`)

#### T3. 동시성/스레드
- [ ] crash 시점 스레드명 확인 (스택 트레이스)
- [ ] 공유 상태(mutable)가 어디에 있는지
- [ ] 관련 framework 코드 확인 (ViewRootImpl, MotionEvent 등)

#### T4. ANR
- [ ] blamed thread 스택 전문 확인
- [ ] 메인 스레드 블로킹 지점 식별 (I/O? 락? inflation?)
- [ ] 발생 기기/OS 패턴 (저사양? 특정 버전?)
- [ ] DI/초기화 관련이라면 생성 코드 확인

#### T5. Native/3rd-party
- [ ] SDK GitHub Issues / 릴리즈 노트 먼저 확인 (알려진 버그?)
- [ ] 우리 코드에서 크래시를 유발하는 API 호출/상태 특정
- [ ] 버전별 재현 여부 (Android 버전, SDK 버전)
```

**Step 2:** 저장 후 흐름 다이어그램과 일치하는지 확인

---

### Task 3: Phase 2 + CP1 — 수정 옵션 2-3개 + 타입별 필수 항목

**Files:**
- Modify: `~/.claude/skills/fix-crash/SKILL.md` (Phase 2, CP1 섹션)

**Step 1:** Phase 2에 타입별 추가 분석 항목 삽입

기존 수정 전략 우선순위 표는 유지하되 역할 설명 변경:
> "수정 방향 옵션을 2-3개 도출할 때 이 우선순위를 참고한다. 높은 순위 전략이 가능한지 먼저 검토."

타입별 추가 분석:
- **T2**: 생명주기 상태 + SDK 동작 근거 명시
- **T3**: 타이밍 다이어그램 (스레드 A → 스레드 B 경쟁 경로)
- **T4**: blamed thread 블로킹 원인 + 기기/OS 패턴
- **T5**: SDK 이슈 트래커 링크 + workaround 가능 여부

**Step 2:** CP1 템플릿 교체

```markdown
### ✋ CP1: 분석 승인

미입력 항목이 있으면 CP1 통과 불가.

## 크래시 분석 (CP1)

### 공통
- 크래시 한 줄 요약:
- 발생 경로: [브래드크럼 기반 / 코드 역추적]
- 문제 코드: <파일:라인>
- 담당자 후보: (로컬: 선택 / CI: 1위 자동)
- 재현 조건:
  - Given:
  - When:
  - Then (크래시 발생):

### 수정 방향 옵션 (2-3개 필수)
- Option A: [전략명] — 방법 / 장점 / 단점
- Option B: [전략명] — 방법 / 장점 / 단점
- Option C: [전략명] — 방법 / 장점 / 단점 (있는 경우)
→ 추천: Option X (이유)

### T1 추가
- null/타입 오류 유입 레이어:

### T2 추가
- crash 시점 생명주기 상태:
- 호출 트리거:
- SDK 근거:

### T3 추가
- 충돌 스레드:
- 타이밍 다이어그램:
- SDK 근거:

### T4 추가
- blamed thread 스택:
- 블로킹 지점 + 원인:
- 발생 패턴 (기기/OS):

### T5 추가
- 유발 조건:
- SDK 이슈 링크:
- 버전별 재현:

[로컬] [Enter] 추천 채택  [b] 다른 옵션 선택  [e] 수정  [s] 중단
[CI]   추천 옵션 자동 선택 → 진행

ESCALATE 시:
⚠️ 앱 레벨 수정 제한적: <이유>
담당자: <식별된 담당자>
[Enter] Jira 코멘트 등록 후 종료  [s] 그냥 종료
```

---

### Task 4: Phase 3 + CP2 — 타입별 테스트 + 재현형/조건검증형

**Files:**
- Modify: `~/.claude/skills/fix-crash/SKILL.md` (Phase 3, CP2 섹션)

**Step 1:** Phase 3 3-A 표를 타입별 테스트 레벨 매트릭스로 교체

```markdown
#### 3-A: 타입별 테스트 전략

| 타입 | 테스트 레벨 | 전략 | 재현 가능 |
|------|------------|------|----------|
| T1. Null/Type | Unit Test | null/타입 조건 재현 → exception throw 확인 | 재현형 |
| T2. 생명주기 | Instrumented Test | 생명주기 상태 재현 → exception throw 확인 | 재현형 |
| T3. 동시성 | Robolectric 시도 → 실패 시 Instrumented | 재현 성공: exception 확인 / 실패: 방어 코드 동작 검증 + Instrumented 보완 필수 | 재현형 or 조건 검증형 |
| T4. ANR | Instrumented + 필요 시 Macrobenchmark | 재현 불가 → 블로킹 원인 제거 간접 검증 | 조건 검증형 |
| T5. Native/3rd-party | Unit / Robolectric | 재현 불가 → 유발 조건 부재 검증 | 조건 검증형 |
```

**Step 2:** CP2 템플릿 업데이트

```markdown
### ✋ CP2: 실패 테스트 확인

## 크래시 재현 테스트 (CP2)

- 테스트 전략: [재현형 / 조건 검증형]
- FAIL 의미: [exception 재현 성공 / 유발 조건 존재 확인]
- 테스트 코드 + 실행 결과 (FAIL 로그)
- Mutation Spot-Check: 방어 코드 제거 → FAIL 확인 → 원복

[Enter] 확인, 수정으로 진행  [e] 테스트 재작성  [s] 중단
```

---

### Task 5: CI 모드 섹션 추가

**Files:**
- Modify: `~/.claude/skills/fix-crash/SKILL.md` (하단 신규 섹션)

**Step 1:** `## CI 모드` 섹션을 `## 참고` 위에 추가

```markdown
## CI 모드

**감지**: `$CI` 환경변수 있으면 자동 / 또는 명시: `/fix-crash KMA-XXXX --ci`

**흐름**:
```
Phase 0~1: 동일 (자동 실행)
Phase 2: 옵션 2-3개 도출 → 추천 옵션 자동 선택 (CP1 스킵)
담당자: 커밋 빈도 1위 → lookupJiraAccountId → editJiraIssue(assignee)
Phase 3: 실패 테스트 작성 → FAIL 확인 (CP2 스킵)
Phase 4: 수정 → PASS → /commit → /create-pr (CP3 스킵)
```

**CI PR description 포함 항목**:
- 타입 / 근본 원인 / 재현 조건 (Given/When/Then)
- 수정 방향 옵션 A/B/C + 선택 근거
- 테스트 결과 (재현형/조건 검증형, FAIL→PASS)
- 변경 파일 목록
```

---

### Task 6: 실행 흐름 다이어그램 업데이트 + 통독 + 커밋

**Files:**
- Modify: `~/.claude/skills/fix-crash/SKILL.md` (상단 흐름 다이어그램)

**Step 1:** 상단 흐름 다이어그램에 타입 판별 + CI 모드 분기 반영

**Step 2:** 전체 통독 — 설계 문서(`docs/plans/2026-04-30-fix-crash-improvement-design.md`)와 대조, 누락/충돌 확인

**Step 3:** `/commit` 으로 커밋
