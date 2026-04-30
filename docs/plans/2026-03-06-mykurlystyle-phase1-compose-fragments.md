# MyKurlyStyle Phase 1 — Fragment → Compose 전환 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** ProfileRequiredTerm Fragment 3개를 독립적인 Compose 컴포넌트로 전환한다. ViewModel/Activity 연결 없이 순수 UI 구현만 진행한다.

**Architecture:** 각 Composable은 stateless로 설계하며 콜백만 주입받는다. isCancelable=false는 `onDismissRequest = {}` + `BackHandler {}`로 처리한다. 분기 로직(EXPIRED 시 시트 전환)은 이 컴포넌트 책임이 아니며 Phase 2 ModalHost에서 처리한다.

**Tech Stack:** Jetpack Compose, KPDS (`com.kurly.kpds.compose`), Material3 ModalBottomSheet/AlertDialog

**참고 설계 문서:** `docs/plans/2026-03-06-mykurlystyle-compose-event-flow-design.md`

---

## Task 1: PrivacyPolicyBottomSheet (KMA-7312)

**레퍼런스:** `ProfileRequiredTermFragment` + `fragment_bottom_sheet_profile_required_terms.xml`

**UI 구조:**
- 상단: 타이틀 "개인정보 처리방침" (18sp bold) + isExpired일 때 NEW 뱃지
- 중단: 수집 목적 / 수집 항목 / 보유 및 이용기간 (레이블 + 값 vertical 나열) + description
- 하단: 비동의(outline) | 동의(filled purple) 버튼 2개
- isCancelable = false, 항상 EXPANDED

**Files:**
- Create: `features/src/main/java/com/kurly/features/mykurlystyle/term/compose/PrivacyPolicyBottomSheet.kt`

---

**Step 1: 파일 생성 및 기본 구조 작성**

```kotlin
package com.kurly.features.mykurlystyle.term.compose

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.kurly.features.R
import com.kurly.features.mykurlystyle.kurlystyle.PrivacyPolicyAction
import com.kurly.features.mykurlystyle.term.model.PrivacyPolicyUIModel
import com.kurly.kpds.compose.component.button.boxbutton.KurlyBoxButton
import com.kurly.kpds.compose.component.button.boxbutton.KurlyBoxButtonStyle
import com.kurly.kpds.compose.foundation.ColorTokens
import com.kurly.kpds.compose.foundation.KurlyTheme

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PrivacyPolicyBottomSheet(
    model: PrivacyPolicyUIModel,
    isExpired: Boolean,
    onAgree: () -> Unit,
    onDisagree: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)

    // isCancelable = false
    BackHandler {}

    ModalBottomSheet(
        onDismissRequest = {},
        sheetState = sheetState,
        modifier = modifier,
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .navigationBarsPadding(),
        ) {
            // 타이틀 + NEW 뱃지
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier
                    .padding(horizontal = 20.dp)
                    .padding(top = 32.dp, bottom = 4.dp),
            ) {
                Text(
                    text = stringResource(R.string.profile_terms_privacy),
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Bold,
                    color = ColorTokens.Gray800.toColor(),
                )
                if (isExpired) {
                    KurlyTheme.spacers.width4()
                    // NEW 뱃지: ic_common_new_badge drawable 사용
                    androidx.compose.foundation.Image(
                        painter = androidx.compose.ui.res.painterResource(R.drawable.ic_common_new_badge),
                        contentDescription = null,
                    )
                }
            }

            // 약관 내용
            PrivacyPolicyContent(
                model = model,
                modifier = Modifier.padding(horizontal = 20.dp, vertical = 16.dp),
            )

            // 버튼 영역
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 12.dp)
                    .padding(top = 24.dp, bottom = 8.dp),
            ) {
                KurlyBoxButton(
                    text = stringResource(R.string.profile_terms_privacy_disagree),
                    onClick = onDisagree,
                    style = KurlyBoxButtonStyle.Secondary,
                    modifier = Modifier.weight(1f),
                )
                KurlyTheme.spacers.width8()
                KurlyBoxButton(
                    text = stringResource(R.string.member_profile_terms_privacy_agree),
                    onClick = onAgree,
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }
}

@Composable
private fun PrivacyPolicyContent(
    model: PrivacyPolicyUIModel,
    modifier: Modifier = Modifier,
) {
    Column(modifier = modifier) {
        PrivacyPolicyItem(
            label = "수집 목적",
            value = model.purpose,
        )
        PrivacyPolicyItem(
            label = "수집 항목",
            value = model.items,
        )
        PrivacyPolicyItem(
            label = "보유 및 이용기간",
            value = model.period,
        )
        KurlyTheme.spacers.height8()
        Text(
            text = model.description,
            fontSize = 14.sp,
            color = ColorTokens.Gray800.toColor(),
        )
    }
}

@Composable
private fun PrivacyPolicyItem(
    label: String,
    value: String,
    modifier: Modifier = Modifier,
) {
    Column(modifier = modifier) {
        Text(
            text = label,
            fontSize = 14.sp,
            color = ColorTokens.Gray800.toColor(),
            modifier = Modifier.padding(bottom = 3.dp),
        )
        Text(
            text = value,
            fontSize = 13.sp,
            color = ColorTokens.Gray450.toColor(),
            modifier = Modifier.padding(bottom = 8.dp),
        )
    }
}
```

