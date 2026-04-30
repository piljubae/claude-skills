# Impression Scroll Filter — Design

**Date**: 2026-04-09  
**Ticket**: KMA-6460  
**Branch**: feature/KMA-6460-impression-fix

---

## 배경

전사 노출(Impression) 측정 기준 표준화 QA(2026-04-08) 결과, Android에서 스크롤 중 impression 이벤트가 발화되는 이슈가 확인됨.

### QA 확인 필요 항목

| 이벤트 | 위치 | 이슈 |
|--------|------|------|
| `impression_recommendation_quick_menu` | 홈-추천 | 좌우 스크롤 중 이벤트 발생 확인됨 |
| `impression_event_banner` | 특가/혜택 | 전체 확인 필요 |
| `impression_recommendation_main_banner_carousel` | 홈-추천 | 스크롤 중 발생 여부 확인 필요 |
| `impression_recommendation_main_banner_carousel_horizontal` | 홈-추천 | 스크롤 중 발생 여부 확인 필요 |

---

## 수정 범위 (이번 PR)

Compose 기반 컴포넌트 2개:
1. `QuickMenuSectionViewHolder.kt` — `ImpressionRecommendationAmplitude`
2. `EventScreen.kt` — `EventBannerAmplitude`

RecyclerView 기반 carousel은 별도 확인 후 다음 PR에서 처리.

---

## 기존 인프라

### `filterImpressionsByScrollState` (이미 작성됨)

```kotlin
// features/src/main/java/com/kurly/features/event/EventUtils.kt
fun <T> filterImpressionsByScrollState(isScrollInProgress: Boolean, visibleItems: List<T>): List<T> {
    return if (isScrollInProgress) emptyList() else visibleItems
}
```

테스트: `ImpressionScrollFilterTest.kt` (4개, 미커밋)

### 참조 구현 (올바른 패턴)

`CategoryQuickMenuSection.kt`에서 `if (!bannerScrollState.isScrollInProgress)` 로 스크롤 중 impression 차단.

---

## 수정 패턴

### Before

```kotlin
val visibleItems = listState.visibleGridItemsWithThreshold(percentThreshold = 0.7f)
LaunchedEffect(key1 = visibleItems) {
    sendImpressionEntireEvent()       // 스크롤 중에도 호출
    visibleItems.forEach { ... consumer.send(event) }
}
```

### After

CLAUDE.md 규칙 준수 — `LaunchedEffect`를 `if`로 감싸지 않고 내부에서 판단:

```kotlin
val visibleItems = listState.visibleGridItemsWithThreshold(percentThreshold = 0.7f)
val filteredItems = filterImpressionsByScrollState(listState.isScrollInProgress, visibleItems)
LaunchedEffect(key1 = filteredItems) {
    if (filteredItems.isNotEmpty()) {
        sendImpressionEntireEvent()   // 스크롤 정지 후에만 호출
    }
    filteredItems.forEach { ... consumer.send(event) }
}
```

`EventBannerAmplitude`도 동일 패턴 적용.

---

## 테스트 전략 (TDD — Compose Instrumented)

### 최소 리팩토링

`QuickMenuSectionViewHolder.kt` 내 `setContent {}` 본문을 `internal` 래퍼 함수로 추출:

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
)
```

- `SendAmplitudeComposable`, `ImpressionRecommendationAmplitude` 는 `private` 유지
- ViewHolder는 `setContent { QuickMenuSectionContent(...) }` 로 위임
- 테스트는 `QuickMenuSectionContent`를 직접 호출

### FakeAnalyticsEventConsumer

```kotlin
class FakeAnalyticsEventConsumer : AnalyticsEventConsumer {
    val sentEvents = mutableListOf<AnalyticsEvent>()
    override fun send(event: AnalyticsEvent) { sentEvents += event }
    override fun send(events: List<AnalyticsEvent>) { sentEvents += events }
    // 기타 메서드 no-op
}
```

### Test List (TDD 순서)

**QuickMenuImpressionScrollTest.kt**

1. `스크롤 중에는 impression 이벤트가 발화되지 않는다` — RED → GREEN (fix 적용)
2. `스크롤 정지 후 보이는 아이템의 impression 이벤트가 발화된다`
3. `sendImpressionEntireEvent는 스크롤 정지 후에만 호출된다`

**EventBannerImpressionScrollTest.kt**

1. `스크롤 중에는 impression_event_banner 이벤트가 발화되지 않는다` — RED → GREEN
2. `스크롤 정지 후 impression_event_banner 이벤트가 발화된다`

### 테스트 인프라

- `createAndroidComposeRule<ComponentActivity>()` — 라이프사이클(`ON_RESUME`) 필요
- `mainClock.autoAdvance = false` — 시간 수동 제어
- `performTouchInput { down(start); moveBy(offset) }` — 스크롤 시뮬레이션
- `mainClock.advanceUntilIdle()` — 스크롤 완료 후 LaunchedEffect 실행

---

## 파일 변경 목록

| 파일 | 변경 유형 |
|------|-----------|
| `features/.../event/EventUtils.kt` | 기존 (미커밋 → 커밋) |
| `features/.../event/ImpressionScrollFilterTest.kt` | 기존 (미커밋 → 커밋) |
| `features/.../section/viewholder/section/QuickMenuSectionViewHolder.kt` | 수정 (래퍼 추출 + filter 적용) |
| `features/.../event/EventScreen.kt` | 수정 (filter 적용) |
| `features/src/androidTest/.../QuickMenuImpressionScrollTest.kt` | 신규 |
| `features/src/androidTest/.../EventBannerImpressionScrollTest.kt` | 신규 |

---

## 비고

- QA팀에 스크롤 테스트 스크립트 전달 필요 (logcat 기반)
- RecyclerView carousel 항목(Row 7, 8)은 이번 범위 외
