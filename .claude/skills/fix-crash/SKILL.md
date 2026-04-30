# /fix-crash 스킬

크래시 티켓을 단일 세션 TDD 방식으로 수정한다.
에이전트 없음 — 탐색부터 커밋까지 같은 세션에서 컨텍스트를 유지하며 진행.

---

## 사용법

```
/fix-crash KMA-XXXX          # 로컬 (CP 대화형)
/fix-crash KMA-XXXX --ci     # CI 모드 (CP 스킵, 자동 완주)
```

---

## 실행 흐름

```
[Phase 0] 티켓 읽기
    │  · 브래드크럼 추출 (있으면)
    │  · 타입 판별: T1 Null/Type | T2 생명주기 | T3 동시성 | T4 ANR | T5 Native/3rd-party
    ↓
[Phase 1] 탐색
    │  · 공통: crash point 특정 + git blame
    │  · 담당자 식별 (git log 빈도 기반)
    │  · 타입별 체크리스트 (T1~T5)
    ↓
[Phase 2] 분석
    │  · 타입별 추가 분석 (생명주기 상태, 타이밍 다이어그램, blamed thread, SDK 이슈 등)
    │  · 수정 방향 옵션 2-3개 도출
    ↓
✋ CP1: 분석 승인  ← [로컬] 사람이 옵션 선택 / [CI] 추천 자동 선택 + Jira 담당자 변경
    ↓
[Phase 3] 실패 테스트 작성 (FAIL 확인)
    │  T1 → Unit (3-B) / 재현형
    │  T2 → Instrumented (3-C) / 재현형
    │  T3 → Robolectric (3-D) → 필요 시 Instrumented (3-C) / 재현형 or 조건검증형
    │  T4 → Instrumented (3-E) + Macrobenchmark / 조건검증형
    └─ T5 → Unit / Robolectric (3-F) / 조건검증형
    ↓
✋ CP2: 실패 테스트 확인  ← [로컬] 사람이 확인 / [CI] 자동 통과
    ↓
[Phase 4] 수정 (PASS 확인 + 컴파일 검증)
    ↓
✋ CP3: diff 확인 → /commit + /create-pr  ← [CI] 자동 실행
```

---

## 상세 절차

### Phase 0: 티켓 읽기

`getJiraIssue` (cloudId: `kurly0521.atlassian.net`). 추출:
- 크래시 클래스/메서드명
- 스택 트레이스 전문
- 브래드크럼 (report-crash가 Jira 설명에 삽입한 사용자 행동 흐름; 없으면 생략)
- Firebase 크래시 URL
- 수정 방향 힌트 (있는 경우)

#### 타입 판별 (T1~T5)

스택 트레이스 + 크래시 키워드로 결정:

| 타입 | 판별 키워드 |
|------|-----------|
| T1. Null/Type | NullPointerException, ClassCastException, `!!` 강제 언랩 |
| T2. 생명주기 | IllegalStateException, onSaveInstanceState, FragmentManager |
| T3. 동시성/스레드 | CalledFromWrongThreadException, ConcurrentModificationException, MotionEvent, wrong thread |
| T4. ANR | ANR, Application Not Responding, blamed=TRUE |
| T5. Native/3rd-party | JNI, Chromium, NDK, 외부 SDK 패키지명 |

#### 브래드크럼 유무에 따른 Phase 1 출발점

- **있음**: 브래드크럼 → 재현 경로 가설 → 코드 탐색으로 검증
- **없음**: 스택 트레이스 → crash point → 역방향 탐색

### Phase 1: 탐색

#### 공통 (모든 타입)
- [ ] 스택 트레이스에서 crash point 특정 (파일:라인)
- [ ] `git blame <파일> -L <라인>,<라인>` → 최근 변경자 확인

#### 담당자 식별

최근 6개월 커밋 빈도 기준 상위 후보 도출:

```bash
git log --follow --pretty=format:"%ae" --since="6 months ago" <파일> \
  | grep -v "bot\|noreply\|github-actions" \
  | sort | uniq -c | sort -rn | head -3
# 결과 없으면 --since 제거 후 재실행 (전체 이력 기준)
```

- **로컬**: 상위 3명 보여주고 사람이 선택 → CP1에 기록
- **CI**: 커밋 빈도 1위 자동 선택 → Jira 담당자 변경은 CP1 이후에 처리