**Step 2: Preview 추가 (동작 확인)**

파일 하단에 추가:

```kotlin
// ─── Previews ──────────────────────────────────────────────────────────────

private val dummyModel = PrivacyPolicyUIModel(
    action = PrivacyPolicyAction.OPEN_BOTTOMSHEET,
    purpose = "수집 항목 활용 맞춤형 상품 추천, 서비스 추천 등의 안내",
    items = "성별, 출생년도, 자녀유무, 피부타입, 피부고민",
    period = "회원 탈퇴 및 동의 철회 시까지",
    description = "회원은 본 서비스 이용 동의에 대한 거부를 할 수 있으며, 미 동의 시 서비스 혜택을 받으실 수 없습니다.",
)

@Preview(showBackground = true)
@Composable
private fun PrivacyPolicyBottomSheetPreview() {
    KurlyTheme {
        PrivacyPolicyBottomSheet(
            model = dummyModel,
            isExpired = false,
            onAgree = {},
            onDisagree = {},
        )
    }
}

@Preview(showBackground = true)
@Composable
private fun PrivacyPolicyBottomSheetExpiredPreview() {
    KurlyTheme {
        PrivacyPolicyBottomSheet(
            model = dummyModel,
            isExpired = true,
            onAgree = {},
            onDisagree = {},
        )
    }
}
```

**Step 3: Android Studio Preview로 시각 확인**

- 일반 상태: NEW 뱃지 없음
- isExpired = true: 타이틀 옆 NEW 뱃지 표시

> **주의:** `KurlyBoxButtonStyle.Secondary`가 실제 KPDS에 존재하지 않을 수 있음. 빌드 오류 시 기존 코드베이스에서 outline/secondary 버튼 사용 패턴을 확인할 것 (`Grep "KurlyBoxButton" --include="*.kt"`).

**Step 4: 커밋**

```bash
git add features/src/main/java/com/kurly/features/mykurlystyle/term/compose/PrivacyPolicyBottomSheet.kt
git commit -m "KMA-7312 PrivacyPolicyBottomSheet Compose 구현"
```

---

## Task 2: ExpiredCancelBottomSheet (KMA-7313)

**레퍼런스:** `ProfileRequiredTermExpiredFragment` + `fragment_bottom_sheet_profile_required_terms_expired.xml`

**UI 구조:**
- 타이틀: `@string/terms_privacy_disagree_popup_title` ("개인정보 수집·이용 동의 만료")
- 본문: 일반 텍스트 + **빨간색 강조** ("기존 정보는 모두 삭제 ")
- 하단: 취소(outline) | 확인(filled purple) 버튼 2개
- isCancelable = false

**Files:**
- Create: `features/src/main/java/com/kurly/features/mykurlystyle/term/compose/ExpiredCancelBottomSheet.kt`

---

**Step 1: 파일 생성**

