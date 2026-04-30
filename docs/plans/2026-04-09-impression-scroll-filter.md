# Impression Scroll Filter Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Compose 기반 impression 이벤트가 스크롤 중에 발화되지 않도록 `filterImpressionsByScrollState`를 QuickMenu와 EventBanner에 적용하고, Compose Instrumented 테스트로 동작을 검증한다.

**Architecture:** 이미 작성된 순수 함수 `filterImpressionsByScrollState(isScrollInProgress, visibleItems)`를 Compose impression 발화 로직에 연결한다. 테스트를 위해 private composable을 `internal QuickMenuSectionContent` 래퍼로 노출하고, `FakeAnalyticsEventConsumer`로 발화된 이벤트를 기록한다.

**Tech Stack:** Kotlin, Jetpack Compose, `createAndroidComposeRule<ComponentActivity>()`, `kotlinx.collections.immutable`

---

## Task 1: 기존 미커밋 작업 커밋

**Files:**
- Commit: `features/src/main/java/com/kurly/features/event/EventUtils.kt`
- Commit: `features/src/test/java/com/kurly/features/event/ImpressionScrollFilterTest.kt`

**Step 1: 변경 내용 확인**

```bash
git diff HEAD -- features/src/main/java/com/kurly/features/event/EventUtils.kt
```

Expected: `filterImpressionsByScrollState` 함수 추가 확인 (8줄 추가)

**Step 2: 단위 테스트 실행**

```bash
./gradlew :features:testDebugUnitTest --tests "com.kurly.features.event.ImpressionScrollFilterTest"
```

Expected: `BUILD SUCCESSFUL`, 4개 테스트 통과

**Step 3: 커밋**

```bash
git add features/src/main/java/com/kurly/features/event/EventUtils.kt
git add features/src/test/java/com/kurly/features/event/ImpressionScrollFilterTest.kt
git commit -m "KMA-6460 스크롤 중 impression 필터링 유틸 함수 추가"
```

---

## Task 2: FakeAnalyticsEventConsumer 생성

테스트에서 전송된 이벤트를 기록하기 위한 Fake.

**Files:**
- Create: `features/src/androidTest/java/com/kurly/features/FakeAnalyticsEventConsumer.kt`

**Step 1: 파일 생성**

```kotlin
package com.kurly.features

import com.kurly.core.event.AnalyticsEvent
import com.kurly.core.event.AnalyticsEventIdentifier
import com.kurly.core.recyclerview.impression.consumer.AnalyticsEventConsumer

class FakeAnalyticsEventConsumer : AnalyticsEventConsumer {
    val sentEvents = mutableListOf<AnalyticsEvent>()

    override fun send(events: List<AnalyticsEvent>) { sentEvents += events }
    override fun send(event: AnalyticsEvent?) { event?.let { sentEvents += it } }
    override fun markConsumed(event: AnalyticsEvent): Boolean = false
    override fun clearAnalyticsEventHeap() { sentEvents.clear() }
    override fun history(): List<AnalyticsEventIdentifier> = emptyList()
    override fun removeAnalyticsEvent(identifier: AnalyticsEventIdentifier) { /* no-op */ }
}
```

**Step 2: 컴파일 확인**

```bash
./gradlew :features:compileDebugAndroidTestKotlin
```

Expected: `BUILD SUCCESSFUL`

---

## Task 3: QuickMenuSectionContent internal 래퍼 추출 (리팩토링)

**Files:**
- Modify: `features/src/main/java/com/kurly/features/home/recommend/section/viewholder/section/QuickMenuSectionViewHolder.kt`

`private fun SendAmplitudeComposable(...)` 앞(라인 384 위)에 새 `internal` 함수를 추가하고, ViewHolder의 `setContent {}` 본문을 이 함수로 위임한다.

**Step 1: `QuickMenuSectionContent` 함수 추가 (라인 382 앞에 삽입)**

