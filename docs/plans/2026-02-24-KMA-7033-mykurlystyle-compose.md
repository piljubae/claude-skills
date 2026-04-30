# KMA-7033 MyKurlyStyleActivity Compose 전환 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** `MyKurlyStyleActivity` (XML + DataBinding + RecyclerView)를 Jetpack Compose로 전환하고 관련 XML/Adapter/ViewHolder를 제거한다.

**Architecture:** Activity는 껍데기(setContent, ActivityResult, Fragment 다이얼로그, Broadcast)만 담당하고, `MyKurlyStyleScreen` Composable이 전체 UI를 렌더링한다. ViewModel의 LiveData를 StateFlow로 마이그레이션하여 Compose `collectAsStateWithLifecycle`로 수집 가능하게 만든다.

**Tech Stack:** Jetpack Compose (KPDS), Hilt, StateFlow, `collectAsStateWithLifecycle`, `rememberLauncherForActivityResult`는 사용하지 않고 Activity의 기존 `siteProfileLauncher` 유지

---

## 현재 파일 구조 (변경 대상)

```
features/src/main/java/com/kurly/features/mykurlystyle/kurlystyle/
├── MyKurlyStyleActivity.kt          ← 대폭 수정
├── MyKurlyStyleViewModel.kt         ← LiveData → StateFlow 마이그레이션
├── controller/
│   └── MyKurlyStyleController.kt    ← 삭제 (Task 4)
├── adapter/
│   ├── SiteProfileAdapter.kt        ← 삭제 (Task 4)
│   ├── diff/
│   │   └── SiteProfileDiffUtil.kt   ← 삭제 (Task 4)
│   └── viewholder/
│       └── SiteProfileViewHolder.kt ← 삭제 (Task 4)
└── compose/ (신규 패키지)
    ├── SiteProfileItem.kt           ← 신규 (Task 1)
    └── MyKurlyStyleScreen.kt        ← 신규 (Task 2~4)

features/src/main/res/layout/
├── activity_my_kurly_style.xml      ← 삭제 (Task 4)
└── list_item_kurly_profile.xml      ← 삭제 (Task 4)
```

---

## Task 1 (KMA-7053): SiteProfileItem Composable 생성

**목표:** `SiteProfileViewHolder` + `list_item_kurly_profile.xml`을 대체하는 Composable 생성.
기존 XML은 아직 유지. 이 태스크에서는 Composable만 추가한다.

**Files:**
- Create: `features/src/main/java/com/kurly/features/mykurlystyle/kurlystyle/compose/SiteProfileItem.kt`
- Reference: `features/src/main/java/com/kurly/features/mykurlystyle/kurlystyle/model/SiteProfileUIModel.kt`
- Reference: `features/src/main/res/layout/list_item_kurly_profile.xml` (기존 XML 참고)

### Step 1: SiteProfileItem.kt 파일 생성