```kotlin
package com.kurly.features.mykurlystyle.term.compose

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.colorResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.kurly.features.R
import com.kurly.kpds.compose.component.button.boxbutton.KurlyBoxButton
import com.kurly.kpds.compose.component.button.boxbutton.KurlyBoxButtonStyle
import com.kurly.kpds.compose.foundation.ColorTokens
import com.kurly.kpds.compose.foundation.KurlyTheme

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ExpiredCancelBottomSheet(
    onConfirm: () -> Unit,
    onCancel: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)

    // isCancelable = false
    BackHandler {}

    ModalBottomSheet(
        onDismissRequest = {},
        sheetState = sheetState,
        modifier = modifier,
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .navigationBarsPadding(),
        ) {
            // 타이틀
            Text(
                text = stringResource(R.string.terms_privacy_disagree_popup_title),
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold,
                color = ColorTokens.Gray800.toColor(),
                modifier = Modifier
                    .padding(horizontal = 20.dp)
                    .padding(top = 32.dp, bottom = 4.dp),
            )

            // 본문 (빨간색 강조)
            val invalidRed = colorResource(R.color.invalidRed_new)
            Text(
                text = buildAnnotatedString {
                    append("미동의 시 이용이 어려우며, 기존 동의를 철회하는 경우 서비스 제공은 즉시 중단되고 ")
                    withStyle(SpanStyle(color = invalidRed)) {
                        append("기존 정보는 모두 삭제 ")
                    }
                    append("됩니다.")
                },
                fontSize = 14.sp,
                color = ColorTokens.Gray600.toColor(),
                modifier = Modifier
                    .padding(horizontal = 20.dp)
                    .padding(top = 16.dp),
            )

            // 버튼 영역
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 12.dp)
                    .padding(top = 24.dp, bottom = 8.dp),
            ) {
                KurlyBoxButton(
                    text = stringResource(R.string.terms_privacy_disagree_popup_btn_cancel),
                    onClick = onCancel,
                    style = KurlyBoxButtonStyle.Secondary,
                    modifier = Modifier.weight(1f),
                )
                KurlyTheme.spacers.width8()
                KurlyBoxButton(
                    text = stringResource(R.string.terms_privacy_disagree_popup_btn_check),
                    onClick = onConfirm,
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }
}
```

**Step 2: Preview 추가**

```kotlin
// ─── Previews ──────────────────────────────────────────────────────────────

@Preview(showBackground = true)
@Composable
private fun ExpiredCancelBottomSheetPreview() {
    KurlyTheme {
        ExpiredCancelBottomSheet(
            onConfirm = {},
            onCancel = {},
        )
    }
}
```

**Step 3: Preview 확인**

- 타이틀 정상 표시
- "기존 정보는 모두 삭제 " 텍스트가 빨간색으로 표시되는지 확인

**Step 4: 커밋**

```bash
git add features/src/main/java/com/kurly/features/mykurlystyle/term/compose/ExpiredCancelBottomSheet.kt
git commit -m "KMA-7313 ExpiredCancelBottomSheet Compose 구현"
```

---

## Task 3: PrivacyPolicyTableDialog (KMA-7314)

**레퍼런스:** `ProfileRequiredTermDialog` + `fragment_dialog_profile_required_term.xml`

**UI 구조:**
- 타이틀: "프로필 수집 및 이용 약관 동의 (필수)" (18sp bold)
- 3열 테이블: 수집 목적 | 수집 항목 | 보유 기간 (헤더 회색 배경 + 데이터 행 흰색)
  - 테이블 외곽: lightGray 배경으로 테두리 효과 (0.5dp gap)
- description 텍스트
- "동의" 버튼 하나
- 내용이 길 경우 스크롤 가능
- 모서리 radius: 12dp

**Files:**
- Create: `features/src/main/java/com/kurly/features/mykurlystyle/term/compose/PrivacyPolicyTableDialog.kt`

---

**Step 1: 파일 생성**