#### T1. Null/Type
- [ ] null 유입 레이어 특정: 서버 응답? DI 주입 순서? 생명주기 타이밍?
- [ ] ClassCast: 실제 타입이 언제 바뀌는지 (다형성? 제네릭 erasure? BackStack 재사용?)
- [ ] `!!` 위치 + null이 될 수 있는 조건

#### T2. 생명주기
- [ ] crash point에서 생명주기 상태 확인 (`isStateSaved`, `isAdded`, `isDetached`)
- [ ] 호출을 트리거한 상위 원인 역추적 (코루틴? 콜백? 딜레이?)
- [ ] `cs.android.com`에서 crash point 메서드 소스 확인 — 내부적으로 어떤 상태 조건을 검사하는지 파악 (예: `checkStateLoss()`, `isStateSaved()` 호출 여부)

#### T3. 동시성/스레드
- [ ] crash 시점 스레드명 확인 (스택 트레이스)
- [ ] 공유 상태(mutable)가 어디에 있는지
- [ ] 관련 framework 코드 확인 (ViewRootImpl, MotionEvent 등)

#### T4. ANR
- [ ] blamed thread 스택 전문 확인
- [ ] 메인 스레드 블로킹 지점 식별 (I/O? 락? inflation?)
- [ ] Phase 0에서 수집한 Firebase 크래시 URL에서 기기/OS 분포 확인 (저사양 집중? 특정 Android 버전?)
- [ ] blamed thread 스택에 `Hilt`, `@Inject`, `Application.onCreate`, `DataBinderMapperImpl` 등이 보이면 DI/초기화 생성 코드 확인

#### T5. Native/3rd-party
- [ ] SDK GitHub Issues / 릴리즈 노트 먼저 확인 (알려진 버그?)
- [ ] 우리 코드에서 크래시를 유발하는 API 호출/상태 특정
- [ ] 버전별 재현 여부 (Android 버전, SDK 버전)

### Phase 2: 분석

Phase 1 결과를 이어받아:
1. 크래시 발생 조건 특정
2. 인과관계 정리
3. 수정 가능 여부: **FIXABLE** / **ESCALATE**
4. 재현 경로 도출 (Given / When / Then)
5. **수정 방향 탐색** — 아래 우선순위로 검토 후 선택 근거를 CP1에 명시:

> 수정 방향 옵션을 2-3개 도출할 때 이 우선순위표를 참고한다. 높은 순위 전략이 가능한지 먼저 검토한 후, 가능한 것들 중 2-3개 옵션을 CP1에 제시한다.

#### 수정 전략 우선순위 (높은 순)

| 순위 | 전략 | 설명 | 예시 |
|------|------|------|------|
| 1 | **아키텍처 수정** | 크래시가 발생할 수 없는 구조로 변경 | ViewPager → ViewPager2 전환, wrap_content → 고정 높이 |
| 2 | **흐름 제어** | 크래시 도달 경로를 상위에서 차단 | null 체크 조기 반환, 상태 검증 guard |
| 3 | **타입/null 안전** | 타입 시스템으로 방어 | `as` → `as?`, non-null assertion 제거 |
| 4 | **방어 코드 (try-catch)** | 예외를 catch하여 graceful 처리 | 마지막 수단 — 위 전략이 불가할 때만 |

> **⛔ try-catch는 마지막 수단이다.** 순위 1~3으로 해결 가능한지 먼저 탐색한다.
> try-catch를 선택할 경우, 상위 전략이 불가한 이유를 CP1에 명시해야 한다.

6. 구체적 수정 방법 (파일:라인 + 변경 내용 + 선택 전략 번호)

#### 타입별 추가 분석

**T2 (생명주기)**: 생명주기 상태 + 호출 트리거 + SDK 동작 근거를 명시. AOSP 소스에서 확인한 내부 조건 포함.

**T3 (동시성/스레드)**: 타이밍 다이어그램 작성. 형식:
```
스레드 A: [액션1] ──→ [공유 상태 접근]
스레드 B:          [액션2] ──→ [공유 상태 접근] → 크래시
```

**T4 (ANR)**: blamed thread 블로킹 원인 + 기기/OS 패턴 명시.

