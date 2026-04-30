# MyKurlyStyle Compose 이벤트 흐름 설계

> 작성일: 2026-03-06
> 브랜치: feature/KMA-7033_mykurlystyle_compose
> 관련 티켓: KMA-7033 (부모), KMA-7312, KMA-7313, KMA-7314

---

## 핵심 원칙

**다이얼로그/바텀시트 표시 상태 결정 기준:**

- 유저 액션으로 기인 → ViewModel StateFlow
- API 응답/ViewModel 내부 로직으로 기인 → ViewModel StateFlow
- 단순 파생 상태 (기존 StateFlow에서 읽을 수 있는 것) → View layer

이 화면에서 모든 모달 상태는 ViewModel을 통한다.

---

## ModalState 설계

`PrivacyPolicyAction`(OPEN_DIALOG / OPEN_BOTTOMSHEET) 분기를 타입 레벨로 표현하여
Route에서 `model.action` 체크를 제거한다.

```kotlin
sealed interface ModalState {
    data object None : ModalState

    // 약관 텍스트 클릭 → 읽기전용 다이얼로그 (OPEN_DIALOG)
    data class PrivacyPolicyDialog(
        val model: PrivacyPolicyUIModel,
    ) : ModalState

    // 진입 시 미동의/만료 + 체크박스 미동의 클릭 → 동의 바텀시트 (OPEN_BOTTOMSHEET)
    data class PrivacyPolicySheet(
        val model: PrivacyPolicyUIModel,
        val showExpiredOverlay: Boolean = false,
    ) : ModalState

    // 체크박스 클릭 (이미 동의 상태) → 동의 철회 확인 다이얼로그
    data object PolicyAgreeCancel : ModalState
}
```

`showExpiredOverlay`는 EXPIRED 상태에서 비동의 클릭 시 만료 취소 시트가 위에 쌓이는 상태를 표현한다.
별도 StateFlow를 두지 않고 `PrivacyPolicySheet` 컨텍스트 안에서만 존재하므로 불가능한 상태가 타입 레벨에서 차단된다.

---

## ViewModel 변경

### 제거

```kotlin
_privacyPolicyEvent: Channel<PrivacyPolicyUIModel>
_showPolicyAgreeCancelEvent: Channel<Unit>
ShowPrivacyPolicySheet: MyKurlyStyleEvent
```

### 추가

```kotlin
private val _modalState = MutableStateFlow<ModalState>(ModalState.None)
val modalState: StateFlow<ModalState> = _modalState.asStateFlow()
```

### Channel 최종 (2개만 유지)

```kotlin
val uiEvent: Flow<MyKurlyStyleEvent>   // NavigateToComplete(siteId) 하나만
val errorEvent: Flow<String?>          // 현행 유지
```

### 내부 로직 변경

```kotlin
// getMyKurlyStyle() 성공 시 — Activity 코디네이터 역할 제거
.onSuccess { data ->
    if (data.privacyPolicyStatus == DISAGREE || data.privacyPolicyStatus == EXPIRED) {
        getPrivacyPolicy(OPEN_BOTTOMSHEET)  // ViewModel이 직접 호출
    }
}

// getPrivacyPolicy() 결과 처리
_modalState.update {
    if (action == OPEN_DIALOG) ModalState.PrivacyPolicyDialog(model)
    else ModalState.PrivacyPolicySheet(model)
}

// siteId 계산 — Activity.startCompleteActivity()에서 이동
val siteId = myKurlyStyleData.value.sites.firstOrNull { it.isSelected }?.id
_uiEvent.send(MyKurlyStyleEvent.NavigateToComplete(siteId))
```

### Action 추가

```kotlin
sealed interface MyKurlyStyleAction {
    // 기존 유지...

    data object AgreePrivacyPolicy : MyKurlyStyleAction
    data object DismissPrivacyPolicy : MyKurlyStyleAction       // 비동의 (EXPIRED면 showExpiredOverlay = true)
    data object DismissExpiredOverlay : MyKurlyStyleAction      // 만료 시트 취소
    data object PolicyAgreeCancelConfirm : MyKurlyStyleAction   // 동의 철회 확인
    data object DismissPolicyAgreeCancelDialog : MyKurlyStyleAction
}
```

---

## Route 구조

### ModalHost 분리

Route가 모달 종류를 직접 나열하지 않도록 `MyKurlyStyleModalHost`로 추출한다.