```kotlin
package com.kurly.features.mykurlystyle.term.compose

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.kurly.features.R
import com.kurly.features.mykurlystyle.kurlystyle.PrivacyPolicyAction
import com.kurly.features.mykurlystyle.term.model.PrivacyPolicyUIModel
import com.kurly.kpds.compose.component.button.boxbutton.KurlyBoxButton
import com.kurly.kpds.compose.foundation.ColorTokens
import com.kurly.kpds.compose.foundation.KurlyTheme

@Composable
fun PrivacyPolicyTableDialog(
    model: PrivacyPolicyUIModel,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        shape = RoundedCornerShape(12.dp),
        title = {
            Text(
                text = "프로필 수집 및 이용 약관 동의 (필수)",
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold,
                color = ColorTokens.Gray800.toColor(),
            )
        },
        text = {
            Column(
                modifier = Modifier.verticalScroll(rememberScrollState()),
            ) {
                PrivacyPolicyTable(model = model)
                KurlyTheme.spacers.height16()
                Text(
                    text = model.description,
                    fontSize = 14.sp,
                    color = ColorTokens.Gray600.toColor(),
                )
            }
        },
        confirmButton = {
            KurlyBoxButton(
                text = stringResource(R.string.profile_terms_use_popup_btn_agree),
                onClick = onDismiss,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 12.dp)
                    .padding(bottom = 8.dp),
            )
        },
        modifier = modifier,
    )
}

@Composable
private fun PrivacyPolicyTable(
    model: PrivacyPolicyUIModel,
    modifier: Modifier = Modifier,
) {
    // lightGray 배경으로 0.5dp 테두리 효과
    val borderColor = ColorTokens.Gray200.toColor()
    val headerBg = ColorTokens.Gray100.toColor()

    Column(
        modifier = modifier
            .fillMaxWidth()
            .background(borderColor),
    ) {
        // 헤더 행
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 0.5.dp, start = 0.5.dp, end = 0.5.dp),
        ) {
            TableCell(
                text = "수집 목적",
                isHeader = true,
                background = headerBg,
                modifier = Modifier.weight(1f),
            )
            TableCell(
                text = "수집 항목",
                isHeader = true,
                background = headerBg,
                modifier = Modifier
                    .weight(1f)
                    .padding(horizontal = 0.5.dp),
            )
            TableCell(
                text = "보유 기간",
                isHeader = true,
                background = headerBg,
                modifier = Modifier.weight(1f),
            )
        }
        // 데이터 행
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .height(IntrinsicSize.Min)
                .padding(bottom = 0.5.dp, start = 0.5.dp, end = 0.5.dp),
        ) {
            TableCell(
                text = model.purpose,
                isHeader = false,
                background = Color.White,
                modifier = Modifier
                    .weight(1f)
                    .fillMaxHeight(),
            )
            TableCell(
                text = model.items,
                isHeader = false,
                background = Color.White,
                modifier = Modifier
                    .weight(1f)
                    .fillMaxHeight()
                    .padding(horizontal = 0.5.dp),
            )
            TableCell(
                text = model.period,
                isHeader = false,
                background = Color.White,
                modifier = Modifier
                    .weight(1f)
                    .fillMaxHeight(),
            )
        }
    }
}

@Composable
private fun TableCell(
    text: String,
    isHeader: Boolean,
    background: Color,
    modifier: Modifier = Modifier,
) {
    Text(
        text = text,
        fontSize = if (isHeader) 14.sp else 12.sp,
        fontWeight = if (isHeader) FontWeight.Bold else FontWeight.Normal,
        color = ColorTokens.Gray800.toColor(),
        textAlign = TextAlign.Center,
        modifier = modifier
            .background(background)
            .padding(horizontal = 10.dp, vertical = if (isHeader) 10.dp else 18.dp),
    )
}
```

**Step 2: Preview 추가**

```kotlin
// ─── Previews ──────────────────────────────────────────────────────────────

private val dummyDialogModel = PrivacyPolicyUIModel(
    action = PrivacyPolicyAction.OPEN_DIALOG,
    purpose = "수집 항목 활용 맞춤형 상품 추천, 서비스 추천 등의 안내 및 이를 기반으로 마케팅 활동",
    items = "성별, 출생년도, 자녀유무, 피부타입, 피부고민, 피부톤, 관심키워드",
    period = "회원 탈퇴 및 동의 철회 시까지",
    description = "회원은 본 서비스 이용 동의에 대한 거부를 할 수 있으며, 미 동의 시 본 서비스에 대한 혜택을 받으실 수 없습니다.",
)

@Preview(showBackground = true)
@Composable
private fun PrivacyPolicyTableDialogPreview() {
    KurlyTheme {
        PrivacyPolicyTableDialog(
            model = dummyDialogModel,
            onDismiss = {},
        )
    }
}
```

**Step 3: Preview 확인**

- 타이틀 표시
- 3열 테이블: 헤더 회색 배경, 데이터 흰색 배경, gray 테두리 효과
- description 텍스트
- "동의" 버튼 하단

> **주의:** `ColorTokens.Gray200`이 lightGray에 정확히 대응하지 않을 수 있음. 시각적으로 맞지 않으면 `colorResource(R.color.lightGray)`로 교체할 것.

**Step 4: 커밋**

```bash
git add features/src/main/java/com/kurly/features/mykurlystyle/term/compose/PrivacyPolicyTableDialog.kt
git commit -m "KMA-7314 PrivacyPolicyTableDialog Compose 구현"
```

---

## 완료 조건

- [ ] `PrivacyPolicyBottomSheet`: isExpired true/false Preview 2개 모두 Fragment 레이아웃과 시각적으로 일치
- [ ] `ExpiredCancelBottomSheet`: "기존 정보는 모두 삭제 " 빨간색 강조 확인
- [ ] `PrivacyPolicyTableDialog`: 3열 테이블 레이아웃이 Fragment XML과 일치
- [ ] 빌드 오류 없음 (`./gradlew :features:compileDebugKotlin`)

## Phase 2 사전 확인

Phase 1 완료 후 Phase 2(ViewModel + Activity 리팩토링) 전에:
- 각 Composable 콜백 시그니처가 설계 문서(`2026-03-06-mykurlystyle-compose-event-flow-design.md`)의 ModalHost 연결 방식과 일치하는지 확인
- Fragment 파일은 Phase 2까지 유지 (아직 삭제하지 않음)
