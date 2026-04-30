# MyKurlyStyle Activity → Route 이벤트 흐름 설계

**날짜:** 2026-03-05
**티켓:** KMA-7033
**맥락:** MyKurlyStyleActivity의 잔여 이벤트 처리 로직을 Compose Route로 이관

---

## 핵심 원칙

### State vs Event 판별 기준

| 기준 | 적용 |
|------|------|
| "조건이 참인 동안 보여줘" | → **State** (StateFlow) |
| "지금 이 순간 발생했으니 처리해" | → **Event** (Channel) |

다이얼로그/바텀시트는 사용자가 dismiss할 때까지 유지되어야 하고, 화면 회전에도 살아있어야 함 → **State**

스낵바/네비게이션은 발생 시점이 중요하고, 프로세스 복원 시 재현 불필요 → **Event**

---

## 최종 이벤트 구조

### Channel (Event) — 일회성

```kotlin
sealed interface MyKurlyStyleEvent {
    data class NavigateToComplete(val siteId: String?) : MyKurlyStyleEvent
    // 변경: SaveMyKurlyStyleSuccess → NavigateToComplete (siteId 포함)
}

val uiEvent: Flow<MyKurlyStyleEvent>   // NavigateToComplete 하나
val errorEvent: Flow<String?>          // 현행 유지
```

### StateFlow (State) — 지속 조건

```kotlin
// 기존 유지
val myKurlyStyleData: StateFlow<MyKurlyStyleUIModel>
val birthYearString: StateFlow<String>
val isYearValid: StateFlow<Boolean>
val ageGroup: StateFlow<String>
val isEnabledSave: StateFlow<Boolean>

// 신규 추가 (Channel에서 State로 전환)
val privacyPolicyToShow: StateFlow<PrivacyPolicyUIModel?>   // null = 숨김
val showPolicyAgreeCancelDialog: StateFlow<Boolean>
```

---

## 제거 항목

| 제거 | 이유 |
|------|------|
| `ShowPrivacyPolicySheet` 이벤트 | Activity가 코디네이터였기 때문에 생긴 인공 이벤트 |
| `privacyPolicyEvent: Channel<PrivacyPolicyUIModel>` | State로 대체 |
| `showPolicyAgreeCancelEvent: Channel<Unit>` | State로 대체 |
| `ClearDataAndFinish` 이벤트 (미도입) | Route가 사용자 액션 맥락을 이미 앎 |

---

## ViewModel 내부 변경

### ShowPrivacyPolicySheet 제거

Activity가 `ShowPrivacyPolicySheet`를 받아 `getPrivacyPolicy()`를 재호출하는 왕복 구조 제거.
ViewModel이 내부에서 직접 연결:

```kotlin
// Before: ViewModel → (이벤트) → Activity → ViewModel
_uiEvent.send(ShowPrivacyPolicySheet)
// Activity: viewModel.getPrivacyPolicy(OPEN_BOTTOMSHEET)

// After: ViewModel 내부에서 직접
private fun getMyKurlyStyle() {
    // ...성공 시
    if (data.privacyPolicyStatus != PrivacyPolicyStatusType.AGREE) {
        getPrivacyPolicy(PrivacyPolicyAction.OPEN_BOTTOMSHEET)  // 직접 호출
    }
}
```

### NavigateToComplete — siteId 포함

Activity에 있던 `startCompleteActivity()`의 siteId 계산 로직을 ViewModel로 이동:

```kotlin
// siteId 결정 로직은 ViewModel이 알아야 할 도메인 지식
private fun saveMyKurlyStyle(params: ...) {
    // 성공 시
    val siteId = _myKurlyStyleData.value.sites.getOrNull(0)?.let {
        if (it.hasProfile) it.id else null
    }
    _uiEvent.send(MyKurlyStyleEvent.NavigateToComplete(siteId))
}
```

---

## Route 책임