```kotlin
@Composable
internal fun QuickMenuSectionContent(
    menus: ImmutableList<SectionBannerItemUIModel>,
    listState: LazyGridState,
    consumer: AnalyticsEventConsumer,
    rowCount: Int,
    isScrollable: Boolean,
    themePosition: Int,
    sectionWrapper: SectionWrapper<out MainSection>,
    panelType: PanelUIType,
    combinePosition: (Int, Int) -> String,
    sendImpressionEntireEvent: () -> Unit,
    navigateBannerLink: (QuickMenuSectionItemUIModel) -> Unit,
    sendSelectRecommendationAmplitude: (QuickMenuSectionItemUIModel, Int, Int) -> Unit,
) {
    SendAmplitudeComposable(
        menus = menus,
        listState = listState,
        consumer = consumer,
        themePosition = themePosition,
        sectionWrapper = sectionWrapper,
        panelType = panelType,
        combinePosition = combinePosition,
        sendImpressionEntireEvent = sendImpressionEntireEvent,
    )
    KurlyTheme(darkTheme = false) {
        QuickMenuSection(
            rowCount = rowCount,
            isScrollable = isScrollable,
            menus = menus,
            listState = listState,
            navigateBannerLink = navigateBannerLink,
            sendSelectRecommendationAmplitude = sendSelectRecommendationAmplitude,
        )
    }
}
```

**Step 2: ViewHolder의 `setContent {}` 수정 (라인 105–170)**

기존 `setContent {}` 블록 안의 `SendAmplitudeComposable(...)` + `KurlyTheme { QuickMenuSection(...) }` 를 `QuickMenuSectionContent(...)` 호출로 교체:

```kotlin
composeView.setContent {
    val lazyGridState = rememberLazyGridState()
    val sendImpressionEntireEvent: () -> Unit = remember(key1 = viewModel) {
        {
            val events = viewModel.createImpressionEvent()?.toList().orEmpty()
            eventConsumer.send(events)
        }
    }
    QuickMenuSectionContent(
        menus = menus,
        listState = lazyGridState,
        consumer = eventConsumer,
        rowCount = it.section.rowSize,
        isScrollable = it.section.maxMenuCount > DEVICE_FITTED_QUICK_MENU_COUNT,
        themePosition = viewModel.visibleSectionPosition,
        sectionWrapper = it,
        panelType = viewModel.panelType,
        combinePosition = ::combinePosition,
        sendImpressionEntireEvent = sendImpressionEntireEvent,
        navigateBannerLink = { item -> navigator.navigateBannerLink(item) },
        sendSelectRecommendationAmplitude = { item, row, column ->
            val position = combinePosition(row, column)
            // 기존 sendSelectRecommendationAmplitude 람다 내용 그대로 유지
            when (viewModel.panelType) {
                is PanelUIType.Panel -> { /* ... 기존 코드 */ }
                PanelUIType.Recommendation -> { /* ... 기존 코드 */ }
            }
        },
    )
    composeView.postRequestLayout()
}
```

> ⚠️ `sendSelectRecommendationAmplitude` 람다 내부 코드(라인 136–167)는 그대로 이동. 변경 없음.

**Step 3: 컴파일 확인**

```bash
./gradlew :features:compileDebugKotlin
```

Expected: `BUILD SUCCESSFUL`

**Step 4: 커밋**

```bash
git add features/src/main/java/com/kurly/features/home/recommend/section/viewholder/section/QuickMenuSectionViewHolder.kt
git commit -m "KMA-6460 QuickMenuSectionContent 내부 래퍼 추출 (테스트 용이성)"
```

---

## Task 4: QuickMenu — RED 테스트 작성

**Files:**
- Create: `features/src/androidTest/java/com/kurly/features/home/recommend/section/viewholder/section/QuickMenuImpressionScrollTest.kt`

**Step 1: 테스트 파일 생성**

테스트 데이터 준비를 위해 `QuickMenuSectionItemUIModel`의 생성 방법을 먼저 확인:

```bash
grep -r "QuickMenuSectionItemUIModel(" features/src/main --include="*.kt" -l | head -3
```