**T5 (Native/3rd-party)**: SDK 이슈 트래커 링크 + workaround 가능 여부 명시.

### ✋ CP1: 분석 승인

미입력 항목이 있으면 CP1 통과 불가. 해당 타입 추가 섹션만 작성 — 나머지 타입 섹션은 생략한다.

```
## 크래시 분석 (CP1)

### 공통
- 크래시 한 줄 요약:
- 발생 경로: [브래드크럼 기반 / 코드 역추적]
- 문제 코드: <파일:라인>
- 담당자 후보: [로컬: 상위 3명 중 선택 / CI: 커밋 빈도 1위 자동]
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
- SDK 근거 (AOSP 확인 내용):

### T3 추가 (Phase 2에서 작성한 타이밍 다이어그램을 여기에 포함)
- 충돌 스레드:
- 타이밍 다이어그램:
- SDK/framework 근거:

### T4 추가
- blamed thread 스택:
- 블로킹 지점 + 원인:
- 발생 패턴 (기기/OS):

### T5 추가
- 유발 조건 (우리 코드):
- SDK 이슈 링크:
- 버전별 재현:
```

[로컬] [Enter] 추천 채택  [b] 다른 옵션 선택  [e] 수정  [s] 중단
[CI]   추천 옵션 자동 선택 → 진행

ESCALATE 시:
```
⚠️ 앱 레벨 수정 제한적: <이유>
담당자: <식별된 담당자>
[Enter] Jira 코멘트 등록 후 종료  [s] 그냥 종료
```

### Phase 3: 실패 테스트 작성

> **⛔ 이 Phase는 스킵 불가.** "View 레이어라 테스트 의미 없음" 등의 이유로 건너뛰지 않는다.
> 크래시 수정의 회귀 방지는 테스트로만 보장된다. 테스트 없는 수정은 Phase 4로 진행할 수 없다.

#### 3-A: 타입별 테스트 전략

| 타입 | 테스트 레벨 | 전략 | 재현 가능 |
|------|------------|------|----------|
| T1. Null/Type | Unit Test (3-B) | null/타입 조건 재현 → exception throw 확인 | 재현형 |
| T2. 생명주기 | Instrumented Test (3-C) | 생명주기 상태 재현 → exception throw 확인 | 재현형 |
| T3. 동시성/스레드 | Robolectric 시도 (3-D) → 실패 시 Instrumented (3-C) | 재현 성공: exception 확인 / 실패: 방어 코드 동작 검증 + Instrumented 보완 필수 | 재현형 or 조건 검증형 |
| T4. ANR | Instrumented (3-E) + 필요 시 Macrobenchmark | 재현 불가 → 블로킹 원인 제거 간접 검증 | 조건 검증형 |
| T5. Native/3rd-party | Unit / Robolectric (3-F) | 재현 불가 → 유발 조건 부재 검증 | 조건 검증형 |

#### Robolectric 한계 시 UI 테스트 보완

Robolectric(3-D)은 JVM에서 View를 시뮬레이션하므로, 실제 터치 이벤트 디스패치·레이아웃 패스 등에서
프로덕션과 다르게 동작할 수 있다. **Mutation Spot-Check에서 방어 코드 제거 후에도 테스트가 PASS하면**
Robolectric 한계로 판단하고 아래 순서로 보완한다:

1. Robolectric 테스트는 **검증 가능한 경로만 유지** (삭제하지 않음)
2. 검증 불가 경로에 대해 **Instrumented UI 테스트(3-C)를 추가** 작성
3. UI 테스트를 작성할 수 없는 환경이면 **PR Test plan에 수동 검증 항목으로 명시**

> 교훈: KMA-7591에서 `onTouchEvent` try-catch는 Robolectric으로 크래시 재현 불가했으나,
> `onInterceptTouchEvent`는 재현 성공. 같은 클래스라도 메서드별로 Robolectric 커버리지가 다를 수 있다.

#### 테스트 공통 원칙

모든 테스트는 아래 두 가지를 따른다:
- **`.claude/rules/testing.md`** — 기술 스택, 코루틴, Assertion, Mock 전략, 금지 패턴
- **`/write-test` 스킬** — Test List 구조, Mutation Spot-Check