```kotlin
package com.kurly.features.mykurlystyle.kurlystyle.compose

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.kurly.features.R
import com.kurly.features.mykurlystyle.kurlystyle.model.SiteProfileUIModel
import com.kurly.kpds.compose.icon.KurlyIcon
import com.kurly.kpds.compose.icon.KurlyIconSize
import com.kurly.kpds.compose.text.KurlyText
import com.kurly.kpds.compose.theme.KurlyTheme

@Composable
fun SiteProfileItem(
    profile: SiteProfileUIModel,
    onProfileClick: (SiteProfileUIModel) -> Unit,
    modifier: Modifier = Modifier,
) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .clickable { onProfileClick(profile) }
            .padding(horizontal = 20.dp, vertical = 16.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        AsyncImage(
            model = profile.thumbnailUrl,
            contentDescription = null,
            modifier = Modifier
                .size(56.dp)
                .clip(CircleShape),
            placeholder = painterResource(R.drawable.ic_common_profile_placeholder),
            error = painterResource(R.drawable.ic_common_profile_placeholder),
        )
        KurlyTheme.spacers.width16()
        Column(modifier = Modifier.weight(1f)) {
            KurlyText(
                text = profile.name,
                style = KurlyTheme.typography.body1Bold,
                color = KurlyTheme.colors.gray900,
            )
            if (profile.hasProfile && profile.isSummaryNotEmpty()) {
                KurlyTheme.spacers.height4()
                KurlyText(
                    text = profile.summary,
                    style = KurlyTheme.typography.body2Regular,
                    color = KurlyTheme.colors.gray600,
                )
            } else if (!profile.hasProfile) {
                KurlyTheme.spacers.height4()
                KurlyText(
                    text = profile.description,
                    style = KurlyTheme.typography.body2Regular,
                    color = KurlyTheme.colors.gray600,
                )
            }
        }
        KurlyTheme.spacers.width8()
        KurlyIcon(
            resId = R.drawable.ic_common_arrow_right,
            size = KurlyIconSize.Small,
            tint = KurlyTheme.colors.gray400,
        )
    }
}

@Preview(showBackground = true)
@Composable
private fun SiteProfileItemPreview() {
    KurlyTheme {
        SiteProfileItem(
            profile = SiteProfileUIModel(
                id = "1",
                name = "마켓컬리",
                description = "프로필을 등록하면 맞춤 상품을 추천해드려요",
                thumbnailUrl = "",
                displayNewIcon = false,
                hasProfile = false,
                summary = "",
            ),
            onProfileClick = {},
        )
    }
}

@Preview(showBackground = true)
@Composable
private fun SiteProfileItemWithProfilePreview() {
    KurlyTheme {
        SiteProfileItem(
            profile = SiteProfileUIModel(
                id = "1",
                name = "마켓컬리",
                description = "",
                thumbnailUrl = "",
                displayNewIcon = false,
                hasProfile = true,
                summary = "30대 여성, 자녀 있음",
            ),
            onProfileClick = {},
        )
    }
}
```

### Step 2: 빌드 확인

```bash
./gradlew :features:compileDebugKotlin
```

Expected: BUILD SUCCESSFUL (컴파일 에러 없음)

### Step 3: 커밋

```bash
/commit
```

---

## Task 2 (KMA-7054): ViewModel 마이그레이션 + Screen 기본 구조

**목표:** LiveData → StateFlow 전환, privacyPolicy 이벤트 Channel 도입,
`MyKurlyStyleScreen.kt` 기본 구조(Toolbar·생년·성별·유아·약관·저장) 생성.

### Step 1: ViewModel - LiveData → StateFlow 마이그레이션

**File:** `features/src/main/java/com/kurly/features/mykurlystyle/kurlystyle/MyKurlyStyleViewModel.kt`

변경 내용:

```kotlin
// Before:
val birthYearString: NonNullLiveData<String> = NonNullLiveData("")
val isYearValid: LiveData<Boolean> = birthYearString.map { ... }
val ageGroup: LiveData<String> = isYearValid.map { ... }
val isEnabledSave: LiveData<Boolean> = combine(...).asLiveData()
val privacyPolicy = MutableSharedFlow<PrivacyPolicyUIModel>()

// After:
val birthYearString: MutableStateFlow<String> = MutableStateFlow("")

val isYearValid: StateFlow<Boolean> = birthYearString
    .map { year -> ... } // 기존 map 로직 동일
    .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000L), false)

val ageGroup: StateFlow<String> = isYearValid
    .map { isValid -> ... } // 기존 map 로직 동일 (myKurlyStyleData 참고)
    .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000L), "")

val isEnabledSave: StateFlow<Boolean> = combine(myKurlyStyleData, isYearValid) { data, valid ->
    data.gender != null && valid
}.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000L), false)

// privacyPolicy: SharedFlow → Channel (one-time event)
private val _privacyPolicyEvent = Channel<PrivacyPolicyUIModel>(Channel.BUFFERED)
val privacyPolicyEvent: Flow<PrivacyPolicyUIModel> = _privacyPolicyEvent.receiveAsFlow()
```

- `privacyPolicy.emit(it)` 호출부를 모두 `_privacyPolicyEvent.send(it)` 로 교체
- DataBinding에서 참조하던 `birthYearString.value = ...` 는 동일하게 동작 (MutableStateFlow도 `.value` 지원)

### Step 2: 빌드 + 기존 Activity 컴파일 확인

```bash
./gradlew :features:compileDebugKotlin
```

Expected: BUILD SUCCESSFUL.
DataBinding 참조 오류가 발생하면 Activity의 `viewModel.birthYearString` 참조를 확인한다.

### Step 3: MyKurlyStyleScreen.kt 기본 구조 생성

**File:** `features/src/main/java/com/kurly/features/mykurlystyle/kurlystyle/compose/MyKurlyStyleScreen.kt`

