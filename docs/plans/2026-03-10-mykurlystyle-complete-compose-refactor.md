# MyKurlyStyleCompleteActivity Compose 개선 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** PR #7136(MyKurlyStyleActivity Compose 전환)과 동일한 패턴으로 MyKurlyStyleCompleteActivity를 개선 — Activity를 최대한 가볍게, navigation 수집을 Route로 이동

**Architecture:** Activity는 `onResume()` screen tracking + Context 필요한 navigation lambda만 보유. Route가 ViewModel(`hiltViewModel()`)을 직접 소유하고 `LaunchedEffect`로 navigation/error Channel 수집. `snackbarHostState`는 Route 레벨로 올려 에러 처리를 1단계로 단순화.

**Tech Stack:** Kotlin, Jetpack Compose, Hilt, Coroutines Channel/Flow, JUnit4, Robolectric

---

### Task 1: ViewModel — `errorMessages` → `errorEvent` 이름 변경

**Files:**
- Modify: `features/src/main/java/com/kurly/features/mykurlystyle/complete/MyKurlyStyleCompleteViewModel.kt`
- Test: `features/src/test/java/com/kurly/features/mykurlystyle/complete/MyKurlyStyleCompleteViewModelTest.kt`

**Step 1: 테스트 시나리오 확인 및 참조명 변경**

기존 테스트 2개가 `errorMessages`를 참조 중 (115, 131번째 줄). 이를 `errorEvent`로 변경:

```kotlin
// 변경 전 (두 곳 모두)
val message = viewModel.errorMessages.first()

// 변경 후
val message = viewModel.errorEvent.first()
```

**Step 2: 테스트 실행 — 컴파일 에러 확인 (RED)**

```bash
./gradlew :features:testDebugUnitTest \
  --tests "com.kurly.features.mykurlystyle.complete.MyKurlyStyleCompleteViewModelTest" \
  2>&1 | tail -15
```
Expected: `error: unresolved reference: errorEvent`

**Step 3: ViewModel 구현 변경 (GREEN)**

```kotlin
// 변경 전
private val _errorMessage = Channel<String?>()
val errorMessages: Flow<String?> = _errorMessage.receiveAsFlow()
// ...
_errorMessage.send(result.throwable.message)

// 변경 후
private val _errorEvent = Channel<String?>()
val errorEvent: Flow<String?> = _errorEvent.receiveAsFlow()
// ...
_errorEvent.send(result.throwable.message)
```

**Step 4: 테스트 재실행 — 통과 확인 (GREEN)**

```bash
./gradlew :features:testDebugUnitTest \
  --tests "com.kurly.features.mykurlystyle.complete.MyKurlyStyleCompleteViewModelTest" \
  2>&1 | tail -10
```
Expected: `BUILD SUCCESSFUL`

**Step 5: Commit**

```bash
git add features/src/main/java/com/kurly/features/mykurlystyle/complete/MyKurlyStyleCompleteViewModel.kt \
        features/src/test/java/com/kurly/features/mykurlystyle/complete/MyKurlyStyleCompleteViewModelTest.kt
git commit -m "KMA-7046 errorMessages Channel을 errorEvent로 이름 변경"
```

---

### Task 2: Screen — `errorMessage: String?` → `snackbarHostState: SnackbarHostState`

**Files:**
- Modify: `features/src/main/java/com/kurly/features/mykurlystyle/complete/ui/MyKurlyStyleCompleteScreen.kt` (Screen 함수만)
- Test: `features/src/test/java/com/kurly/features/mykurlystyle/complete/ui/MyKurlyStyleCompleteScreenTest.kt`

#### 변경 배경

이전: Screen 내부에서 `LaunchedEffect(errorMessage)`가 snackbar를 직접 trigger.
이후: Screen은 외부로부터 `snackbarHostState`를 주입받아 Scaffold에 연결만 함. snackbar trigger는 Route의 `LaunchedEffect`가 담당.

따라서 Screen 테스트도 **"외부에서 snackbarHostState에 showSnackbar를 호출하면 화면에 메시지가 표시된다"** 로 시나리오가 바뀐다.

**Step 1: 테스트 시나리오 작성 (새 동작 기준)**

`MyKurlyStyleCompleteScreenTest.kt`의 `setScreen` helper와 에러 테스트를 아래로 교체:

