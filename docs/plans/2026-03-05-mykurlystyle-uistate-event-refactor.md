# MyKurlyStyle UIState → Event 분리 리팩토링 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** `MyKurlyStyleUIState`에서 일회성 이벤트를 제거하고 `MyKurlyStyleEvent` Channel로 분리하여 State/Event 역할을 명확히 구분한다.

**Architecture:** UIState는 `Loading` / `Content` / `Error` 3가지만 유지. `GetMyKurlyStyleSuccess`, `SaveMyKurlyStyleSuccess`는 `MyKurlyStyleEvent` sealed interface로 이동. `GetPrivacyPolicySuccess`, `UpdatePrivacyPolicySuccess`, `UpdateSiteProfile`은 `Content`로 대체 또는 제거.

**Tech Stack:** Kotlin, Coroutines Channel, StateFlow, JUnit4, MockK

---

## 변경 파일 목록

| 파일 | 작업 |
|------|------|
| `model/MyKurlyStyleUIState.kt` | Success 상태 제거, `Content` 추가 |
| `model/MyKurlyStyleEvent.kt` | 신규 생성 |
| `MyKurlyStyleViewModel.kt` | `_uiEvent` Channel 추가, emit 수정 |
| `MyKurlyStyleActivity.kt` | uiEvent collect로 전환 |
| `compose/MyKurlyStyleScreen.kt` | `Content` 분기 추가 |
| `MyKurlyStyleViewModelTest.kt` | 테스트 수정 |

---

## Task 1: MyKurlyStyleUIState 단순화

**Files:**
- Modify: `features/src/main/java/com/kurly/features/mykurlystyle/kurlystyle/model/MyKurlyStyleUIState.kt`

**Step 1: 테스트 작성 (컴파일 오류 확인용)**

현재 파일의 Success 상태들을 제거하고 `Content` 추가. 먼저 테스트에서 컴파일 오류가 나는지 확인하기 위해 파일을 수정한다.

**Step 2: UIState 파일 수정**

```kotlin
package com.kurly.features.mykurlystyle.kurlystyle.model

sealed class MyKurlyStyleUIState {
    data object Loading : MyKurlyStyleUIState()
    data object Content : MyKurlyStyleUIState()
    data class Error(val errorMessage: String?) : MyKurlyStyleUIState()
}
```

**Step 3: 빌드 오류 확인**

```bash
./gradlew :features:compileDebugKotlin 2>&1 | grep "error:" | head -30
```

Expected: 여러 참조 오류 발생 (Task 2~6에서 순차 수정)

---

## Task 2: MyKurlyStyleEvent 신규 생성

**Files:**
- Create: `features/src/main/java/com/kurly/features/mykurlystyle/kurlystyle/model/MyKurlyStyleEvent.kt`

**Step 1: 파일 생성**

```kotlin
package com.kurly.features.mykurlystyle.kurlystyle.model

sealed interface MyKurlyStyleEvent {
    data class GetMyKurlyStyleSuccess(val myKurlyStyle: MyKurlyStyleUIModel) : MyKurlyStyleEvent
    data object SaveMyKurlyStyleSuccess : MyKurlyStyleEvent
}
```

> **근거:**
> - `GetMyKurlyStyleSuccess`: Activity에서 개인정보 약관 체크 트리거에 필요
> - `SaveMyKurlyStyleSuccess`: Activity에서 완료 화면 이동에 필요
> - `GetPrivacyPolicySuccess`: `_privacyPolicyEvent`가 이미 처리 → `Content`로 대체
> - `UpdatePrivacyPolicySuccess`: `_myKurlyStyleData` 이미 업데이트됨 → `Content`로 대체
> - `UpdateSiteProfile`: `_myKurlyStyleData` 이미 업데이트됨 → 완전 제거

**Step 2: 컴파일 확인**

```bash
./gradlew :features:compileDebugKotlin 2>&1 | grep "MyKurlyStyleEvent" | head -10
```