```kotlin
package com.kurly.features.mykurlystyle.kurlystyle.compose

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.kurly.features.R
import com.kurly.features.mykurlystyle.kurlystyle.MyKurlyStyleViewModel
import com.kurly.features.mykurlystyle.kurlystyle.model.MyKurlyStyleUIModel
import com.kurly.features.mykurlystyle.kurlystyle.model.SiteProfileUIModel
import com.kurly.features.mykurlystyle.term.model.PrivacyPolicyUIModel
import com.kurly.kpds.compose.theme.KurlyTheme

@Composable
fun MyKurlyStyleScreen(
    viewModel: MyKurlyStyleViewModel,
    onStartSiteProfile: (SiteProfileUIModel) -> Unit,
    onShowPrivacyPolicyEvent: (PrivacyPolicyUIModel) -> Unit,
    onNavigateToComplete: () -> Unit,
    onShowError: (String?) -> Unit,
    onClearDataAndFinish: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val myKurlyStyleData by viewModel.myKurlyStyleData.collectAsStateWithLifecycle()
    val birthYear by viewModel.birthYearString.collectAsStateWithLifecycle()
    val isYearValid by viewModel.isYearValid.collectAsStateWithLifecycle()
    val ageGroup by viewModel.ageGroup.collectAsStateWithLifecycle()
    val isEnabledSave by viewModel.isEnabledSave.collectAsStateWithLifecycle()

    // UIState 이벤트 처리 (일회성)
    LaunchedEffect(uiState) {
        when (val state = uiState) {
            is MyKurlyStyleViewModel.UIState.SaveMyKurlyStyleSuccess -> onNavigateToComplete()
            is MyKurlyStyleViewModel.UIState.Error -> onShowError(state.errorMessage)
            else -> Unit
        }
    }

    // privacyPolicy 이벤트 처리 (Activity에서 Fragment 다이얼로그 표시)
    LaunchedEffect(Unit) {
        viewModel.privacyPolicyEvent.collect { onShowPrivacyPolicyEvent(it) }
    }

    MyKurlyStyleContent(
        myKurlyStyleData = myKurlyStyleData,
        birthYear = birthYear,
        isYearValid = isYearValid,
        ageGroup = ageGroup,
        isEnabledSave = isEnabledSave,
        isLoading = uiState is MyKurlyStyleViewModel.UIState.Loading,
        onBirthYearChange = { viewModel.birthYearString.value = it },
        onGenderSelect = { viewModel.setGender(it) },
        onToddlerToggle = { viewModel.toggleHasToddler() },
        onProfileVisibilityToggle = { viewModel.toggleIsOpenProfile() },
        onTermsClick = { viewModel.getPrivacyPolicy(com.kurly.features.mykurlystyle.kurlystyle.PrivacyPolicyAction.OPEN_DIALOG) },
        onTermsCheckToggle = { /* toggleIsAgreePrivacyPolicy 로직 이동 */ },
        onSaveClick = { viewModel.checkValidate() },
        onStartSiteProfile = onStartSiteProfile,
        onClearDataAndFinish = onClearDataAndFinish,
        modifier = modifier,
    )
}

@Composable
private fun MyKurlyStyleContent(
    myKurlyStyleData: MyKurlyStyleUIModel,
    birthYear: String,
    isYearValid: Boolean,
    ageGroup: String,
    isEnabledSave: Boolean,
    isLoading: Boolean,
    onBirthYearChange: (String) -> Unit,
    onGenderSelect: (com.kurly.domain.model.mykurlystyle.GenderType) -> Unit,
    onToddlerToggle: () -> Unit,
    onProfileVisibilityToggle: () -> Unit,
    onTermsClick: () -> Unit,
    onTermsCheckToggle: () -> Unit,
    onSaveClick: () -> Unit,
    onStartSiteProfile: (SiteProfileUIModel) -> Unit,
    onClearDataAndFinish: () -> Unit,
    modifier: Modifier = Modifier,
) {
    // TODO: 전체 UI 구현 (Task 2~3에서 채울 예정)
    // 현재는 스캐폴드만 작성
    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState()),
    ) {
        // TODO: BirthYearSection
        // TODO: GenderSection
        // TODO: ToddlerSection
        // TODO: SiteProfileList (Task 3에서 추가)
        // TODO: ProfileVisibilitySection
        // TODO: TermsAndSaveSection
    }
}
```