**Step 2: 테스트 파일 작성**

```kotlin
package com.kurly.features.home.recommend.section.viewholder.section

import androidx.activity.ComponentActivity
import androidx.compose.foundation.lazy.grid.rememberLazyGridState
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performTouchInput
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.kurly.features.FakeAnalyticsEventConsumer
import com.kurly.features.amplitude.home.recommendation.ImpressionRecommendation
import com.kurly.features.home.model.PanelUIType
import kotlinx.collections.immutable.toImmutableList
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class QuickMenuImpressionScrollTest {

    @get:Rule
    val composeTestRule = createAndroidComposeRule<ComponentActivity>()

    private val fakeConsumer = FakeAnalyticsEventConsumer()

    private fun buildTestMenus() = List(15) { index ->
        QuickMenuSectionItemUIModel(
            title = "메뉴$index",
            link = "https://kurly.com/$index",
            // 나머지 필드는 QuickMenuSectionItemUIModel 생성자에 맞게 채움
            // 빌드 에러 발생 시 from() factory 또는 실제 생성자 확인
        )
    }.toImmutableList()

    @Test
    fun `스크롤 중에는 impression 이벤트가 발화되지 않는다`() {
        composeTestRule.mainClock.autoAdvance = false

        composeTestRule.setContent {
            val listState = rememberLazyGridState()
            QuickMenuSectionContent(
                menus = buildTestMenus(),
                listState = listState,
                consumer = fakeConsumer,
                rowCount = 2,
                isScrollable = true,
                themePosition = 0,
                sectionWrapper = TestFixtures.sectionWrapper(),  // Task 4 Step 3 참고
                panelType = PanelUIType.Recommendation,
                combinePosition = { row, col -> "$row.$col" },
                sendImpressionEntireEvent = {},
                navigateBannerLink = {},
                sendSelectRecommendationAmplitude = { _, _, _ -> },
            )
        }

        // 초기 렌더링 완료 + ON_RESUME → impressions 발화
        composeTestRule.mainClock.advanceUntilIdle()
        fakeConsumer.sentEvents.clear()  // 초기 이벤트 제거

        // 스크롤 시작 (손가락 떼지 않음)
        composeTestRule.onRoot().performTouchInput {
            down(center)
            moveTo(center + Offset(-400f, 0f))
        }

        // 스크롤 중 clock 진행
        composeTestRule.mainClock.advanceTimeBy(300)

        // 스크롤 중 impression 이벤트 없어야 함 (현재는 발화되어 이 테스트가 FAIL)
        assertTrue(
            "스크롤 중 impression 이벤트가 발화되면 안 됨",
            fakeConsumer.sentEvents.none { it is ImpressionRecommendation }
        )

        // 스크롤 종료
        composeTestRule.onRoot().performTouchInput { up() }
    }

    @Test
    fun `스크롤 정지 후 impression 이벤트가 발화된다`() {
        composeTestRule.setContent {
            val listState = rememberLazyGridState()
            QuickMenuSectionContent(
                menus = buildTestMenus(),
                listState = listState,
                consumer = fakeConsumer,
                rowCount = 2,
                isScrollable = true,
                themePosition = 0,
                sectionWrapper = TestFixtures.sectionWrapper(),
                panelType = PanelUIType.Recommendation,
                combinePosition = { row, col -> "$row.$col" },
                sendImpressionEntireEvent = {},
                navigateBannerLink = {},
                sendSelectRecommendationAmplitude = { _, _, _ -> },
            )
        }

        // 초기 이벤트 제거
        composeTestRule.waitForIdle()
        fakeConsumer.sentEvents.clear()

        // 스크롤 → 정지
        composeTestRule.onRoot().performTouchInput {
            swipeLeft(startX = centerX + 200, endX = centerX - 200)
        }
        composeTestRule.waitForIdle()

        // 스크롤 정지 후 impression 이벤트 발화
        assertTrue(
            "스크롤 정지 후 impression 이벤트가 발화되어야 함",
            fakeConsumer.sentEvents.any { it is ImpressionRecommendation }
        )
    }
}
```