---

## Task 3: MyKurlyStyleViewModel 수정

**Files:**
- Modify: `features/src/main/java/com/kurly/features/mykurlystyle/kurlystyle/MyKurlyStyleViewModel.kt`

**Step 1: import 추가 및 `_uiEvent` Channel 선언**

`_uiState` 선언 바로 아래에 추가:

```kotlin
import com.kurly.features.mykurlystyle.kurlystyle.model.MyKurlyStyleEvent

// _uiState 아래에 추가
private val _uiEvent = Channel<MyKurlyStyleEvent>()
val uiEvent: Flow<MyKurlyStyleEvent> = _uiEvent.receiveAsFlow()
```

**Step 2: `getMyKurlyStyle()` 수정**

```kotlin
private fun getMyKurlyStyle() {
    viewModelScope.launch {
        _uiState.emit(MyKurlyStyleUIState.Loading)
        when (val result = getMyKurlyStyle.execute()) {
            is GetMyKurlyStyleUsecase.Result.Success -> {
                MyKurlyStyleUIModel.create(result.myKurlyStyle).let {
                    _myKurlyStyleData.value = it
                    _birthYearString.value = it.birthYear?.toString() ?: ""
                    _uiState.emit(MyKurlyStyleUIState.Content)
                    _uiEvent.send(MyKurlyStyleEvent.GetMyKurlyStyleSuccess(it))
                }
            }
            is GetMyKurlyStyleUsecase.Result.Failure -> {
                _uiState.emit(MyKurlyStyleUIState.Error(result.throwable.message))
            }
        }
    }
}
```

**Step 3: `saveMyKurlyStyle()` 수정**

```kotlin
private fun saveMyKurlyStyle(params: SaveMyKurlyStyleUsecase.Params) {
    viewModelScope.launch {
        _uiState.emit(MyKurlyStyleUIState.Loading)
        when (val result = saveMyKurlyStyle.execute(params)) {
            is SaveMyKurlyStyleUsecase.Result.Success -> {
                _uiState.emit(MyKurlyStyleUIState.Content)
                _uiEvent.send(MyKurlyStyleEvent.SaveMyKurlyStyleSuccess)
            }
            is SaveMyKurlyStyleUsecase.Result.Failure -> {
                _uiState.emit(MyKurlyStyleUIState.Error(result.message))
            }
        }
    }
}
```

**Step 4: `getPrivacyPolicy()` 수정**

`GetPrivacyPolicySuccess` emit → `Content` emit으로 교체:

```kotlin
fun getPrivacyPolicy(action: PrivacyPolicyAction) {
    viewModelScope.launch {
        _uiState.emit(MyKurlyStyleUIState.Loading)
        when (val result = getPrivacyPolicy.execute()) {
            is GetPrivacyPolicyUsecase.Result.Success -> {
                PrivacyPolicyUIModel.create(action, result.privacyPolicy).let {
                    _uiState.emit(MyKurlyStyleUIState.Content)
                    _privacyPolicyEvent.send(it)
                }
            }
            is GetPrivacyPolicyUsecase.Result.Failure -> {
                _uiState.emit(MyKurlyStyleUIState.Error(result.throwable.message))
            }
        }
    }
}
```

**Step 5: `updatePrivacyPolicy()` 수정**

`UpdatePrivacyPolicySuccess` emit → `Content` emit으로 교체:

```kotlin
fun updatePrivacyPolicy(isAgree: Boolean) {
    val params = UpdatePrivacyPolicyUsecase.Params(isAgree)
    val statusType = if (isAgree) PrivacyPolicyStatusType.AGREE else PrivacyPolicyStatusType.DISAGREE

    viewModelScope.launch {
        _uiState.emit(MyKurlyStyleUIState.Loading)
        when (val result = updatePrivacyPolicy.execute(params)) {
            is UpdatePrivacyPolicyUsecase.Result.Success -> {
                _myKurlyStyleData.value = _myKurlyStyleData.value.copy(privacyPolicyStatus = statusType)
                _uiState.emit(MyKurlyStyleUIState.Content)
            }
            is UpdatePrivacyPolicyUsecase.Result.Failure -> {
                _uiState.emit(MyKurlyStyleUIState.Error(result.errorMessage))
            }
        }
    }
}
```