### Step 4: 빌드 확인

```bash
./gradlew :features:compileDebugKotlin
```

### Step 5: MyKurlyStyleContent 각 섹션 구현

각 섹션을 private Composable로 분리하여 구현:

**BirthYearSection** - `OutlinedTextField` (KPDS 없으면 Material3) + 나이 그룹 표시 + 유효성 메시지
**GenderSection** - `RadioButton` 3개 (남성/여성/선택안함) 수평 Row
**ToddlerSection** - `Checkbox` + 텍스트
**ProfileVisibilitySection** - `Switch` + 설명 텍스트
**TermsSection** - `Checkbox` + 약관 링크 텍스트 (`AnnotatedString` + `clickable`)
**SaveButton** - `KurlyButton` (enabled = isEnabledSave)

기존 `activity_my_kurly_style.xml`의 각 뷰를 1:1 매핑하여 구현. 문자열 리소스는 기존 strings.xml에 있는 것 재사용:
- `R.string.my_kurly_style_title`
- `R.string.my_kurly_style_birth_year_hint`
- `R.string.my_kurly_style_age_group_*`
- `R.string.my_kurly_style_profile_required_term`

### Step 6: 빌드 + Preview 확인

```bash
./gradlew :features:compileDebugKotlin
```

Android Studio에서 Preview 렌더링 확인.

### Step 7: 커밋

```bash
/commit
```

---

## Task 3 (KMA-7055): LazyColumn + 프로필 리스트 연동

**목표:** `rvSiteProfiles` RecyclerView를 LazyColumn으로 교체. `SiteProfileItem` 연동. Activity Result 콜백 유지.

### Step 1: MyKurlyStyleContent에 SiteProfileList 추가

`MyKurlyStyleContent` 내부의 `// TODO: SiteProfileList` 부분을 채운다:

```kotlin
// MyKurlyStyleScreen.kt 내부

@Composable
private fun SiteProfileListSection(
    sites: List<SiteProfileUIModel>,
    onStartSiteProfile: (SiteProfileUIModel) -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(modifier = modifier.fillMaxWidth()) {
        sites.forEach { profile ->
            SiteProfileItem(
                profile = profile,
                onProfileClick = onStartSiteProfile,
            )
            // 구분선 (기존 dividerBuilder() 대체)
            androidx.compose.material3.HorizontalDivider(
                color = KurlyTheme.colors.gray200,
                thickness = 1.dp,
            )
        }
    }
}
```

> **Note:** LazyColumn 대신 `forEach`를 사용하는 이유: 전체 화면이 이미 `NestedScrollView` 구조이고, 프로필 수가 적기 때문(현재 마켓컬리 단일 또는 소수). LazyColumn을 쓰려면 외부 `verticalScroll`을 제거하고 `LazyColumn`으로 전체 화면을 감싸야 한다. 아이템이 많아지면 그때 LazyColumn으로 전환할 것.
>
> 만약 LazyColumn으로 구현한다면 전체 화면 구조를 다음처럼 변경:
> ```kotlin
> LazyColumn {
>     item { BirthYearSection(...) }
>     item { GenderSection(...) }
>     item { ToddlerSection(...) }
>     items(items = sites, key = { it.id }) { profile ->
>         SiteProfileItem(profile = profile, onProfileClick = onStartSiteProfile)
>         HorizontalDivider(...)
>     }
>     item { ProfileVisibilitySection(...) }
>     // 저장 버튼은 하단 고정이므로 Scaffold bottomBar로 분리
> }
> ```

### Step 2: UpdateSiteProfile 상태 처리

기존 Activity의 `updateList(state.sites)` 로직 → Screen에서 UIState 관찰로 처리:

현재 `myKurlyStyleData`는 `UpdateSiteProfile` 상태가 emit되면 `viewModel.updateSiteProfile()` 내부에서
`myKurlyStyleData`도 함께 업데이트된다. 따라서 `myKurlyStyleData`를 `collectAsStateWithLifecycle`로
수집하면 자동으로 UI가 갱신된다. 별도 처리 불필요.

### Step 3: Activity Result 연동 확인

`siteProfileLauncher`는 Activity에서 그대로 유지. 결과 수신 후 `viewModel.updateSiteProfile(newProfile)` 호출 → `myKurlyStyleData` 업데이트 → Screen 자동 리컴포지션.

