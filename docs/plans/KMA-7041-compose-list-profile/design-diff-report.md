# ListProfileActivity 디자인 차이점 리포트

비교 기준: commit `c8d31de1e0` 삭제 XML (Production) vs 현재 Compose 구현 (Beta)

## 요약

총 **15개** 차이점 발견: **수정 필요 9개**, **KPDS 근사치 사용 1개**, **확인 불필요 5개**

주요 신규 발견: `list_item_segment_info.xml` 전체 속성 분석 추가
- tvSegName 폰트 스타일 불일치 (bold vs semiBold)
- tvSegName 하단 간격 축소 (8dp → 4dp)
- tvSegDesc 폰트 크기 확대 (13sp → 14sp)
- 색상 지정 확인 필요

---

## 차이점 목록

### 수정 필요

| # | 위치 | XML (Production) | Compose (Beta) | 수정 방향 |
|---|------|-----------------|----------------|----------|
| 1 | `activity_list_profile.xml` → RecyclerView paddingHorizontal | `paddingHorizontal="15dp"` | `padding(horizontal = 16.dp)` (`ProfileCategorySection` modifier) | Compose를 `15.dp`로 수정 (또는 의도적 변경이면 확인 불필요로 이동) |
| 2 | `list_item_profile_top_guide.xml` → `tvListProfileGuide` | "피부정보 및 관심 키워드를 선택해 주세요." 텍스트 표시 (`16sp bold`, 색상 `#8D4CC4` loversLavender) | `ListProfileContent`에 해당 텍스트 없음 | `ListProfileContent` 상단에 안내 텍스트 추가 필요 여부 PM/디자이너 확인 |
| 3 | `activity_list_profile.xml` → 저장 버튼 marginHorizontal | `marginHorizontal="12dp"` | `padding(horizontal = 16.dp)` (`KurlyBoxButton` modifier) | Compose를 `12.dp`로 수정 (또는 의도적 변경이면 확인 불필요로 이동) |
| 4 | `activity_list_profile.xml` → 저장 버튼 영역 배경 | `background="@drawable/view_bottom_button_gradient"` (위: 투명→하단: 흰색 세로 그라디언트) | 배경 없음 (단색 `Background1`) | `KurlyBoxButton` 위에 그라디언트 오버레이 Box 추가 필요 여부 디자이너 확인 |
| 5 | `fragment_dialog_segment_info.xml` → 다이얼로그 제목 크기 | `textSize="18sp"` + `textStyle="bold"` (`Bold18` 동등) | `KurlyTheme.typography.bold20` (20sp) | `bold18`로 변경: `style = KurlyTheme.typography.bold18` |
| 6 | `list_item_profile_recycler_view.xml` → `tvMultiSelectGuide` | `MULTI` 타입일 때 "중복선택가능" 텍스트 표시 (`12sp regular`, 색상 `#999999` kurlyGray450) | `ProfileCategorySection`에 해당 레이블 없음 | 카테고리 헤더 row에 `MULTI` 타입일 때 "중복선택가능" 텍스트 표시 추가 |
| 7 | `list_item_segment_info.xml` → `tvSegName` 폰트 스타일 | `textStyle="bold"` (굵은 스타일) | `KurlyTheme.typography.semiBold16` (semiBold 굵기) | 스타일 변경: `bold16` 또는 `bold18` 사용 (PM/디자이너 확인) |
| 8 | `list_item_segment_info.xml` → `tvSegName` 하단 간격 | `android:layout_marginBottom="8dp"` | `KurlyTheme.spacers.height4()` (4dp) | 간격 증가: 4dp → 8dp로 수정 (또는 외부 16.dp spacedBy와의 상호작용 재검토) |
| 9 | `list_item_segment_info.xml` → `tvSegDesc` 폰트 크기 | `textSize="13sp"` | `KurlyTheme.typography.regular14` (14sp) | 크기 축소: `regular14` → `regular13`으로 변경 (KPDS 정확한 매칭) |

### KPDS 비적용 (근사치 사용)