```kotlin
@Composable
fun MyKurlyStyleRoute(...) {
    // state 수집, snackbar, navigation 처리
    MyKurlyStyleScreen(uiState, onAction)
    MyKurlyStyleModalHost(
        modalState = modalState,
        onAction = viewModel::onAction,
    )
}

@Composable
private fun MyKurlyStyleModalHost(
    modalState: ModalState,
    onAction: (MyKurlyStyleAction) -> Unit,
) {
    when (val modal = modalState) {
        is ModalState.PrivacyPolicyDialog ->
            PrivacyPolicyTableDialog(
                model = modal.model,
                onDismiss = { onAction(MyKurlyStyleAction.DismissPrivacyPolicy) },
            )

        is ModalState.PrivacyPolicySheet -> {
            PrivacyPolicyBottomSheet(
                model = modal.model,
                isExpired = modal.model.action == OPEN_BOTTOMSHEET && ...,
                onAgree = { onAction(MyKurlyStyleAction.AgreePrivacyPolicy) },
                onDisagree = { onAction(MyKurlyStyleAction.DismissPrivacyPolicy) },
            )
            if (modal.showExpiredOverlay) {
                ExpiredCancelBottomSheet(
                    onConfirm = { onAction(MyKurlyStyleAction.PolicyAgreeCancelConfirm) },
                    onCancel = { onAction(MyKurlyStyleAction.DismissExpiredOverlay) },
                )
            }
        }

        is ModalState.PolicyAgreeCancel ->
            KurlyAlertDialog(
                onConfirm = { onAction(MyKurlyStyleAction.PolicyAgreeCancelConfirm) },
                onDismiss = { onAction(MyKurlyStyleAction.DismissPolicyAgreeCancelDialog) },
            )

        is ModalState.None -> Unit
    }
}
```

### siteProfileLauncher 이동

```kotlin
// Activity → Route
val siteProfileLauncher = rememberLauncherForActivityResult(
    contract = ActivityResultContracts.StartActivityForResult()
) { result ->
    if (result.resultCode == RESULT_OK) {
        val siteProfile = result.data?.getParcelableExtra<SiteProfileUIModel>(EXTRA_SITE_PROFILE)
        siteProfile?.let { viewModel.onAction(MyKurlyStyleAction.UpdateSiteProfile(it)) }
    }
}
```

Single Activity 전환 시에도 이 위치가 올바른 패턴이다.

---

## Activity 최종 형태

```kotlin
class MyKurlyStyleActivity : AppCompatActivity() {

    override fun onCreate(...) {
        setContent {
            KurlyTheme {
                MyKurlyStyleRoute(
                    onNavigateBack = { finish() },
                    onNavigateToComplete = { siteId -> startCompleteActivity(siteId) },
                )
            }
        }
    }

    private fun startCompleteActivity(siteId: String?) {
        startActivity(Intent(this, MyKurlyStyleCompleteActivity::class.java).apply {
            putExtra(EXTRA_SITE_ID, siteId)
        })
        finish()
    }
}
```

---

## Composable 인터페이스 설계 (Phase 1 구현 기준)

### PrivacyPolicyBottomSheet (KMA-7312)

```kotlin
@Composable
fun PrivacyPolicyBottomSheet(
    model: PrivacyPolicyUIModel,
    isExpired: Boolean,
    onAgree: () -> Unit,
    onDisagree: () -> Unit,       // 분기 없음 — ModalHost가 처리
    modifier: Modifier = Modifier,
)
```

- `isCancelable = false` → `onDismissRequest = {}` + `BackHandler {}`
- `isExpired = true`일 때 NEW 뱃지 표시
- `skipPartiallyExpanded = true`

### ExpiredCancelBottomSheet (KMA-7313)

```kotlin
@Composable
fun ExpiredCancelBottomSheet(
    onConfirm: () -> Unit,
    onCancel: () -> Unit,
    modifier: Modifier = Modifier,
)
```

- Spannable 빨간 강조 → `buildAnnotatedString { withStyle(SpanStyle(color = Red)) }`
- `isCancelable = false` 동일 처리

### PrivacyPolicyTableDialog (KMA-7314)

```kotlin
@Composable
fun PrivacyPolicyTableDialog(
    model: PrivacyPolicyUIModel,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier,
)
```

- TableLayout 3열 → `Row` + `Modifier.weight(1f)` 각 셀
- 읽기전용, "동의" 버튼 하나

---

## 구현 단계

### Phase 1 — KMA-7312 / KMA-7313 / KMA-7314

Fragment 3개를 Composable로 독립 구현. ViewModel/Activity 연결 없음. Fragment는 유지.

| 티켓 | 작업 |
|---|---|
| KMA-7312 | `PrivacyPolicyBottomSheet` Composable + Preview |
| KMA-7313 | `ExpiredCancelBottomSheet` Composable + Preview |
| KMA-7314 | `PrivacyPolicyTableDialog` Composable + Preview |

### Phase 2 — 별도 티켓 (Activity/ViewModel 리팩토링)

1. `ModalState` sealed class 추가
2. ViewModel Channel → StateFlow 전환 + Action 추가
3. ViewModel 테스트 수정
4. Route에 `MyKurlyStyleModalHost` 추가 + siteProfileLauncher 이동
5. Activity 정리
6. Fragment 파일 3개 + XML 3개 제거

---

## 제거 대상 (Phase 2)

```
ProfileRequiredTermFragment.kt
ProfileRequiredTermExpiredFragment.kt
ProfileRequiredTermDialog.kt

fragment_profile_required_term.xml
fragment_profile_required_term_expired.xml
dialog_profile_required_term.xml
```