**Step 3: TestFixtures 헬퍼 생성**

`SectionWrapper` 생성이 복잡하므로 별도 파일로 분리:

```kotlin
// features/src/androidTest/java/com/kurly/features/TestFixtures.kt
package com.kurly.features

import com.kurly.domain.model.home.section.base.SectionWrapper
// 실제 생성자 시그니처에 맞게 최소 데이터로 생성
// 빌드 에러 시 실제 SectionWrapper 생성자/팩토리 확인 필요

object TestFixtures {
    fun sectionWrapper(): SectionWrapper<*> {
        // TODO: SectionWrapper 최소 생성 방법 확인 후 구현
        TODO("SectionWrapper 최소 생성자 확인 필요")
    }
}
```

**Step 4: RED 확인 (테스트 실패 확인)**

```bash
./gradlew :features:connectedDebugAndroidTest \
  --tests "com.kurly.features.home.recommend.section.viewholder.section.QuickMenuImpressionScrollTest.스크롤 중에는 impression 이벤트가 발화되지 않는다"
```

Expected: **FAILED** — `스크롤 중 impression 이벤트가 발화되면 안 됨` assertion 실패

> ⚠️ 빌드 에러 발생 시: `QuickMenuSectionItemUIModel` 생성자, `SectionWrapper` 생성자를 코드에서 확인 후 `buildTestMenus()` 와 `TestFixtures.sectionWrapper()` 수정

---

## Task 5: QuickMenu — GREEN (filterImpressionsByScrollState 적용)

**Files:**
- Modify: `features/src/main/java/com/kurly/features/home/recommend/section/viewholder/section/QuickMenuSectionViewHolder.kt:431-467`

**Step 1: import 추가 (파일 상단)**

```kotlin
import com.kurly.features.event.filterImpressionsByScrollState
```

**Step 2: `ImpressionRecommendationAmplitude` 수정 (라인 431–467)**

```kotlin
@Composable
private fun ImpressionRecommendationAmplitude(
    menus: ImmutableList<SectionBannerItemUIModel>,
    listState: LazyGridState,
    consumer: AnalyticsEventConsumer,
    themePosition: Int,
    sectionWrapper: SectionWrapper<out MainSection>,
    panelType: PanelUIType,
    combinePosition: (Int, Int) -> String,
    sendImpressionEntireEvent: () -> Unit,
) {
    val visibleItems = listState.visibleGridItemsWithThreshold(percentThreshold = 0.7f)
    val filteredItems = filterImpressionsByScrollState(listState.isScrollInProgress, visibleItems)
    LaunchedEffect(key1 = filteredItems) {
        if (filteredItems.isNotEmpty()) {
            sendImpressionEntireEvent()
        }
        filteredItems.forEach { layoutInfo ->
            val item = menus[layoutInfo.index]
            if (item is QuickMenuSectionItemUIModel) {
                val position = combinePosition(layoutInfo.row, layoutInfo.column)
                val event = when (panelType) {
                    is PanelUIType.Panel -> {
                        val property = PanelEventProperty.QuickMenu(
                            panelId = panelType.panelId,
                            templateCode = sectionWrapper.templateCode,
                            sectionId = sectionWrapper.id,
                            themePosition = themePosition,
                            buttonName = item.title,
                            buttonType = ButtonType.MENU.value,
                            url = item.link,
                            position = position,
                        )
                        ImpressionButton(property)
                    }
                    PanelUIType.Recommendation -> {
                        ImpressionRecommendation.fromQuickMenu(
                            themePosition = themePosition,
                            title = item.title,
                            url = item.link,
                            position = position,
                            sectionWrapper = sectionWrapper,
                        )
                    }
                }
                consumer.send(event)
            }
        }
    }
}
```

**Step 3: GREEN 확인**

```bash
./gradlew :features:connectedDebugAndroidTest \
  --tests "com.kurly.features.home.recommend.section.viewholder.section.QuickMenuImpressionScrollTest"
```

