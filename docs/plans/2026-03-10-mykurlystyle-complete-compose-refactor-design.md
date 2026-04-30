# Design: MyKurlyStyleCompleteActivity Compose 개선

- **날짜**: 2026-03-10
- **브랜치**: feature/KMA-7046-compose
- **레퍼런스**: PR #7136 (KMA-7033 MyKurlyStyle Compose 전환)

## 목표

Activity를 최대한 가볍게 유지하고, PR 7136의 `MyKurlyStyleActivity` 패턴에 맞춰 Compose 친화적인 구조로 개선한다.

## 변경 범위

### 1. Activity (`MyKurlyStyleCompleteActivity`)

**제거:**
- `private val viewModel by viewModels()` — Route가 `hiltViewModel()`로 직접 보유
- `repeatOnStarted { viewModel.navigation.collect {...} }` — Route의 `LaunchedEffect`로 이동
- `handleNavigation(navigation: Navigation)` 메서드

**유지:**
- `@Inject lateinit var myKurlyStyleDelegator` — Context 필요한 navigation은 Activity 책임
- `@Inject lateinit var amplitudeSender` — `sendScreenName()` 외 다른 이벤트도 있으므로 유지
- `override fun onResume() { amplitudeSender.sendScreenName() }` — PR 7136 패턴과 동일

**추가:**
- Route에 `onNavigateToProductDetail`, `onNavigateToMain` lambda 전달

**결과:**
```kotlin
@AndroidEntryPoint
class MyKurlyStyleCompleteActivity : AppCompatActivity() {
    @Inject lateinit var myKurlyStyleDelegator: MyKurlyStyleDelegator
    @Inject lateinit var amplitudeSender: MyKurlyStyleCompleteAmplitudeSender

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            KurlyTheme(darkTheme = false) {
                MyKurlyStyleCompleteRoute(
                    onFinish = ::finish,
                    onNavigateToProductDetail = { item, referrerEventName ->
                        myKurlyStyleDelegator.startProductDetail(this, item, referrerEventName)
                    },
                    onNavigateToMain = { siteFilterType ->
                        myKurlyStyleDelegator.startMainActivity(this, siteFilterType)
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

### 2. Route (`MyKurlyStyleCompleteRoute`)

**제거:**
- `var errorMessage by remember { mutableStateOf<String?>(null) }` 중간 상태
- `MyKurlyStyleCompleteScreen`에 `errorMessage` 파라미터 전달

**추가:**
- `onNavigateToProductDetail`, `onNavigateToMain` 파라미터
- `snackbarHostState` Route로 이동 (Screen에서 올라옴)
- `LaunchedEffect(Unit)` — navigation Channel 수집
- `LaunchedEffect(Unit)` — errorEvent Channel 수집 후 snackbar 직접 호출

**결과:**
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

### 3. ViewModel (`MyKurlyStyleCompleteViewModel`)

**이름 변경 (PR 7136 컨벤션 통일):**
- `_errorMessage` → `_errorEvent`
- `errorMessages` → `errorEvent`

로직 변경 없음.

### 4. Screen (`MyKurlyStyleCompleteScreen`)

**파라미터 변경:**
- `errorMessage: String?` 제거
- `snackbarHostState: SnackbarHostState` 추가

**제거:**
- `LaunchedEffect(errorMessage) { snackbarHostState.showSnackbar(errorMessage) }` — Route에서 처리

## 영향 범위

- `MyKurlyStyleCompleteActivity.kt`
- `MyKurlyStyleCompleteViewModel.kt`
- `MyKurlyStyleCompleteScreen.kt` (Route + Screen)
- 테스트: `errorMessages` → `errorEvent` 이름 변경 반영 필요

## 비변경 대상

- `Navigation` sealed class — 구조 그대로
- `Action` sealed class — 구조 그대로
- `RecommendResultUIModel` — 변경 없음
- ViewModel 비즈니스 로직 — 변경 없음