```kotlin
import androidx.compose.material3.SnackbarHostState
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

// setScreen helper 교체
private fun setScreen(
    recommendResult: RecommendResultUIModel?,
    snackbarHostState: SnackbarHostState = SnackbarHostState(),
    onAction: (Action) -> Unit = {},
    onFinish: () -> Unit = {},
) {
    composeTestRule.setContent {
        KurlyTheme {
            MyKurlyStyleCompleteScreen(
                recommendResult = recommendResult,
                snackbarHostState = snackbarHostState,
                onAction = onAction,
                onFinish = onFinish,
            )
        }
    }
}

// 에러 테스트 교체 — 외부 trigger 방식으로 시나리오 변경
@Test
fun `외부에서 snackbarHostState에 showSnackbar 호출시 메시지가 화면에 표시된다`() {
    // given
    val snackbarHostState = SnackbarHostState()
    setScreen(
        recommendResult = null,
        snackbarHostState = snackbarHostState,
    )

    // when — Route의 LaunchedEffect가 하는 동작을 테스트에서 시뮬레이션
    CoroutineScope(Dispatchers.Main).launch {
        snackbarHostState.showSnackbar("네트워크 오류")
    }
    composeTestRule.waitForIdle()

    // then
    composeTestRule.onNodeWithText("네트워크 오류").assertIsDisplayed()
}
```

**Step 2: 테스트 실행 — 컴파일 에러 확인 (RED)**

```bash
./gradlew :features:testDebugUnitTest \
  --tests "com.kurly.features.mykurlystyle.complete.ui.MyKurlyStyleCompleteScreenTest" \
  2>&1 | tail -15
```
Expected: `error: none of the following candidates is applicable` (파라미터 불일치)

**Step 3: Screen 구현 변경 (GREEN)**

`MyKurlyStyleCompleteScreen` 함수 시그니처 및 내부 변경:

```kotlin
// 변경 전
@Composable
fun MyKurlyStyleCompleteScreen(
    recommendResult: RecommendResultUIModel?,
    errorMessage: String?,           // ← 제거
    onAction: (Action) -> Unit,
    onFinish: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val snackbarHostState = remember { SnackbarHostState() }  // ← 제거

    LaunchedEffect(errorMessage) {                            // ← 제거
        errorMessage ?: return@LaunchedEffect
        snackbarHostState.showSnackbar(errorMessage)
    }
    ...
}

// 변경 후
@Composable
fun MyKurlyStyleCompleteScreen(
    recommendResult: RecommendResultUIModel?,
    snackbarHostState: SnackbarHostState,    // ← 외부 주입
    onAction: (Action) -> Unit,
    onFinish: () -> Unit,
    modifier: Modifier = Modifier,
) {
    // snackbarHostState 내부 생성 및 LaunchedEffect 제거됨
    Scaffold(
        modifier = modifier,
        topBar = { ... },
        snackbarHost = { SnackbarHost(snackbarHostState) },  // 주입받은 것 사용
    ) { ... }
}
```

**Step 4: @Preview 수정**

```kotlin
@Preview(showBackground = true)
@Composable
private fun MyKurlyStyleCompleteScreenPreview() {
    KurlyTheme {
        MyKurlyStyleCompleteScreen(
            recommendResult = RecommendResultUIModel(...),
            snackbarHostState = remember { SnackbarHostState() },  // ← 변경
            onAction = {},
            onFinish = {},
        )
    }
}

@Preview(showBackground = true)
@Composable
private fun MyKurlyStyleCompleteScreenLoadingPreview() {
    KurlyTheme {
        MyKurlyStyleCompleteScreen(
            recommendResult = null,
            snackbarHostState = remember { SnackbarHostState() },  // ← 변경
            onAction = {},
            onFinish = {},
        )
    }
}
```

**Step 5: 테스트 재실행 — 통과 확인 (GREEN)**

```bash
./gradlew :features:testDebugUnitTest \
  --tests "com.kurly.features.mykurlystyle.complete.ui.MyKurlyStyleCompleteScreenTest" \
  2>&1 | tail -10
```
Expected: `BUILD SUCCESSFUL`

**Step 6: Commit**

```bash
git add features/src/main/java/com/kurly/features/mykurlystyle/complete/ui/MyKurlyStyleCompleteScreen.kt \
        features/src/test/java/com/kurly/features/mykurlystyle/complete/ui/MyKurlyStyleCompleteScreenTest.kt
git commit -m "KMA-7046 Screen errorMessage 파라미터를 snackbarHostState로 교체"
```

---

### Task 3: Route — navigation lambda 추가 + LaunchedEffect 2개

**Files:**
- Modify: `features/src/main/java/com/kurly/features/mykurlystyle/complete/ui/MyKurlyStyleCompleteScreen.kt` (Route 함수만)

