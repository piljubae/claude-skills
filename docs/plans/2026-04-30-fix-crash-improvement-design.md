# fix-crash 스킬 개선 설계

- **Date**: 2026-04-30
- **Status**: Approved
- **Scope**: `~/.claude/skills/fix-crash/SKILL.md`

---

## 문제 정의

현재 스킬은 크래시의 근본 원인 분석 → 재현 경로 도출 → 테스트 → 수정이라는 목적을
달성하지 못하고 있다. 주요 실패 원인:

1. 크래시 성격(타입)에 관계없이 탐색 경로가 동일 → 피상적 분석
2. CP1에서 사용자가 분석의 정확성을 판단할 근거 부족
3. 브래드크럼 등 재현 경로 힌트를 활용하지 않음
4. 타입별 적절한 테스트 레벨 / 재현 전략이 없음

---

## 크래시 타입 분류 (T1~T5)

실제 KMA-6390 하위 티켓 기반으로 도출.

| 타입 | 대표 예시 | 특징 |
|------|----------|------|
| **T1. Null/Type** | NPE, ClassCast, `!!` | null 유입 레이어 역추적 |
| **T2. 생명주기** | onSaveInstanceState, FragmentStateManager, ActivityNotFound | 호출 타이밍 + 상위 트리거 역추적 |
| **T3. 동시성/스레드** | wrong thread, MotionEvent, LayoutNode | 공유 상태 + 접근 스레드 경쟁 경로 |
| **T4. ANR** | onCreateViewHolder, DataBinderMapperImpl | blamed thread 블로킹 지점 |
| **T5. Native/3rd-party** | Chromium JNI, AppsFlyer, DNS | 우리 코드의 유발 조건 탐색 |

---

## 설계

### Phase 0: 티켓 읽기 (개선)

기존 추출 항목에 추가:
- **브래드크럼**: Jira description에서 추출 (report-crash가 넣어둔 경우)
- **타입 판별**: 스택 트레이스 + 크래시 키워드로 T1~T5 결정

브래드크럼 유무에 따라 Phase 1 출발점이 달라짐:
- **있음**: 브래드크럼 → 재현 경로 가설 → 코드 탐색으로 검증
- **없음**: 스택 트레이스 → crash point → 역방향 탐색

---

### Phase 1: 타입별 탐색 체크리스트 (신규)

#### 공통 (모든 타입)
- [ ] 스택 트레이스에서 crash point 특정 (파일:라인)
- [ ] `git blame <파일> -L <라인>` → 최근 변경자 확인
  - 도메인 컨텍스트 필요 시 확인 대상
  - ESCALATE 시 에스컬레이션 대상

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

---

### Phase 2: 타입별 분석 (개선)

기존 분석 항목 유지 + 타입별 추가 항목:

**T2 추가**: 생명주기 상태 + SDK 동작 근거 명시
**T3 추가**: 타이밍 다이어그램 (스레드 A → 스레드 B 경쟁 경로)
**T4 추가**: blamed thread 블로킹 원인 + 기기/OS 패턴
**T5 추가**: SDK 이슈 트래커 링크 + workaround 가능 여부

---

### Phase 1: 담당자 식별 (공통 — 신규)

git blame 기반 + 최근 6개월 커밋 빈도로 상위 후보 도출:

```bash
# 해당 라인 최근 변경자
git blame <파일> -L <라인>,<라인> --porcelain | grep "^author-mail"

# 해당 파일 최근 6개월 기여자 (커밋 횟수 순)
git log --follow --pretty=format:"%ae" --since="6 months ago" <파일> \
  | sort | uniq -c | sort -rn | head -3
```

- **로컬**: 상위 3명 보여주고 사람이 선택
- **CI**: 커밋 횟수 1위 자동 선택 → Jira 담당자 변경 + PR 태그

---

### CP1: 타입별 필수 항목 템플릿 (신규)

미입력 항목이 있으면 CP1 통과 불가.

```
## 크래시 분석 (CP1)

### 공통
- 크래시 한 줄 요약:
- 발생 경로: [브래드크럼 기반 / 코드 역추적]
- 문제 코드: <파일:라인>
- 담당자 후보: <git log 상위 3명> (로컬: 선택 / CI: 1위 자동)
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
```

---

### Phase 3: 타입별 테스트 전략 (개선)

| 타입 | 테스트 레벨 | 전략 |
|------|------------|------|
| T1 | Unit Test | null/타입 조건 재현 → exception throw 확인 (재현형) |
| T2 | Instrumented Test | 생명주기 상태 재현 → exception throw 확인 (재현형) |
| T3 | Robolectric 시도 → 실패 시 Instrumented | 재현 성공: exception 확인 / 실패: 방어 코드 동작 검증 (조건 검증형) + Instrumented 보완 필수 |
| T4 | Instrumented + 필요 시 Macrobenchmark | 재현 불가 → 블로킹 원인 제거 간접 검증 (조건 검증형) |
| T5 | Unit / Robolectric | 재현 불가 → 유발 조건 부재 검증 (조건 검증형) |

---

### CP2: 업데이트 (개선)

```
## 크래시 재현 테스트 (CP2)

- 테스트 전략: [재현형 / 조건 검증형]
- FAIL 의미: [exception 재현 성공 / 유발 조건 존재 확인]
- 테스트 코드 + 실행 결과 (FAIL 스크린샷 or 로그)
- Mutation Spot-Check: 방어 코드 제거 → FAIL 확인 → 원복

[Enter] 확인, 수정으로 진행  [e] 테스트 재작성  [s] 중단
```

---

### CI 모드 (신규)

**감지**: `$CI` 환경변수 or `--ci` 플래그

**흐름**:
```
Phase 0~1: 동일 (자동 실행)
Phase 2: 옵션 2-3개 도출 → 추천 옵션 자동 선택 (CP1 스킵)
Phase 1 담당자: 커밋 빈도 1위 자동 선택
  → lookupJiraAccountId(이메일) → editJiraIssue(assignee)
Phase 3: 실패 테스트 작성 → FAIL 확인 (CP2 스킵)
Phase 4: 수정 → PASS → 커밋 → /create-pr 자동 실행 (CP3 스킵)
```

**CI PR description 포함 항목**:
```
## 크래시 분석
- 타입 / 근본 원인 / 재현 조건 (Given/When/Then)

## 수정 방향
- Option A: ... / Option B: ...
- 선택: Option X (이유)

## 테스트 결과
- 전략: [재현형 / 조건 검증형]
- FAIL → PASS 확인

## 변경 파일
```

---

## 변경 범위

| 섹션 | 변경 |
|------|------|
| Phase 0 | 브래드크럼 추출, 타입 판별 추가 |
| Phase 1 | 전면 재작성 — 공통 + 타입별 체크리스트 + 담당자 식별 |
| Phase 2 | 타입별 추가 분석 항목 + 수정 옵션 2-3개 필수 |
| CP1 | 타입별 필수 항목 템플릿 + 수정 옵션 선택 |
| Phase 3 | 타입별 테스트 레벨 + 재현형/조건 검증형 명시 |
| CP2 | 재현형/조건 검증형 + Mutation Spot-Check 명시 |
| Phase 4 | 변경 없음 |
| CP3 | 변경 없음 |
| CI 모드 | 신규 — 전 Phase 자동화 + Jira 담당자 변경 + PR 자동 생성 |
