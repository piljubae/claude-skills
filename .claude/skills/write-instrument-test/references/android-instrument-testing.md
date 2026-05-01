# Android Instrumented Test Rules

Kurly Android instrumented test 작성 기준.
`/write-instrument-test` 스킬의 본체. SKILL.md 는 이 파일을 읽고 실행한다.

외부 레퍼런스:
- [Compose UI Testing](https://developer.android.com/develop/ui/compose/testing)
- [Compose Testing APIs](https://developer.android.com/develop/ui/compose/testing/apis)
- [Compose Test Synchronization](https://developer.android.com/develop/ui/compose/testing/synchronization)
- [Hilt Testing](https://developer.android.com/training/dependency-injection/hilt-testing)
- [Now in Android 샘플](https://github.com/android/nowinandroid)

---

## 1. 범위 — Instrumented Test가 필요한 경우

| 검증 대상 | Instrumented | Local Unit Test |
|-----------|-------------|-----------------|
| Composable 렌더링 (UiState별 UI 상태) | ✅ | ❌ |
| 클릭 → 콜백 호출 | ✅ | ❌ |
| 스크롤 impression 타이밍 (발화 억제 포함) | ✅ | ❌ |
| Room DAO, DataStore | ✅ | ❌ |
| ViewModel 상태 전환 / 이벤트 발화 | ❌ | ✅ (mockk) |
| Amplitude 이벤트 프로퍼티 검증 | ❌ | ✅ (mockk) |
| UseCase / Repository 로직 | ❌ | ✅ |

> **원칙:** Composable이 올바르게 보이고 올바르게 반응하는지 검증한다.
> Analytics 이벤트 프로퍼티는 ViewModel 단위 테스트에서 검증한다.

---

## 2. ComposeTestRule 선택 기준

| 상황 | 사용할 Rule |
|------|------------|
| Composable 단독 렌더링 검증 (UiState 직접 주입) | `createAndroidComposeRule<ComponentActivity>()` |
| `R.string` 등 string resource 비교 필요 | `createAndroidComposeRule<ComponentActivity>()` |
| 스크롤/터치/`mainClock` 제어 필요 | `createAndroidComposeRule<ComponentActivity>()` |
| XML View + Compose 혼재 Activity 테스트 | `createEmptyComposeRule()` + `ActivityScenario` |
| 전체 앱 네비게이션 E2E | `createAndroidComposeRule<MainActivity>()` + `@HiltAndroidTest` |

> `createComposeRule()`은 사용하지 않는다. `createAndroidComposeRule<ComponentActivity>()`가
> string resource 접근 포함 모든 케이스를 커버하고, Activity 의존성도 최소화된다.

```kotlin
// Good: ComponentActivity 기반 (Kurly 표준)
@get:Rule
val composeTestRule = createAndroidComposeRule<ComponentActivity>()

// Bad: createComposeRule — string resource 접근 불가
@get:Rule
val composeTestRule = createComposeRule()
```

---

## 3. 기본 패턴 — UiState 직접 주입 (Hilt 없음)

ViewModel을 배제하고 Composable에 UiState를 직접 주입한다.
가장 빠르고 안정적. Feature 화면 단독 테스트 표준 패턴.

```kotlin
@RunWith(AndroidJUnit4::class)
class ProductDetailScreenTest {

    @get:Rule
    val composeTestRule = createAndroidComposeRule<ComponentActivity>()

    @Test
    fun `로딩 상태에서 로딩 인디케이터가 표시된다`() {
        composeTestRule.setContent {
            KurlyTheme {
                ProductDetailScreen(
                    uiState = ProductDetailUiState(isLoading = true),
                    onAction = {},
                )
            }
        }
        val loading = composeTestRule.activity.getString(R.string.loading)
        composeTestRule.onNodeWithContentDescription(loading).assertIsDisplayed()
    }

    @Test
    fun `품절 상품은 장바구니 버튼이 비활성화된다`() {
        composeTestRule.setContent {
            KurlyTheme {
                ProductDetailScreen(
                    uiState = ProductDetailUiState(
                        product = Product.DUMMY.copy(isSoldOut = true),
                    ),
                    onAction = {},
                )
            }
        }
        composeTestRule
            .onNodeWithText(composeTestRule.activity.getString(R.string.add_to_cart))
            .assertIsNotEnabled()
    }

    @Test
    fun `상품 클릭 시 onAction이 호출된다`() {
        var clickedId: String? = null
        composeTestRule.setContent {
            KurlyTheme {
                ProductCard(
                    product = Product.DUMMY,
                    onProductClick = { clickedId = it },
                )
            }
        }
        composeTestRule.onNodeWithTag("product_card_${Product.DUMMY.id}").performClick()
        assertEquals(Product.DUMMY.id, clickedId)
    }
}
```

---

## 4. 스크롤 Impression 타이밍 검증 — mainClock 패턴

스크롤 중 impression 억제, 디바운스 타이밍 등 시간 제어가 필요한 경우.
`FakeAnalyticsEventConsumer`를 Composable에 직접 주입하여 이벤트 발화 여부만 검증한다.
(프로퍼티 내용은 ViewModel 단위 테스트에서 검증)

```kotlin
@RunWith(AndroidJUnit4::class)
class BannerImpressionScrollTest {

    @get:Rule
    val composeTestRule = createAndroidComposeRule<ComponentActivity>()

    private val fakeConsumer = FakeAnalyticsEventConsumer()

    @Test
    fun `스크롤 중에는 impression 이벤트가 발화되지 않는다`() {
        composeTestRule.mainClock.autoAdvance = false

        composeTestRule.setContent {
            KurlyTheme {
                BannerContent(
                    banners = BannerFixtures.list,
                    consumer = fakeConsumer,
                )
            }
        }

        // 초기 impression 소화
        composeTestRule.mainClock.advanceTimeBy(2_000)
        fakeConsumer.sentEvents.clear()

        // 손가락을 떼지 않은 채 스크롤 (isScrollInProgress = true 유지)
        composeTestRule.onRoot().performTouchInput {
            down(center)
            moveTo(center + Offset(0f, -400f))
        }
        composeTestRule.mainClock.advanceTimeBy(300)

        assertTrue("스크롤 중 impression 없어야 함", fakeConsumer.sentEvents.isEmpty())

        // 손가락 뗀 후 impression 발화 확인
        composeTestRule.onRoot().performTouchInput { up() }
        composeTestRule.mainClock.advanceTimeBy(2_000)

        assertTrue("스크롤 종료 후 impression 발화", fakeConsumer.sentEvents.isNotEmpty())
    }
}
```

**주의:** `mainClock.autoAdvance = false` 설정 시 `waitForIdle()`도 시간을 자동 진행하지 않는다.
`advanceTimeBy()` 로 프레임을 명시적으로 제어해야 한다.

---

## 5. 의존성 체크리스트 (신규 모듈에 추가할 때)

```kotlin
// build.gradle.kts
androidTestImplementation(libs.androidx.compose.ui.test.junit4)
debugImplementation(libs.androidx.compose.ui.test.manifest)  // 필수 — 없으면 빌드 오류
androidTestImplementation(libs.mockk.android)                // mock 필요 시
```

> `ui-test-manifest`는 `createComposeRule()` / `createAndroidComposeRule()` 사용 시 반드시 필요.
> 누락 시 `android:exported` manifest merge 오류 발생.

현재 `:features`, `:app` 모듈에만 선언되어 있다. 신규 모듈에 Compose UI Test 추가 시 위 3줄 필수.

---

## 6. 테스트 네이밍

로컬 단위 테스트와 동일하게 한글 백틱 메서드명 사용. 화면 상태 / 인터랙션 기준으로 작성.

```kotlin
@Test fun `로딩 상태에서 로딩 인디케이터가 표시된다`()
@Test fun `빈 목록일 때 빈 화면 안내 문구가 표시된다`()
@Test fun `에러 상태에서 재시도 버튼이 표시된다`()
@Test fun `상품 클릭 시 onProductClick이 호출된다`()
@Test fun `스크롤 중에는 impression이 발화되지 않는다`()
```

---

## 7. 피해야 할 패턴

```kotlin
// Bad: Thread.sleep — Flaky 테스트 원인
Thread.sleep(3000)
// Good: waitUntil 또는 mainClock.advanceTimeBy 사용
composeTestRule.waitUntil(5_000) { condition }

// Bad: ViewModel을 Composable에 직접 주입
composeTestRule.setContent {
    ProductScreen(viewModel = hiltViewModel())  // Hilt 설정 없으면 크래시
}
// Good: UiState 직접 주입
composeTestRule.setContent {
    ProductScreen(uiState = ProductUiState.DUMMY, onAction = {})
}

// Bad: Amplitude 이벤트 프로퍼티를 instrumented test에서 검증
assertTrue(fakeConsumer.sentEvents.first().properties["placement_id"] == "1")
// Good: 발화 여부 / 타이밍만 검증. 프로퍼티는 ViewModel 단위 테스트에서 검증
assertTrue(fakeConsumer.sentEvents.isNotEmpty())

// Bad: KurlyTheme 없이 Composable 렌더링
composeTestRule.setContent { ProductCard(...) }
// Good: KurlyTheme 래핑 필수
composeTestRule.setContent { KurlyTheme { ProductCard(...) } }

// Bad: createComposeRule (string resource 접근 불가)
val composeTestRule = createComposeRule()
// Good
val composeTestRule = createAndroidComposeRule<ComponentActivity>()
```

---

## 8. assertIsDisplayed() vs assertExists() 구분

| 메서드 | 의미 | 사용 시점 |
|--------|------|-----------|
| `assertIsDisplayed()` | 화면에 실제로 보임 (뷰포트 내) | 사용자에게 보여야 하는 요소 검증 |
| `assertExists()` | Semantics 트리에 존재 (화면 밖 가능) | LazyColumn 미스크롤 아이템, 숨겨진 요소 |
| `assertDoesNotExist()` | 트리에 없음 | 조건부 노출 요소가 숨겨졌는지 검증 |

```kotlin
// Good: 화면에 보여야 하는 경우
composeTestRule.onNodeWithText("장바구니 담기").assertIsDisplayed()

// Good: LazyColumn에서 아직 스크롤 안 된 아이템 존재 여부만 확인
composeTestRule.onNodeWithTag("item_99").assertExists()

// Good: 조건부 컴포넌트가 완전히 제거되었는지 확인
composeTestRule.onNodeWithText("광고 배지").assertDoesNotExist()

// Bad: 화면 밖 아이템에 assertIsDisplayed() → 항상 실패
composeTestRule.onNodeWithTag("item_99").assertIsDisplayed()
```

---

## 9. 접근성 / Semantics 검증 패턴

Compose Semantics 트리 = TalkBack 데이터 소스 = 테스트 트리. 접근성 검증 = 테스트 가능성 검증.

```kotlin
// 1. 인터랙티브 요소에 클릭 액션 존재
composeTestRule
    .onNodeWithText("구매하기")
    .assert(hasClickAction())

// 2. 비활성 상태 semantics 전달
composeTestRule
    .onNodeWithText("품절")
    .assertIsNotEnabled()

// 3. 로딩 인디케이터 semantics
composeTestRule
    .onNode(hasProgressBarRangeInfo(ProgressBarRangeInfo.Indeterminate))
    .assertIsDisplayed()

// 4. contentDescription으로 노드 탐색 (이미지 버튼 등)
composeTestRule
    .onNodeWithContentDescription("장바구니 담기")
    .assertIsDisplayed()
    .assert(hasClickAction())

// 5. 체크박스/스위치 선택 상태
composeTestRule
    .onNodeWithTag("alarm_toggle")
    .assertIsToggleable()
    .assertIsOff()
```

**접근성 시나리오 체크리스트:**
- [ ] 모든 클릭 가능한 요소 → `hasClickAction()` 또는 `contentDescription` 존재
- [ ] 비활성 버튼 → `assertIsNotEnabled()`
- [ ] 로딩 인디케이터 → `hasProgressBarRangeInfo(Indeterminate)`
- [ ] 장식용 이미지 → contentDescription 없음 (`assertDoesNotExist()` 로 확인)

---

## 10. 상태 전이 검증 패턴

UI 상태를 유한 상태 기계로 보고 전이 경로를 검증. `mutableStateOf` 로 상태를 바꿔가며 재검증.

```kotlin
@Test
fun `로딩 완료 후 데이터가 표시되고 로딩 인디케이터가 사라진다`() {
    var uiState by mutableStateOf<ProductUiState>(ProductUiState(isLoading = true))

    composeTestRule.setContent {
        KurlyTheme {
            ProductScreen(uiState = uiState, onAction = {})
        }
    }

    // Loading 상태 검증
    composeTestRule
        .onNode(hasProgressBarRangeInfo(ProgressBarRangeInfo.Indeterminate))
        .assertIsDisplayed()

    // Success 상태로 전이
    uiState = ProductUiState(product = Product.DUMMY)
    composeTestRule.waitForIdle()

    // 로딩 사라지고 데이터 표시
    composeTestRule
        .onNode(hasProgressBarRangeInfo(ProgressBarRangeInfo.Indeterminate))
        .assertDoesNotExist()
    composeTestRule.onNodeWithText(Product.DUMMY.name).assertIsDisplayed()
}

@Test
fun `에러 상태에서 재시도 클릭 시 로딩 상태로 전이된다`() {
    var uiState by mutableStateOf<ProductUiState>(ProductUiState(error = "네트워크 오류"))
    var retryClicked = false

    composeTestRule.setContent {
        KurlyTheme {
            ProductScreen(uiState = uiState, onAction = { action ->
                if (action is ProductAction.Retry) {
                    retryClicked = true
                    uiState = ProductUiState(isLoading = true)
                }
            })
        }
    }

    composeTestRule.onNodeWithText("재시도").performClick()
    composeTestRule.waitForIdle()

    assertTrue(retryClicked)
    composeTestRule
        .onNode(hasProgressBarRangeInfo(ProgressBarRangeInfo.Indeterminate))
        .assertIsDisplayed()
}
```

---

## 11. LazyColumn — performScrollToNode

LazyColumn 아이템은 화면 밖이면 Compose 트리에 없을 수 있다. 스크롤 후 접근해야 한다.

```kotlin
// 특정 아이템까지 스크롤 후 검증
composeTestRule
    .onNodeWithTag("product_list")
    .performScrollToNode(hasText("마지막 상품"))

composeTestRule
    .onNodeWithText("마지막 상품")
    .assertIsDisplayed()

// index 기반 스크롤
composeTestRule
    .onNodeWithTag("product_list")
    .performScrollToIndex(49)

// useUnmergedTree: 병합 트리에 안 보이는 자식 노드 접근
composeTestRule
    .onNodeWithText("할인가", useUnmergedTree = true)
    .assertIsDisplayed()
```

> LazyColumn에 `Modifier.testTag("list_tag")` 지정 필수.

---

## 12. waitUntil — Compose 클럭 외부 비동기 대기

네트워크/DB 등 Compose 가상 클럭 밖의 비동기 작업 완료 대기.
`Thread.sleep` 대신 반드시 사용.

```kotlin
// 조건이 충족될 때까지 최대 5초 대기
composeTestRule.waitUntil(timeoutMillis = 5_000L) {
    composeTestRule
        .onAllNodesWithTag("product_item")
        .fetchSemanticsNodes().isNotEmpty()
}

// 편의 메서드 (Compose 1.5+)
composeTestRule.waitUntilAtLeastOneExists(
    matcher = hasTestTag("product_item"),
    timeoutMillis = 5_000L,
)
composeTestRule.waitUntilDoesNotExist(
    matcher = hasProgressBarRangeInfo(ProgressBarRangeInfo.Indeterminate),
    timeoutMillis = 5_000L,
)
```

> `mainClock.autoAdvance = false` 상태에서는 `waitUntil` 도 자동으로 시간을 진행하지 않는다.
> impression 타이밍 테스트처럼 클럭을 수동 제어하는 경우 `advanceTimeBy()` 를 사용한다.

---

## 13. String Resource 위임 프로퍼티 패턴

`createAndroidComposeRule<ComponentActivity>()` 사용 시 string resource를 깔끔하게 참조하는 패턴.

```kotlin
// 방법 1: activity.getString() 직접 호출
val label = composeTestRule.activity.getString(R.string.add_to_cart)
composeTestRule.onNodeWithText(label).assertIsDisplayed()

// 방법 2: 위임 프로퍼티 (Now in Android 패턴) — 여러 번 쓸 때 권장
private val addToCart by lazy {
    composeTestRule.activity.getString(R.string.add_to_cart)
}
private val soldOut by lazy {
    composeTestRule.activity.getString(R.string.sold_out)
}

@Test
fun `품절 상품은 품절 버튼이 표시된다`() {
    composeTestRule.setContent { /* ... */ }
    composeTestRule.onNodeWithText(soldOut).assertIsDisplayed()
    composeTestRule.onNodeWithText(addToCart).assertDoesNotExist()
}
```

> `activity` 프로퍼티는 `setContent {}` 호출 이후에만 접근 가능.
> `@get:Rule` 선언 시점에는 접근하면 안 되므로 `by lazy` 또는 테스트 메서드 내부에서 호출한다.