**Step 6: `updateSiteProfile()` 수정**

`_uiState.emit(UpdateSiteProfile(...))` 제거 (데이터는 `_myKurlyStyleData`가 처리):

```kotlin
fun updateSiteProfile(newProfile: SiteProfileUIModel) {
    _myKurlyStyleData.value.sites.let {
        val siteProfiles = it.toMutableList()
        val index = siteProfiles.indexOfFirst { newProfile.id == it.id }
        siteProfiles[index] = newProfile
        _myKurlyStyleData.value = _myKurlyStyleData.value.copy(sites = siteProfiles)
    }
}
```

**Step 7: 컴파일 확인**

```bash
./gradlew :features:compileDebugKotlin 2>&1 | grep "error:" | head -20
```

Expected: Activity, Screen 관련 오류만 남음

---

## Task 4: MyKurlyStyleActivity 수정

**Files:**
- Modify: `features/src/main/java/com/kurly/features/mykurlystyle/kurlystyle/MyKurlyStyleActivity.kt`

**Step 1: 현재 `handleState` 파악**

Activity는 현재 `uiState.collect`에서 `GetMyKurlyStyleSuccess`, `SaveMyKurlyStyleSuccess`를 처리한다.

**Step 2: `uiEvent` collect 추가, `handleState` 수정**

`observeViewModel()` 혹은 상태 수집 부분에서:

```kotlin
// 기존 uiState collect는 유지 (Compose가 Loading/Content/Error 처리)
// uiEvent collect 추가
repeatOnLifecycle(Lifecycle.State.STARTED) {
    launch {
        viewModel.uiState.collect { /* Compose가 처리 — 필요 시 Activity 전용 로직만 */ }
    }
    launch {
        viewModel.uiEvent.collect { event ->
            handleEvent(event)
        }
    }
}
```

`handleState` → `handleEvent`로 교체:

```kotlin
private fun handleEvent(event: MyKurlyStyleEvent) {
    when (event) {
        is MyKurlyStyleEvent.GetMyKurlyStyleSuccess -> handleKurlyStyleData(event.myKurlyStyle)
        is MyKurlyStyleEvent.SaveMyKurlyStyleSuccess -> startCompleteActivity()
    }
}
```

> `handleState()`와 `else -> { /* Compose가 처리 */ }` 블록은 제거한다.

**Step 3: 컴파일 확인**

```bash
./gradlew :features:compileDebugKotlin 2>&1 | grep "error:" | head -20
```

Expected: Activity 오류 해소, Screen 오류만 남음

---

## Task 5: MyKurlyStyleScreen 수정

**Files:**
- Modify: `features/src/main/java/com/kurly/features/mykurlystyle/kurlystyle/compose/MyKurlyStyleScreen.kt`

**Step 1: `when (uiState)` 분기에 `Content` 추가**

```kotlin
) { innerPadding ->
    when (uiState) {
        is MyKurlyStyleUIState.Loading -> {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .fillMaxSize()
                    .padding(innerPadding),
            ) {
                KurlyProgress()
            }
        }
        is MyKurlyStyleUIState.Content,
        is MyKurlyStyleUIState.Error -> {
            MyKurlyStyleContent(
                myKurlyStyleData = myKurlyStyleData,
                birthYearString = birthYearString,
                isYearValid = isYearValid,
                ageGroup = ageGroup,
                onAction = onAction,
                onSiteProfileClick = onSiteProfileClick,
                modifier = Modifier.padding(innerPadding),
            )
        }
    }
}
```