변경 불필요.

### Step 4: 빌드 + 수동 테스트

```bash
./gradlew :features:compileDebugKotlin
```

기기/에뮬레이터에서 프로필 목록이 표시되는지 확인하려면 먼저 Task 4(Activity 전환)를 완료해야 한다.
Preview에서 `SiteProfileListSection` Preview 추가:

```kotlin
@Preview(showBackground = true)
@Composable
private fun SiteProfileListSectionPreview() {
    KurlyTheme {
        SiteProfileListSection(
            sites = listOf(
                SiteProfileUIModel("1", "마켓컬리", "설명", "", false, false, ""),
                SiteProfileUIModel("2", "컬리나우", "설명", "", false, true, "30대 여성"),
            ),
            onStartSiteProfile = {},
        )
    }
}
```

### Step 5: 커밋

```bash
/commit
```

---

## Task 4 (KMA-7056): Activity Compose 전환 + XML 제거

**목표:** `setContentView` → `setContent`, XML 레이아웃 삭제, Adapter/ViewHolder/Controller 삭제.

### Step 1: MyKurlyStyleActivity.kt 전환

`DataBindingUtil.setContentView(...)` 를 `setContent { ... }` 로 교체:

```kotlin
// Before (onCreate):
binding = DataBindingUtil.setContentView(this, R.layout.activity_my_kurly_style)
binding.lifecycleOwner = this
binding.viewModel = viewModel
setupWindowInsets(binding.root)
initView()
initViewModel()

// After (onCreate):
enableEdgeToEdge()
setContent {
    KurlyTheme {
        MyKurlyStyleScreen(
            viewModel = viewModel,
            onStartSiteProfile = { profile -> onStartSiteProfile(profile) },
            onShowPrivacyPolicyEvent = { privacyPolicy -> showPrivacyTermDialog(privacyPolicy) },
            onNavigateToComplete = { startCompleteActivity() },
            onShowError = { message -> showError(message) },
            onClearDataAndFinish = { clearDataAndFinish() },
        )
    }
}
BroadcastAction.REFRESH_MY_KURLY_NOTIFICATION
    .replaceExtras(bundleOf(BroadcastAction.EXTRA_NOTIFICATION_PROFILE to true))
    .send(this)
```

제거 대상 (Activity에서 삭제):
- `binding: ActivityMyKurlyStyleBinding` 필드
- `profileAdapter: SiteProfileAdapter` 필드
- `initView()` 메서드 전체
- `initViewModel()` 메서드 전체 (LaunchedEffect로 이동됨)
- `initToolBar()` 메서드 전체
- `initRecyclerView()` 메서드 전체
- `handleState()`, `handleProgressbar()`, `handleKurlyStyleData()`, `updateList()` 메서드 전체
- `handleError()` 메서드 → Activity 레벨 `showError()` 메서드로 대체

Activity에 남기는 메서드 (그대로 유지):
- `siteProfileLauncher` (Activity Result)
- `startCompleteActivity()` (navigation + finish)
- `onStartSiteProfile()` (controller 구현 → 람다로 전달)
- `showPrivacyTermDialog()` + `showPrivacyTermBottomSheet()` + `showPrivacyTermExpiredBottomSheet()` (Fragment 다이얼로그)
- `showFinishMyKurlyStyleDialog()` (뒤로가기 팝업)
- `showPolicyAgreeCancelDialog()` (약관 해제 팝업)
- `clearDataAndShowSnackbar()` → `clearDataAndFinish()` 로 리네임
- `sendScreenName()` (`onResume`)
- `onOptionsItemSelected()` (뒤로가기 버튼 처리)
- `onBackPressed()` (뒤로가기)

> **주의:** Toolbar/ActionBar는 Compose의 `TopAppBar`로 대체하므로 `setSupportActionBar`, `supportActionBar` 호출도 제거. `onOptionsItemSelected`의 `android.R.id.home` 처리는 Screen의 NavigationIcon `onClick` 콜백으로 이동.

`MyKurlyStyleController` 인터페이스는 더 이상 불필요하므로:
- `MyKurlyStyleActivity : AppCompatActivity(), MyKurlyStyleController` → `MyKurlyStyleActivity : AppCompatActivity()`

### Step 2: 빌드

```bash
./gradlew :features:compileDebugKotlin
```

