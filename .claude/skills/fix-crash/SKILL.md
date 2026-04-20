# /fix-crash 스킬

크래시 티켓을 단일 세션 TDD 방식으로 수정한다.
에이전트 없음 — 탐색부터 커밋까지 같은 세션에서 컨텍스트를 유지하며 진행.

---

## 사용법

```
/fix-crash KMA-XXXX
```

---

## 실행 흐름

```
[Phase 0] 티켓 읽기
    ↓
[Phase 1] 탐색 — Grep/Read로 크래시 위치 특정
    ↓
[Phase 2] 분석 — 근본 원인 + 재현 경로
    ↓
✋ CP1: 분석 승인
    ↓
[Phase 3] 실패 테스트 작성 (FAIL 확인)
    ├─ ViewModel/UseCase → 단위 테스트 (3-B)
    └─ Activity/Fragment → Instrumented Test (3-C)
    ↓
✋ CP2: 실패 테스트 확인
    ↓
[Phase 4] 수정 (PASS 확인 + 컴파일 검증)
    ↓
✋ CP3: diff 확인 → 커밋 + PR
```

---

## 상세 절차

### Phase 0: 티켓 읽기

`getJiraIssue` (cloudId: `kurly0521.atlassian.net`). 추출:
- 크래시 클래스/메서드명
- 수정 방향 (있는 경우)
- Firebase 크래시 URL (있는 경우 — `/report-crash` 미실행 시 참고용)

### Phase 1: 탐색

직접 도구 사용:
1. CRASH_SUMMARY에서 클래스명/메서드명 키워드 추출
2. Grep으로 코드베이스 검색
3. Read로 관련 파일 열어 문제 코드 블록 특정
4. Fragment/Activity 관계라면 상위 호출자까지 추적

### Phase 2: 분석

Phase 1 결과를 이어받아:
1. 크래시 발생 조건 특정
2. 인과관계 정리
3. 수정 가능 여부: **FIXABLE** / **ESCALATE**
4. 재현 경로 도출 (Given / When / Then)
5. 구체적 수정 방법 (파일:라인 + 변경 내용)

### ✋ CP1: 분석 승인

```
## 원인 분석 + 재현 경로

[근본 원인 / 발생 조건 / 재현 경로 / 수정 방법 요약]

[Enter] 진행  [e] 수정  [s] 중단
```

ESCALATE 시:
```
⚠️ 앱 레벨 수정 제한적: <이유>
[Enter] Jira 코멘트 등록 후 종료  [s] 그냥 종료
```

### Phase 3: 실패 테스트 작성

> **⛔ 이 Phase는 스킵 불가.** "View 레이어라 테스트 의미 없음" 등의 이유로 건너뛰지 않는다.
> 크래시 수정의 회귀 방지는 테스트로만 보장된다. 테스트 없는 수정은 Phase 4로 진행할 수 없다.

#### 3-A: 테스트 전략 판단

| 크래시 위치 | 테스트 전략 |
|------------|------------|
| ViewModel / UseCase / Repository | **단위 테스트** (BaseMockKTest) → 3-B |
| Activity / Fragment (FragmentManager, View 직접 참조) | **Instrumented Test** → 3-C |
| Custom View / 라이브러리 래퍼 (ViewPager, RecyclerView 등) | **Robolectric 단위 테스트** → 3-D |
| ANR (성능 문제) | **Instrumented Test + assertion** → 3-E |

어떤 레이어든 테스트 가능한 형태가 반드시 존재한다. 크래시 재현이 어려우면 **방어 코드의 동작을 검증**하는 테스트를 작성한다.

#### 3-B: 단위 테스트 (ViewModel/UseCase/Repository)

`.claude/rules/testing.md` 규칙:
- 한글 백틱 메서드명, Given-When-Then
- `BaseMockKTest` / `BaseContextMockkTest` 상속
- `runTest`, `advanceUntilIdle`

```bash
./gradlew :<module>:testDebugUnitTest --tests "패키지.클래스명.테스트명"
```

#### 3-C: Instrumented Test (Activity/Fragment 레이어)

파일 위치: `app/src/androidTest/java/.../MainActivityTest.kt`

**주의사항 (파일럿에서 발견):**

1. **메서드명 공백 불가** — DEX 제약으로 백틱 메서드명의 공백 금지. camelCase 사용:
   ```kotlin
   // Bad:  fun `LOUNGE 탭에서 뒤로가기가 크래시 없이 처리된다`()
   // Good: fun onBackPressed_whenLoungeTab_doesNotCrash()
   ```

2. **Fragment 트랜잭션** — `onActivity {}` 내에서 `commitNow()` 대신 `commitNowAllowingStateLoss()` 사용:
   ```kotlin
   activity.supportFragmentManager.beginTransaction()
       .replace(R.id.content, Fragment())
       .commitNowAllowingStateLoss()   // commitNow()는 onSaveInstanceState 후 예외
   ```