Expected: **PASSED** 2개

**Step 4: 커밋**

```bash
git add features/src/main/java/com/kurly/features/home/recommend/section/viewholder/section/QuickMenuSectionViewHolder.kt
git add features/src/androidTest/java/com/kurly/features/FakeAnalyticsEventConsumer.kt
git add features/src/androidTest/java/com/kurly/features/TestFixtures.kt
git add features/src/androidTest/java/com/kurly/features/home/recommend/section/viewholder/section/QuickMenuImpressionScrollTest.kt
git commit -m "KMA-6460 QuickMenu 스크롤 중 impression 이벤트 필터링 적용"
```

---

## Task 6: EventBanner — RED 테스트 작성

**Files:**
- Create: `features/src/androidTest/java/com/kurly/features/event/EventBannerImpressionScrollTest.kt`

**Step 1: EventScreen.kt의 EventBannerAmplitude 호출 구조 확인**

```bash
grep -n "EventBannerAmplitude\|SendAmplitudeComposable" \
  features/src/main/java/com/kurly/features/event/EventScreen.kt
```

Expected: `SendAmplitudeComposable`이 `EventBannerAmplitude`를 호출하는 구조 확인

**Step 2: EventBannerContent internal 래퍼 생성 필요 여부 확인**

EventScreen.kt의 `SendAmplitudeComposable`이 `private`이면 Task 3과 동일하게 `internal` 래퍼 추출 필요. `public`이면 직접 테스트 가능.

```bash
grep -n "^private fun SendAmplitudeComposable\|^fun SendAmplitudeComposable" \
  features/src/main/java/com/kurly/features/event/EventScreen.kt
```

private이면: `EventBannerContent` internal 래퍼를 EventScreen.kt에 추가 (Task 3 패턴 반복)

**Step 3: 테스트 파일 작성**

```kotlin
package com.kurly.features.event

import androidx.activity.ComponentActivity
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performTouchInput
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.kurly.features.FakeAnalyticsEventConsumer
import com.kurly.features.amplitude.event.ImpressionEventBanner
import kotlinx.collections.immutable.toImmutableList
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class EventBannerImpressionScrollTest {

    @get:Rule
    val composeTestRule = createAndroidComposeRule<ComponentActivity>()

    private val fakeConsumer = FakeAnalyticsEventConsumer()

    private fun buildTestBanners() = List(10) { index ->
        BannerUIModel(id = index.toLong(), title = "배너$index", linkUrl = "https://kurly.com/$index")
    }.toImmutableList()

    @Test
    fun `스크롤 중에는 impression_event_banner 이벤트가 발화되지 않는다`() {
        composeTestRule.mainClock.autoAdvance = false

        composeTestRule.setContent {
            val listState = rememberLazyListState()
            // EventBannerContent 또는 EventBannerAmplitude에 직접 접근 (래퍼 추출 후)
            EventBannerContent(
                banners = buildTestBanners(),
                listState = listState,
                consumer = fakeConsumer,
            )
        }

        composeTestRule.mainClock.advanceUntilIdle()
        fakeConsumer.sentEvents.clear()

        composeTestRule.onRoot().performTouchInput {
            down(center)
            moveTo(center + Offset(0f, -400f))
        }
        composeTestRule.mainClock.advanceTimeBy(300)

        assertTrue(
            "스크롤 중 impression_event_banner가 발화되면 안 됨",
            fakeConsumer.sentEvents.none { it is ImpressionEventBanner }
        )

        composeTestRule.onRoot().performTouchInput { up() }
    }

    @Test
    fun `스크롤 정지 후 impression_event_banner 이벤트가 발화된다`() {
        composeTestRule.setContent {
            val listState = rememberLazyListState()
            EventBannerContent(
                banners = buildTestBanners(),
                listState = listState,
                consumer = fakeConsumer,
            )
        }

        composeTestRule.waitForIdle()
        fakeConsumer.sentEvents.clear()

        composeTestRule.onRoot().performTouchInput {
            swipeUp(startY = centerY + 200, endY = centerY - 200)
        }
        composeTestRule.waitForIdle()

        assertTrue(
            "스크롤 정지 후 impression_event_banner가 발화되어야 함",
            fakeConsumer.sentEvents.any { it is ImpressionEventBanner }
        )
    }
}
```