컴파일 에러를 순서대로 수정. 주요 예상 오류:
- `binding.*` 참조 → 제거
- `profileAdapter.*` 참조 → 제거
- `initStatusBar()` → Compose Activity에서는 `WindowCompat.setDecorFitsSystemWindows(window, false)` 또는 `enableEdgeToEdge()`로 대체

### Step 3: XML 레이아웃 삭제

```
features/src/main/res/layout/activity_my_kurly_style.xml  ← 삭제
features/src/main/res/layout/list_item_kurly_profile.xml  ← 삭제
```

### Step 4: 불필요한 클래스 삭제

```
features/.../kurlystyle/adapter/SiteProfileAdapter.kt          ← 삭제
features/.../kurlystyle/adapter/viewholder/SiteProfileViewHolder.kt ← 삭제
features/.../kurlystyle/adapter/diff/SiteProfileDiffUtil.kt    ← 삭제
features/.../kurlystyle/controller/MyKurlyStyleController.kt   ← 삭제
```

### Step 5: DataBinding import 정리

ViewModel에서 DataBinding 관련 import 제거:
- `NonNullLiveData` import 제거 (이미 Step 2에서 제거됨)

Activity에서 제거:
```kotlin
import androidx.databinding.DataBindingUtil
import com.fondesa.recyclerviewdivider.dividerBuilder
import com.kurly.features.databinding.ActivityMyKurlyStyleBinding
import com.kurly.features.mykurlystyle.kurlystyle.adapter.SiteProfileAdapter
import com.kurly.features.mykurlystyle.kurlystyle.controller.MyKurlyStyleController
```

추가:
```kotlin
import androidx.activity.compose.setContent
import com.kurly.kpds.compose.theme.KurlyTheme
```

### Step 6: 전체 빌드 + 린트

```bash
./gradlew :features:assembleDebug
./gradlew :features:lintDebug
```

Expected: BUILD SUCCESSFUL, lint 경고 없음 (또는 기존 경고 수준 유지)

### Step 7: 수동 테스트 체크리스트

- [ ] 화면 진입 → 프로필 로딩 표시
- [ ] 생년 입력 → 나이 그룹 실시간 표시
- [ ] 성별 선택 → 저장 버튼 활성화
- [ ] 저장 버튼 클릭 → 완료 화면 이동
- [ ] 프로필 카드 클릭 (첫 진입) → StepProfileActivity 이동
- [ ] 프로필 카드 클릭 (재진입) → ListProfileActivity 이동
- [ ] 프로필 수정 후 돌아오기 → 목록 갱신
- [ ] 약관 링크 클릭 → ProfileRequiredTermDialog 표시
- [ ] 약관 체크 해제 → 동의 취소 팝업
- [ ] 뒤로가기 → 미완료 팝업
- [ ] 개인정보 약관 Disagree/Expired 시 → BottomSheet 표시
- [ ] Loading 상태 → 프로그레스 표시

### Step 8: 커밋

```bash
/commit
```

---

## 사이드 이펙트 유의 사항

| 구분 | 항목 | 대응 방법 |
|------|------|-----------|
| 연동 | `siteProfileLauncher`, `EXTRA_SITE_PROFILE` | Activity에서 유지. 변경 없음. |
| 기능 | PrivacyPolicy 다이얼로그/바텀시트 | 기존 Fragment 다이얼로그 유지. Activity에서 호출. |
| 분석 | `ScreenName.MyKurlyStyle`, `SelectBackButton`, `SelectProfile` | 유지. 위치만 Activity→Screen 이벤트로 이동. |
| 연동 | `BroadcastAction.REFRESH_MY_KURLY_NOTIFICATION` | Activity `onCreate`에서 유지. |
| UI | 상단 스낵바 (`SimpleSnackbar`) | `window.decorView` 기반 → Compose의 `SnackbarHostState` 또는 Activity decorView 사용 |

---

## 각 Task의 티켓 매핑

| Task | Jira 티켓 | 예상 공수 |
|------|----------|----------|
| Task 1 | KMA-7053 | 1주 |
| Task 2 | KMA-7054 | 1.5주 |
| Task 3 | KMA-7055 | 1주 |
| Task 4 | KMA-7056 | 0.5주 |
| 테스트/버퍼 | - | 0.5주 |
| **합계** | **KMA-7033** | **4.5~5주** |