3. **코루틴 타이밍 활용** — `onActivity {}` 블록은 메인 스레드 동기 실행.
   `lifecycleScope.launch { }` 코루틴은 블록 종료 후 실행됨.
   → 탭 전환 후 Fragment 교체(코루틴)보다 `commitNowAllowingStateLoss()`가 먼저 실행됨을 활용:
   ```kotlin
   activityScenarioRule.scenario.onActivity { activity ->
       navView.selectTab(TAB_INDEX_LOUNGE)          // replaceFragment 코루틴 큐잉
       fragmentManager.beginTransaction()
           .replace(R.id.content, Fragment())
           .commitNowAllowingStateLoss()             // 코루틴보다 먼저 실행
       activity.onBackPressed()                      // 크래시 재현
   }
   ```

실행:
```bash
./gradlew :app:connectedStoreDebugAndroidTest \
  -Pandroid.testInstrumentationRunnerArguments.class=com.dbs.kurly.m2.MainActivityTest#테스트명
```

FAIL → 정상 / PASS → 재현 실패, 테스트 수정 필요

#### 3-D: Robolectric 단위 테스트 (Custom View / 라이브러리 래퍼)

커스텀 View의 방어 코드(try-catch, null 체크 등)가 동작하는지 검증한다.

```kotlin
// 예: ViewPager 멀티터치 방어 코드 검증
@RunWith(RobolectricTestRunner::class)
class TouchEventErrorHandledViewPagerTest {

    @Test
    fun onInterceptTouchEvent_whenExceptionThrown_returnsFalseWithoutCrash() {
        val viewPager = spy(TouchEventErrorHandledViewPager(context))
        // super.onInterceptTouchEvent가 예외를 던지도록 설정
        doThrow(IllegalArgumentException("pointerIndex out of range"))
            .whenever(viewPager).callSuperOnInterceptTouchEvent(any())
        
        val result = viewPager.onInterceptTouchEvent(motionEvent)
        assertThat(result).isFalse()  // 크래시 없이 false 반환
    }
}
```

직접 재현이 어려우면 **방어 코드의 catch 경로**를 검증하는 것으로 충분하다.
단, 크래시 시나리오를 Given/When/Then 주석으로 명시한다.

#### 3-E: ANR 검증 (Instrumented Test + assertion)

ANR은 타이밍 재현이 불가하므로, **원인 제거를 간접 검증**한다:

| ANR 원인 | 검증 방법 |
|----------|----------|
| wrap_content로 전체 ViewHolder inflation | ViewHolder 생성 수 ≤ 화면에 보이는 수 + cache 크기 assertion |
| 메인 스레드 blocking I/O | StrictMode 또는 메인 스레드 실행 시간 assertion |
| 과도한 레이아웃 패스 | OnGlobalLayoutListener count assertion |

```kotlin
// 예: RecyclerView가 전체 아이템을 한 번에 inflate하지 않는지 검증
@Test
fun onCreateViewHolder_whenLargeDataSet_doesNotInflateAllAtOnce() {
    // Given: 50개 아이템 submitList
    // When: 첫 레이아웃 완료
    // Then: 생성된 ViewHolder 수 < 전체 아이템 수
}
```

FAIL → 정상 / PASS → 재현 실패, 테스트 수정 필요

### ✋ CP2: 실패 테스트 확인

```
## 크래시 재현 테스트 (현재 FAIL)

[테스트 코드 + 실행 결과]

[Enter] 확인, 수정으로 진행  [e] 테스트 재작성  [s] 중단
```

### Phase 4: 수정

1. 대상 파일 Read (필수) → Edit으로 최소 범위 수정
2. 테스트 재실행 → PASS 확인
3. 컴파일 검증: `./gradlew :<module>:compileDebugKotlin`
4. 실패 시 재수정 (최대 3회)

수정 원칙:
- 최소 변경 — 실패 테스트만 통과시킨다
- `as` → `as?` + null 처리
- YAGNI

### ✋ CP3: 수정 확인 + 커밋 + PR

```
## 수정 결과

[diff + 테스트 PASS + 컴파일 SUCCESS]

[Enter] 커밋 + PR  [c] 커밋만  [e] 수정 변경  [s] 중단
```

커밋:
```bash
git add <수정 파일> <테스트 파일>
git commit -m "<TICKET_KEY> <크래시 수정 요약>"
```
PR: `/create-pr` 실행

---

## 참고

- `/report-crash` — 수정 전 티켓 본문 채우기
- `/write-test` — 테스트 작성 규칙
- `/create-pr` — PR 생성
- `.claude/rules/testing.md`, `.claude/rules/android-architecture.md`