**Step 4: RED 확인**

```bash
./gradlew :features:connectedDebugAndroidTest \
  --tests "com.kurly.features.event.EventBannerImpressionScrollTest.스크롤 중에는 impression_event_banner 이벤트가 발화되지 않는다"
```

Expected: **FAILED**

---

## Task 7: EventBanner — GREEN (filterImpressionsByScrollState 적용)

**Files:**
- Modify: `features/src/main/java/com/kurly/features/event/EventScreen.kt:327-348`

**Step 1: import 추가**

```kotlin
import com.kurly.features.event.filterImpressionsByScrollState
```

**Step 2: `EventBannerAmplitude` 수정**

```kotlin
@Composable
private fun EventBannerAmplitude(
    banners: ImmutableList<BannerUIModel>,
    listState: LazyListState,
    consumer: AnalyticsEventConsumer,
) {
    val visibleItems = listState.visibleItemsWithThreshold(percentThreshold = 0.7f)
    val filteredItems = filterImpressionsByScrollState(listState.isScrollInProgress, visibleItems)
    LaunchedEffect(key1 = filteredItems) {
        filteredItems.forEach { index ->
            banners.getOrNull(index)?.let { banner ->
                consumer.send(
                    ImpressionEventBanner(
                        id = banner.id,
                        title = banner.title,
                        url = banner.linkUrl,
                        position = index + 1,
                    )
                )
            }
        }
    }
}
```

**Step 3: GREEN 확인**

```bash
./gradlew :features:connectedDebugAndroidTest \
  --tests "com.kurly.features.event.EventBannerImpressionScrollTest"
```

Expected: **PASSED** 2개

**Step 4: 커밋**

```bash
git add features/src/main/java/com/kurly/features/event/EventScreen.kt
git add features/src/androidTest/java/com/kurly/features/event/EventBannerImpressionScrollTest.kt
git commit -m "KMA-6460 EventBanner 스크롤 중 impression 이벤트 필터링 적용"
```

---

## Task 8: 최종 빌드 검증

**Step 1: 수정된 모듈 전체 컴파일**

```bash
./gradlew :features:compileDebugKotlin
```

Expected: `BUILD SUCCESSFUL`, 에러 없음

**Step 2: 전체 단위 테스트**

```bash
./gradlew :features:testDebugUnitTest
```

Expected: `BUILD SUCCESSFUL`

**Step 3: 전체 instrumented 테스트**

```bash
./gradlew :features:connectedDebugAndroidTest \
  --tests "com.kurly.features.home.recommend.section.viewholder.section.QuickMenuImpressionScrollTest" \
  --tests "com.kurly.features.event.EventBannerImpressionScrollTest" \
  --tests "com.kurly.features.event.ImpressionScrollFilterTest"
```

Expected: **모두 PASSED**

---

## 주의사항

- `QuickMenuSectionItemUIModel` 생성자 파악이 필요. `QuickMenuSectionItemUIModel.from(domain)` 팩토리를 통해 생성되므로, 테스트용 최소 도메인 객체가 필요할 수 있음
- `SectionWrapper` 생성이 복잡하면 `mockk<SectionWrapper<*>>(relaxed = true)` 로 대체 가능 (테스트 룰 예외: 내부 의존성이 아닌 데이터 클래스 역할이므로 허용)
- `SendAmplitudeComposable` 내 `OnLifecycleEvent`는 `ON_RESUME` 이후 impression 활성화. `createAndroidComposeRule<ComponentActivity>()` 사용 시 자동으로 처리됨
- RecyclerView 기반 carousel (Row 7, 8) 수정은 이번 범위 외