> `Error`는 snackbar로 처리되므로 Content와 동일하게 컨텐츠를 표시한다.
> `LaunchedEffect(uiState)`의 Error 분기는 그대로 유지.

**Step 2: Preview 수정**

기존 `GetMyKurlyStyleSuccess` → `Content`로 교체:

```kotlin
// Before
uiState = MyKurlyStyleUIState.GetMyKurlyStyleSuccess(previewMyKurlyStyleUIModel()),
// After
uiState = MyKurlyStyleUIState.Content,
```

**Step 3: 전체 빌드 확인**

```bash
./gradlew :features:compileDebugKotlin 2>&1 | grep "error:"
```

Expected: 오류 없음

---

## Task 6: MyKurlyStyleViewModelTest 수정

**Files:**
- Modify: `features/src/test/java/com/kurly/features/mykurlystyle/kurlystyle/MyKurlyStyleViewModelTest.kt`

### 수정할 테스트 목록

**① `스타일 조회 성공 시 GetMyKurlyStyleSuccess 상태가 된다` → `Content 상태가 된다`**

```kotlin
@Test
fun `스타일 조회 성공 시 Content 상태가 된다`() = runTest {
    coEvery { getMyKurlyStyleUsecase.execute() } returns
        GetMyKurlyStyleUsecase.Result.Success(testMyKurlyStyle)
    createViewModel()

    advanceUntilIdle()

    assertEquals(MyKurlyStyleUIState.Content, viewModel.uiState.value)
}
```

**② `스타일 조회 성공 시 반환된 데이터가 UIState에 포함된다` → `myKurlyStyleData에 반영된다`**

```kotlin
@Test
fun `스타일 조회 성공 시 반환된 데이터가 myKurlyStyleData에 반영된다`() = runTest {
    coEvery { getMyKurlyStyleUsecase.execute() } returns
        GetMyKurlyStyleUsecase.Result.Success(testMyKurlyStyle)
    createViewModel()

    advanceUntilIdle()

    assertNull(viewModel.myKurlyStyleData.value.gender)
    assertEquals(1990, viewModel.myKurlyStyleData.value.birthYear)
}
```

**③ `스타일 조회 성공 시 GetMyKurlyStyleSuccess 이벤트가 emit된다` (신규 추가)**

```kotlin
@Test
fun `스타일 조회 성공 시 GetMyKurlyStyleSuccess 이벤트가 emit된다`() = runTest {
    coEvery { getMyKurlyStyleUsecase.execute() } returns
        GetMyKurlyStyleUsecase.Result.Success(testMyKurlyStyle)
    createViewModel()

    val deferred = launch {
        val event = viewModel.uiEvent.first()
        assertTrue(event is MyKurlyStyleEvent.GetMyKurlyStyleSuccess)
    }

    advanceUntilIdle()
    deferred.join()
}
```

**④ `updateSiteProfile 호출 시 UpdateSiteProfile 상태가 emit된다` → 제거**

해당 테스트 삭제. `myKurlyStyleData` 업데이트 확인 테스트(`updateSiteProfile 호출 시 해당 id의 프로필이 갱신된다`)는 그대로 유지.

**⑤ `저장 성공 시 SaveMyKurlyStyleSuccess 상태가 된다` → 2개로 분리**