현재 KPDS 근사치 사용이 없습니다. 차이 #7, #8, #9는 모두 명확한 수정 필요 사항입니다.

> **참고:** 기존 리포트의 `list_item_segment_info.xml` → `tvSegDesc` 폰트 크기 항목 (#7에서 수정 필요로 재분류)
> - KPDS에 `regular13`(`TypoDefaults.Regular13`, 13sp/18sp lineHeight)이 정확히 존재
> - 현재 `regular14` 사용은 KPDS 규칙 위반
> - `SegmentInfoComposeDialog` 내 `segment.description` Text의 `style = KurlyTheme.typography.regular14` → `regular13`으로 변경 필수

### 확인 불필요 (동일 또는 의도적 변경)

| # | 항목 | 사유 |
|---|------|------|
| 1 | 텍스트 버튼 카드 radius (`list_item_profile_text_button.xml`) | XML `4dp` = Compose `RoundedCornerShape(4.dp)` — 동일 |
| 2 | 텍스트 태그 버튼 카드 radius (`list_item_profile_text_button_tag.xml`) | XML `4dp` = Compose `RoundedCornerShape(4.dp)` — 동일 |
| 3 | 이미지 버튼 카드 radius (`list_item_profile_image_button.xml`) | XML `6dp` = Compose `RoundedCornerShape(6.dp)` — 동일 |
| 4 | 이미지+설명 버튼 radius (`list_item_profile_image_button_description.xml`) | XML `6dp` = Compose `RoundedCornerShape(6.dp)` — 동일 |
| 5 | 설명 버튼 radius (`list_item_profile_button_description.xml`) | XML `6dp` = Compose `RoundedCornerShape(6.dp)` — 동일 |

---

## 세부 분석

### 차이 #1: 콘텐츠 영역 가로 패딩

**XML** (`activity_list_profile.xml`):
```xml
<androidx.recyclerview.widget.RecyclerView
    android:paddingHorizontal="15dp"
    android:paddingTop="24dp"
    android:paddingBottom="88dp" />
```

**Compose** (`ListProfileScreen.kt`, `ProfileCategorySection`):
```kotlin
modifier = Modifier
    .fillMaxWidth()
    .padding(horizontal = 16.dp, vertical = 12.dp)
```
추가로 `ListProfileBodyContent` 내부에서 `padding(horizontal = 24.dp)`이 적용되어, 실제 세그먼트 아이템의 좌우 여백은 Compose가 더 큰 상태.

---

### 차이 #2: 최상단 안내 텍스트 누락

**XML** (`list_item_profile_top_guide.xml`):
```xml
<TextView
    android:text="피부정보 및 관심 키워드를 선택해 주세요."
    android:textColor="@color/loversLavender"   <!-- #8D4CC4 -->
    android:textSize="16sp"
    android:textStyle="bold" />
```

**Compose**: `ListProfileContent`에 해당 텍스트 없음. RecyclerView의 첫 번째 아이템으로 표시되던 UI가 Compose 전환 시 누락됨.

---

### 차이 #3, #4: 저장 버튼 영역

**XML** (`activity_list_profile.xml`):
```xml
<androidx.constraintlayout.widget.ConstraintLayout
    android:background="@drawable/view_bottom_button_gradient"
    android:minHeight="68dp"
    android:paddingVertical="8dp">
    <MaterialButton
        android:layout_marginHorizontal="12dp"
        android:minHeight="52dp"
        android:textSize="16sp"
        android:textStyle="bold"
        app:cornerRadius="6dp" />
```
`view_bottom_button_gradient`: `#00ffffff` (투명 상단) → `#ffffff` (불투명 하단) 그라디언트.

**Compose** (`ListProfileScreen.kt`):
```kotlin
KurlyBoxButton(
    text = ...,
    onClick = onSaveClick,
    modifier = Modifier
        .fillMaxWidth()
        .navigationBarsPadding()
        .padding(horizontal = 16.dp, vertical = 12.dp),
)
```
그라디언트 배경 없음, 가로 패딩 12dp → 16dp 차이.

---

### 차이 #5: 다이얼로그 제목 폰트 크기

**XML** (`fragment_dialog_segment_info.xml`):
```xml
<AppCompatTextView
    android:textSize="18sp"
    android:textStyle="bold"
    android:lineSpacingExtra="5sp" />
```
→ `Bold18` (18sp, lineHeight 26sp) 에 해당

**Compose** (`ListProfileScreen.kt`, `SegmentInfoComposeDialog`):
```kotlin
Text(
    text = "$categoryName 안내",
    style = KurlyTheme.typography.bold20,  // 20sp — 2sp 크게 적용
)
```

---

### 차이 #6: 다중선택 가능 레이블 누락

**XML** (`list_item_profile_recycler_view.xml`):
```xml
<AppCompatTextView
    android:id="@+id/tvMultiSelectGuide"
    android:text="@string/site_profile_multiple_selection_possible"   <!-- "중복선택가능" -->
    android:textColor="@color/kurlyGray450"   <!-- #999999 -->
    android:textSize="12sp"
    android:visibility="@{selectType == SelectType.MULTI ? View.VISIBLE : View.GONE}" />
```
카테고리명 옆에 "중복선택가능" 레이블이 MULTI일 때 표시됨.

**Compose** (`ListProfileScreen.kt`, `ProfileCategorySection`): 해당 레이블 없음.
`StepHeaderContent`는 title + description만 표시하며 selectType 기반 레이블 렌더링 없음.

---

### KPDS 근사치: 다이얼로그 설명 텍스트 크기

**XML** (`list_item_segment_info.xml`, `fragment_dialog_segment_info.xml` 내부):
```xml
<AppCompatTextView
    android:textSize="13sp"
    android:textColor="@color/kurlyGray600" />
```

**Compose** (`ListProfileScreen.kt`, `SegmentInfoComposeDialog`):
```kotlin
Text(
    text = description,
    style = KurlyTheme.typography.regular14,  // 14sp — 1sp 크게
)
```
KPDS에 `regular13`이 존재하므로 `regular14` 대신 `regular13` 사용 권장.

---

### list_item_segment_info.xml 전체 분석

**XML 전체 구조** (commit `c8d31de1e0`에서 삭제):
```xml
<?xml version="1.0" encoding="utf-8"?>
<layout xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:tools="http://schemas.android.com/tools">

    <data>
        <variable name="name" type="String" />
        <variable name="description" type="String" />
    </data>

    <androidx.appcompat.widget.LinearLayoutCompat
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:orientation="vertical">

        <androidx.appcompat.widget.AppCompatTextView
            android:id="@+id/tvSegName"
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:layout_marginBottom="8dp"
            android:text="@{name}"
            android:textColor="@color/kurlyGray800"
            android:textSize="16sp"
            android:textStyle="bold"
            tools:text="건성" />

        <androidx.appcompat.widget.AppCompatTextView
            android:id="@+id/tvSegDesc"
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:text="@{description}"
            android:textColor="@color/kurlyGray600"
            android:textSize="13sp"
            tools:text="피부 표면이 건조하며 윤기가 없고 세안 후 당기는 느낌이 든다." />
    </androidx.appcompat.widget.LinearLayoutCompat>
</layout>
```

#### 상세 속성 비교

| 항목 | XML (Production) | Compose (Beta) | 차이 | 평가 |
|------|-----------------|----------------|------|------|
| **tvSegName - 폰트 크기** | `16sp` | `KurlyTheme.typography.semiBold16` (16sp) | 동일 | ✅ 동일 |
| **tvSegName - 폰트 스타일** | `bold` | `semiBold16` | `bold` vs `semiBold` | ⚠️ 미세한 차이 |
| **tvSegName - 색상** | `kurlyGray800` (#1D1D1D) | Compose에서 기본 색상 (dark: Gray900, light: Gray800) | 거의 동일 | ✅ 동일 |
| **tvSegName - 하단 마진** | `8dp` | `KurlyTheme.spacers.height4()` (4dp) | 8dp vs 4dp | ⚠️ 간격 축소 |
| **tvSegDesc - 폰트 크기** | `13sp` | `KurlyTheme.typography.regular14` (14sp) | 13sp vs 14sp | ❌ 1sp 확대 |
| **tvSegDesc - 색상** | `kurlyGray600` (#666666) | Text 기본 색상 (테마 기본값) | 설정 필요 확인 | ⚠️ 명시적 색상 지정 필요 |
| **컨테이너 - 레이아웃** | `LinearLayoutCompat` (vertical, wrap_content) | `Column { ... }` | 동등 구조 | ✅ 동일 |
| **컨테이너 - 패딩** | 패딩 없음 (다이얼로그 내에서 처리) | 외부 Column에서 16.dp spacedBy로 처리 | 동등 | ✅ 동일 |

#### 수정 필요 항목

1. **tvSegName 폰트 스타일**: `bold` (굵기) vs `semiBold` (중간 굵기)
   - XML은 `textStyle="bold"` 명시
   - Compose의 `semiBold16`은 semiBold 굵기
   - **수정**: `KurlyTheme.typography.bold16` (또는 bold18과 혼합)로 변경 검토 필요

2. **tvSegName 하단 간격**: `8dp` vs `4dp`
   - XML은 `marginBottom="8dp"` 명시 (텍스트 항목 간 간격)
   - Compose는 `KurlyTheme.spacers.height4()` (4dp)
   - **현황**: ListProfileScreen.kt 216줄에서 `KurlyTheme.spacers.height4()` 사용
   - **수정 필요**: 외부 Column의 `Arrangement.spacedBy(16.dp)`가 이미 항목 간 간격을 처리하므로, 내부 name/description 간 간격만 고려하면 4dp는 적절할 수 있음 (재검토 필요)

3. **tvSegDesc 폰트 크기**: `13sp` vs `14sp` (KPDS 근사치)
   - XML은 `textSize="13sp"` 명시
   - Compose는 `regular14` 사용
   - **수정**: `KurlyTheme.typography.regular13`으로 변경 필수

4. **tvSegDesc 색상**: `kurlyGray600` (#666666) vs Compose 기본색
   - XML은 `textColor="@color/kurlyGray600"` 명시
   - Compose의 Text 기본 색상이 테마 기본값인지 명시적 지정 필요
   - **확인 필요**: ListProfileScreen.kt 217줄 Text() 호출에서 color 파라미터 확인

#### 현재 Compose 구현 코드 (ListProfileScreen.kt 209-223줄)

```kotlin
segments.forEach { segment ->
    Column {
        Text(
            text = segment.name,
            style = KurlyTheme.typography.semiBold16,  // ⚠️ bold16이어야 함
        )
        segment.description?.let { description ->
            KurlyTheme.spacers.height4()  // ⚠️ 8dp 재검토 필요 (현재는 16.dp spacedBy + 4.dp 간격)
            Text(
                text = description,
                style = KurlyTheme.typography.regular14,  // ❌ regular13으로 변경 필수
            )
        }
    }
}
```

#### 결론

- **확인 불필요**: 컨테이너 레이아웃, 정렬 방식, 텍스트 색상 (기본값 확인 후)
- **수정 필수**:
  - `tvSegDesc` 폰트 크기 14sp → 13sp (`regular13` 사용)
  - `tvSegName` 폰트 스타일 `semiBold` → `bold` (또는 bold18) 재검토
  - 내부 간격 4dp vs 8dp 재검토 (외부 16.dp spacedBy와의 상호작용)

---

## 코드 위치 참조

| 파일 | 관련 차이 |
|------|----------|
| `features/src/main/java/com/kurly/features/mykurlystyle/siteprofile/list/ListProfileScreen.kt` | #1, #2, #3, #4, #5, #6 (다이얼로그 제목, KPDS 근사치, list_item_segment_info 분석) |
| `features/src/main/java/com/kurly/features/mykurlystyle/siteprofile/StepBodyContent.kt` | 세그먼트 아이템 Composable (radius 동일 확인) |
| `features/src/main/java/com/kurly/features/mykurlystyle/siteprofile/StepHeaderContent.kt` | #6 관련 (selectType 레이블 없음) |