> Route는 ViewModel + Activity lambda를 연결하는 얇은 글루 레이어라 단독 유닛 테스트 없음.
> 컴파일 + 전체 테스트 통과로 검증.

**Step 1: Route 전체 교체**

```kotlin
@Composable
fun MyKurlyStyleCompleteRoute(
    onFinish: () -> Unit,
    onNavigateToProductDetail: (ContentProductListItemUIModel, String?) -> Unit,
    onNavigateToMain: (SiteFilterType) -> Unit,
    viewModel: MyKurlyStyleCompleteViewModel = hiltViewModel(),
) {
    val recommendResult by viewModel.recommendResult.collectAsStateWithLifecycle()
    val snackbarHostState = remember { SnackbarHostState() }
    val defaultErrorMessage = stringResource(R.string.error_state_title)

    LaunchedEffect(Unit) {
        viewModel.navigation.collect { navigation ->
            when (navigation) {
                is Navigation.ToProductDetail -> onNavigateToProductDetail(
                    navigation.item,
                    navigation.referrerEventName,
                )
                is Navigation.ToMain -> onNavigateToMain(navigation.siteFilterType)
            }
        }
    }

    LaunchedEffect(Unit) {
        viewModel.errorEvent.collect { message ->
            snackbarHostState.showSnackbar(message ?: defaultErrorMessage)
        }
    }

    MyKurlyStyleCompleteScreen(
        recommendResult = recommendResult,
        snackbarHostState = snackbarHostState,
        onAction = viewModel::onAction,
        onFinish = onFinish,
    )
}
```

추가할 import:
```kotlin
import com.kurly.domain.model.main.SiteFilterType
import com.kurly.features.mykurlystyle.complete.Navigation
```

**Step 2: 컴파일 + 전체 테스트 확인 (GREEN)**

```bash
./gradlew :features:testDebugUnitTest 2>&1 | tail -10
```
Expected: `BUILD SUCCESSFUL`

**Step 3: Commit**

```bash
git add features/src/main/java/com/kurly/features/mykurlystyle/complete/ui/MyKurlyStyleCompleteScreen.kt
git commit -m "KMA-7046 Route navigation 수집을 LaunchedEffect로 이동, snackbar 단순화"
```

---

### Task 4: Activity — 경량화

**Files:**
- Modify: `features/src/main/java/com/kurly/features/mykurlystyle/complete/MyKurlyStyleCompleteActivity.kt`

> Activity 동작은 instrumented test 영역. 여기서는 컴파일 + 유닛 테스트 전체 통과로 검증.

**Step 1: Activity 전체 교체**

```kotlin
package com.kurly.features.mykurlystyle.complete

import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import com.kurly.features.mykurlystyle.complete.ui.MyKurlyStyleCompleteRoute
import com.kurly.kpds.compose.foundation.KurlyTheme
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject

@AndroidEntryPoint
class MyKurlyStyleCompleteActivity : AppCompatActivity() {

    @Inject
    lateinit var myKurlyStyleDelegator: MyKurlyStyleDelegator

    @Inject
    lateinit var amplitudeSender: MyKurlyStyleCompleteAmplitudeSender

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        setContent {
            KurlyTheme(darkTheme = false) {
                MyKurlyStyleCompleteRoute(
                    onFinish = ::finish,
                    onNavigateToProductDetail = { item, referrerEventName ->
                        myKurlyStyleDelegator.startProductDetail(
                            context = this,
                            item = item,
                            referrerEventName = referrerEventName,
                        )
                    },
                    onNavigateToMain = { siteFilterType ->
                        myKurlyStyleDelegator.startMainActivity(
                            context = this,
                            site = siteFilterType,
                        )
                    },
                )
            }
        }
    }

    override fun onResume() {
        super.onResume()
        amplitudeSender.sendScreenName()
    }
}
```

제거되는 요소:
- `import androidx.activity.viewModels`
- `import com.kurly.core.extension.repeatOnStarted`
- `private val viewModel: MyKurlyStyleCompleteViewModel by viewModels()`
- `repeatOnStarted { viewModel.navigation.collect { handleNavigation(it) } }`
- `handleNavigation(navigation: Navigation)` 메서드 전체

**Step 2: 전체 테스트 통과 확인 (GREEN)**

```bash
./gradlew :features:testDebugUnitTest 2>&1 | tail -10
```
Expected: `BUILD SUCCESSFUL`

**Step 3: Commit**

```bash
git add features/src/main/java/com/kurly/features/mykurlystyle/complete/MyKurlyStyleCompleteActivity.kt
git commit -m "KMA-7046 Activity에서 viewModels/repeatOnStarted 제거, navigation lambda로 위임"
```