크래시 테스트에서도 `/write-test`의 핵심을 적용한다:
1. **Test List 먼저 출력** — 테스트 코드 작성 전에 검증 항목을 나열
2. **Given-When-Then** — 크래시 시나리오를 명확히 기술
3. **Mutation Spot-Check** — 핵심 방어 코드 1개 제거 → 테스트 FAIL 확인 → 원복

#### 3-B: 단위 테스트 (ViewModel/UseCase/Repository)

- 한글 백틱 메서드명, Given-When-Then
- `BaseMockKTest` / `BaseContextMockkTest` 상속
- `runTest`, `advanceUntilIdle`

```bash
./gradlew :<module>:testStoreDebugUnitTest --tests "패키지.클래스명.테스트명"
# 플레이버 없는 모듈은 testDebugUnitTest 사용. 모호성 오류 발생 시 testStoreDebugUnitTest로 폴백.
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

**주의사항: Robolectric + MockK 제네릭 타입**

제네릭 반환 타입이 있는 메서드에 `mockk(relaxed = true)` 사용 시
Robolectric 샌드박스 클래스 로더와 충돌로 ClassCastException 발생 가능:
```
FeatureValue$Subclass8 cannot be cast to MyFeature$Value
```
제네릭 반환 타입 메서드는 반드시 명시적으로 stub한다:
```kotlin
// Bad
val manager = mockk<ABTestManager>(relaxed = true)

// Good
val manager = mockk<ABTestManager>().also {
    every { it.getValue<MyFeature.Value>(FeatureKeys.MY_KEY) } returns null
}
```

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

#### 3-F: 조건 검증 테스트 (Native / 3rd-party 크래시)

크래시가 Chromium·NDK·JNI 등 외부 코드에서 발생해 JVM에서 재현 불가한 경우.
**"크래시를 유발하는 조건이 우리 코드에 존재하지 않음"을 assertion으로 검증**한다.

```kotlin
// 예: LAYER_TYPE_HARDWARE 설정 시 Chromium GPU 크래시 (KMA-7160)
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [30])
class WebViewLayerTypeTest {

    @Test
    fun `initWebView 기본값으로 호출 시 LAYER_TYPE_HARDWARE가 설정되지 않아야 한다`() {
        // Given: 기본값으로 초기화
        val webView = WebView(context)

        // When
        webViewFacade.initWebView(webView)

        // Then: 크래시 조건 부재 검증 (재현이 아닌 방어 확인)
        assertNotEquals(View.LAYER_TYPE_HARDWARE, webView.layerType)
    }
}
```

Mutation Spot-Check: 방어 코드 제거 → assertion FAIL 확인 → 원복.

### ✋ CP2: 실패 테스트 확인

```
## 크래시 재현 테스트 (CP2)

- 테스트 전략: [재현형 / 조건 검증형]
- FAIL 의미: [exception 재현 성공 / 유발 조건 존재 확인 / T3 Robolectric 한계 시: 방어 코드 동작 간접 검증]
- 테스트 코드 + 실행 결과 (FAIL 로그)
- Mutation Spot-Check: 방어 코드 제거 → FAIL 확인 → 원복
```

[Enter] 확인, 수정으로 진행  [e] 테스트 재작성  [s] 중단

### Phase 4: 수정

1. 대상 파일 Read (필수) → Edit으로 최소 범위 수정
2. 테스트 재실행 → PASS 확인
3. 컴파일 검증: `./gradlew :<module>:compileDebugKotlin`
4. 실패 시 재수정 (최대 3회)

수정 원칙:
- Phase 2에서 선택한 전략 우선순위를 따른다
- 최소 변경 — 실패 테스트만 통과시킨다
- YAGNI — 크래시 수정 범위를 벗어나는 개선 금지

### ✋ CP3: 수정 확인 + 커밋 + PR

```
## 수정 결과

[diff + 테스트 PASS + 컴파일 SUCCESS]

[Enter] 커밋 + PR  [c] 커밋만  [e] 수정 변경  [s] 중단
```

커밋: `/commit` 실행
PR: `/create-pr` 실행

---

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

---

## 참고

- `/report-crash` — 수정 전 티켓 본문 채우기
- `/write-test` — 테스트 작성 규칙
- `/create-pr` — PR 생성
- `.claude/rules/testing.md`, `.claude/rules/android-architecture.md`