```kotlin
@Test
fun `저장 성공 시 Content 상태가 된다`() = runTest {
    coEvery { saveMyKurlyStyleUsecase.execute(any()) } returns
        SaveMyKurlyStyleUsecase.Result.Success(true)
    createViewModel()
    advanceUntilIdle()
    viewModel.onAction(MyKurlyStyleAction.BirthYearChange("1990"))
    viewModel.setGender(GenderType.FEMALE)

    viewModel.checkValidate()
    advanceUntilIdle()

    assertEquals(MyKurlyStyleUIState.Content, viewModel.uiState.value)
}

@Test
fun `저장 성공 시 SaveMyKurlyStyleSuccess 이벤트가 emit된다`() = runTest {
    coEvery { saveMyKurlyStyleUsecase.execute(any()) } returns
        SaveMyKurlyStyleUsecase.Result.Success(true)
    createViewModel()
    advanceUntilIdle()
    viewModel.onAction(MyKurlyStyleAction.BirthYearChange("1990"))
    viewModel.setGender(GenderType.FEMALE)

    val deferred = launch {
        val event = viewModel.uiEvent.first()
        assertEquals(MyKurlyStyleEvent.SaveMyKurlyStyleSuccess, event)
    }

    viewModel.checkValidate()
    advanceUntilIdle()
    deferred.join()
}
```

**⑥ `약관 조회 성공 시 GetPrivacyPolicySuccess 상태가 된다` → `Content 상태가 된다`**

```kotlin
@Test
fun `약관 조회 성공 시 Content 상태가 된다`() = runTest {
    coEvery { getPrivacyPolicyUsecase.execute() } returns
        GetPrivacyPolicyUsecase.Result.Success(testPrivacyPolicy)
    createViewModel()
    advanceUntilIdle()

    viewModel.getPrivacyPolicy(PrivacyPolicyAction.OPEN_DIALOG)
    advanceUntilIdle()

    assertEquals(MyKurlyStyleUIState.Content, viewModel.uiState.value)
}
```

**⑦ `약관 업데이트 성공 시 UpdatePrivacyPolicySuccess 상태가 된다` → `Content 상태가 된다`**

```kotlin
@Test
fun `약관 업데이트 성공 시 Content 상태가 된다`() = runTest {
    coEvery { updatePrivacyPolicyUsecase.execute(any()) } returns
        UpdatePrivacyPolicyUsecase.Result.Success(true)
    createViewModel()
    advanceUntilIdle()

    viewModel.updatePrivacyPolicy(isAgree = true)
    advanceUntilIdle()

    assertEquals(MyKurlyStyleUIState.Content, viewModel.uiState.value)
}
```

**Step 2: import 추가**

```kotlin
import com.kurly.features.mykurlystyle.kurlystyle.model.MyKurlyStyleEvent
```

**Step 3: 테스트 실행**

```bash
./gradlew :features:testDebugUnitTest --tests "com.kurly.features.mykurlystyle.kurlystyle.MyKurlyStyleViewModelTest" 2>&1 | tail -30
```

Expected: BUILD SUCCESSFUL, 모든 테스트 통과

---

## Task 7: 전체 테스트 및 커밋

**Step 1: 전체 빌드**

```bash
./gradlew :features:compileDebugKotlin
```

Expected: 오류 없음

**Step 2: 유닛 테스트 전체 실행**

```bash
./gradlew :features:testDebugUnitTest 2>&1 | tail -20
```

Expected: BUILD SUCCESSFUL

**Step 3: 커밋**

```bash
git add features/src/main/java/com/kurly/features/mykurlystyle/kurlystyle/model/MyKurlyStyleUIState.kt \
        features/src/main/java/com/kurly/features/mykurlystyle/kurlystyle/model/MyKurlyStyleEvent.kt \
        features/src/main/java/com/kurly/features/mykurlystyle/kurlystyle/MyKurlyStyleViewModel.kt \
        features/src/main/java/com/kurly/features/mykurlystyle/kurlystyle/MyKurlyStyleActivity.kt \
        features/src/main/java/com/kurly/features/mykurlystyle/kurlystyle/compose/MyKurlyStyleScreen.kt \
        features/src/test/java/com/kurly/features/mykurlystyle/kurlystyle/MyKurlyStyleViewModelTest.kt
git commit -m "KMA-7033 UIState에서 일회성 이벤트를 MyKurlyStyleEvent Channel로 분리"
```