```kotlin
@Composable
fun MyKurlyStyleRoute(
    onNavigateBack: () -> Unit,
    onNavigateToComplete: (siteId: String?) -> Unit,
    onSiteProfileClick: (SiteProfileUIModel) -> Unit,
    viewModel: MyKurlyStyleViewModel = hiltViewModel(),
) {
    val snackBarHostState = remember { KurlySnackBarHostState() }
    val coroutineScope = rememberCoroutineScope()

    // State 수집
    val privacyPolicyToShow by viewModel.privacyPolicyToShow.collectAsStateWithLifecycle()
    val showPolicyAgreeCancelDialog by viewModel.showPolicyAgreeCancelDialog.collectAsStateWithLifecycle()

    // Event 수집
    LaunchedEffect(Unit) {
        viewModel.errorEvent.collect { message ->
            message?.let { snackBarHostState.showSnackBar(it, SnackBarType.ERROR) }
        }
    }
    LaunchedEffect(Unit) {
        viewModel.uiEvent.collect { event ->
            when (event) {
                is MyKurlyStyleEvent.NavigateToComplete -> onNavigateToComplete(event.siteId)
            }
        }
    }

    // 다이얼로그 — State 기반 (화면 회전에도 유지)
    if (showPolicyAgreeCancelDialog) {
        PolicyAgreeCancelDialog(
            onConfirm = {
                viewModel.onAction(MyKurlyStyleAction.PolicyAgreeCancelConfirm)
                coroutineScope.launch {
                    snackBarHostState.showSnackBar(
                        message = "...",
                        snackBarType = SnackBarType.INFO,
                    )
                    // showSnackBar는 suspend → 완료 후 navigate (현행 addCallback과 동일 타이밍)
                    onNavigateBack()
                }
            },
            onDismiss = {
                viewModel.onAction(MyKurlyStyleAction.DismissPolicyAgreeCancelDialog)
            },
        )
    }

    // 바텀시트 — State 기반
    privacyPolicyToShow?.let { policy ->
        PrivacyPolicyBottomSheet(
            policy = policy,
            onAgree = {
                viewModel.onAction(MyKurlyStyleAction.AgreePrivacyPolicy)
            },
            onDisagree = {
                // isExpired에 따라 분기 → ViewModel이 상태로 노출
            },
            onDismiss = {
                viewModel.onAction(MyKurlyStyleAction.DismissPrivacyPolicy)
            },
        )
    }

    // ...
}
```

---

## Activity — 최종 형태

```kotlin
@AndroidEntryPoint
class MyKurlyStyleActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        setContent {
            KurlyTheme {
                MyKurlyStyleRoute(
                    onNavigateBack = { finish() },
                    onNavigateToComplete = { siteId ->
                        startActivity(
                            Intent(this, MyKurlyStyleCompleteActivity::class.java)
                                .apply { putExtra(SITE_ID, siteId) }
                        )
                        finish()
                    },
                    onSiteProfileClick = { siteProfile ->
                        // rememberLauncherForActivityResult로 이동 후 제거 예정
                        onStartSiteProfile(siteProfile)
                    },
                )
            }
        }

        BroadcastAction.REFRESH_MY_KURLY_NOTIFICATION
            .replaceExtras(bundleOf(BroadcastAction.EXTRA_NOTIFICATION_PROFILE to true))
            .send(this)
    }

    override fun onResume() {
        super.onResume()
        AmplitudeShareData.screenName = ScreenName.MyKurlyStyle
    }
}
// initViewModel(), handleEvent(), showPolicyAgreeCancelDialog(),
// showPrivacyTermBottomSheet(), showPrivacyTermExpiredBottomSheet(),
// clearDataAndShowSnackbar() 전부 제거
```

---

## 스낵바 타이밍

`clearDataAndShowSnackbar()`의 `addCallback { finish() }` 패턴을
`showSnackBar()` suspend 특성으로 대체:

```kotlin
// Before (View)
SimpleSnackbar.make(...).addCallback(
    SimpleSnackbar.SimpleAfterActionCallback { finish() }
).show()

// After (Compose)
coroutineScope.launch {
    snackBarHostState.showSnackBar(...)  // suspend — 표시 완료까지 대기
    onNavigateBack()                     // 이후 실행
}
```

같은 인스턴스(`snackBarHostState`)를 Route에서 생성해 Screen/Scaffold에 전달하므로
Route 어디서든 호출해도 Scaffold의 `KurlySnackBarHost`가 렌더링함.
