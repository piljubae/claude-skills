# Compose Design Analyzer

## 역할

Compose 마이그레이션 대상 화면의 **before 기준**(origin/develop 코드 또는 Figma)과
현재 feature 브랜치 Compose 코드를 비교하여 모든 시각적 차이를 `design-diff-report.md`에 기록한다.

체크리스트의 **모든 항목을 확인**하기 전까지 report 출력 금지.
"없음"도 반드시 기록한다 — 확인하지 않은 것과 없는 것은 다르다.

---

## 입력

- `Screen`: 분석 대상 Activity/Fragment 클래스명
- `Before 기준`: `develop` | `figma:<url>`
- `Upstream remote`: `origin` 또는 `upstream`
- `작업 폴더`: `docs/plans/<branch>/`

---

## 파일 탐색 전략

### A. git diff 기반 (변경된 파일)

```bash
# feature 브랜치 vs upstream/develop 전체 diff
git diff {UPSTREAM_REMOTE}/develop --name-only

# 삭제된 파일 (구 View 코드)
git diff {UPSTREAM_REMOTE}/develop --diff-filter=D --name-only

# 수정된 파일
git diff {UPSTREAM_REMOTE}/develop --diff-filter=M --name-only
```

### B. 패키지 기반 (Activity명으로 추적)

```bash
# Screen 클래스가 있는 패키지 경로 탐색
PACKAGE_PATH=$(git show {UPSTREAM_REMOTE}/develop --name-only | grep "{SCREEN_NAME}" | head -1 | xargs dirname)

# 해당 패키지 전체 파일 목록
git show {UPSTREAM_REMOTE}/develop --name-only | grep "${PACKAGE_PATH}"
```

**최종 탐색 대상 = A ∪ B (합집합)**

---

## 필수 체크리스트

아래 7개 항목을 **순서대로** 모두 확인한다.
각 항목은 "확인 완료 ✅" 또는 "해당 없음 ✅ (이유)"로 표시해야 한다.

---

### □ 체크 1: 레이아웃 XML

```bash
# upstream/develop에서 관련 XML 파일 읽기
git show {UPSTREAM_REMOTE}/develop -- features/src/main/res/layout/activity_{screen}.xml
git show {UPSTREAM_REMOTE}/develop -- features/src/main/res/layout/fragment_{screen}.xml
git show {UPSTREAM_REMOTE}/develop -- features/src/main/res/layout/list_item_*.xml
```

**추출 항목:**
- `android:padding*`, `android:layout_margin*` → 모든 dp 값
- `android:minHeight`, `android:maxHeight`
- `android:textSize`, `android:textStyle`, `android:textColor`
- `app:cardCornerRadius`, `app:cornerRadius`
- `android:background` (drawable 참조 포함)
- `android:layout_width/height` 고정값
- RecyclerView: `android:paddingHorizontal`, `android:paddingTop`, `android:paddingBottom`, `android:clipToPadding`

---

### □ 체크 2: ItemDecoration 클래스 (필수 — 섹션 간 spacing)

```bash
# *Decorator.kt 파일 강제 탐색 (없어도 "없음" 기록)
git show {UPSTREAM_REMOTE}/develop --name-only | grep -iE "Decorator|ItemDecoration"

# 존재하면 내용 읽기
git show {UPSTREAM_REMOTE}/develop -- path/to/XxxDecorator.kt
```

**추출 항목:**
- `outRect.top`, `outRect.bottom`, `outRect.left`, `outRect.right` 값
- `position` 조건별 분기 (첫 번째 아이템 vs 나머지)

---

### □ 체크 3: Adapter / ViewHolder

```bash
# *Adapter.kt, *ViewHolder.kt 강제 탐색
git show {UPSTREAM_REMOTE}/develop --name-only | grep -iE "Adapter|ViewHolder"

# 존재하면 내용 읽기
git show {UPSTREAM_REMOTE}/develop -- path/to/XxxAdapter.kt
```

**추출 항목:**
- 동적 visibility 변경 (`View.VISIBLE`, `View.GONE`)
- 프로그래매틱 size 조정 (`layoutParams.height = ...`)
- `spanCount`, FlexboxLayoutManager 설정

---

### □ 체크 4: Activity / Fragment 코드

```bash
git show {UPSTREAM_REMOTE}/develop -- path/to/XxxActivity.kt
git show {UPSTREAM_REMOTE}/develop -- path/to/XxxFragment.kt
```

**추출 항목:**
- `addItemDecoration(...)` 호출 및 파라미터
- RecyclerView `setLayoutManager(...)` 설정
- 프로그래매틱 padding/margin 설정
- `setAdapter(...)` 시 전달하는 설정값

---

### □ 체크 5: styles.xml / 공통 스타일

```bash
git show {UPSTREAM_REMOTE}/develop -- features/src/main/res/values/styles.xml
```

레이아웃 XML에서 참조된 `style="@style/..."` 값 추출.
**추출 항목:** `textSize`, `textStyle`, `textColor`, `background`

---

### □ 체크 6: drawable 파일

레이아웃 XML에서 참조된 `@drawable/...` 파일 읽기.

```bash
git show {UPSTREAM_REMOTE}/develop -- features/src/main/res/drawable/xxx.xml
```

**추출 항목:**
- gradient (colors, angle)
- shape (corners radius, stroke width/color)
- layer-list (복합 배경)

---

### □ 체크 7: 컬러 토큰 매핑

```bash
git show {UPSTREAM_REMOTE}/develop -- features/src/main/res/values/colors.xml
# 또는 공통 colors.xml
git show {UPSTREAM_REMOTE}/develop -- core/src/main/res/values/colors.xml
```

레이아웃/스타일에서 사용된 `@color/xxx` 값을 추출하고,
현재 Compose에서 사용 중인 KPDS 토큰과 매핑이 올바른지 확인.

예시:
```
@color/kurlyGray800 → TextColorTokens.Primary ✅
@color/loversLavender → MainColorTokens.Primary ✅
@color/kurlyGray450 → TextColorTokens.Tertiary ✅ (확인 필요)
```

---

## Figma before 처리 (before=figma인 경우)

위 7개 체크 대신 Figma MCP를 사용한다.

```
get_design_context(fileKey, nodeId)
```

추출 항목:
- spacing, padding 값
- typography (size, weight, color token)
- border radius
- background color / gradient

결과를 동일한 report 포맷으로 변환.

---

## 현재 Compose 코드 분석

체크리스트 완료 후, 현재 feature 브랜치의 Compose 파일을 읽어 before 값과 비교한다.

```bash
# 현재 Compose 파일 목록
git diff {UPSTREAM_REMOTE}/develop --diff-filter=A --name-only | grep "\.kt$"
# 또는 직접 Read tool로 읽기
```

---

## 출력: design-diff-report.md

`{WORK_DIR}/design-diff-report.md`에 저장.

```markdown
# Design Diff Report — {SCREEN_NAME}
생성일: {date}
Before 기준: {BEFORE_MODE}

## 체크리스트 완료 현황
- [x] 레이아웃 XML
- [x] ItemDecoration (ProfileCategoryDecorator.kt 발견)
- [x] Adapter/ViewHolder
- [x] Activity/Fragment
- [x] styles.xml
- [x] drawable
- [x] 컬러 토큰 매핑

## 수정 필요 항목

| # | 위치 | 항목 | Before 값 | Compose 현재 | 수정 방법 |
|---|------|------|-----------|-------------|---------|
| 1 | ProfileCategorySection | 섹션 간 spacing | 35dp (Decorator) | 4dp | padding(top=35.dp) |
| 2 | SegmentTextButtonItem | 최소 높이 | minHeight=50dp | 없음 | heightIn(min=50.dp) |

## KPDS 근사치 항목

| 항목 | Before 값 | 적용 값 | 사유 |
|------|-----------|---------|------|
| description textSize | 13sp | regular13 | KPDS에 13sp 없음 |

## 확인 불필요 항목

| 항목 | 사유 |
|------|------|
| RecyclerView overScrollMode | Compose 기본값과 동일 |
```

---

## 주의사항

- dp 값은 반드시 **실제 수치**로 기록 (예: "크다/작다" 표현 금지)
- KPDS 토큰이 있으면 토큰명으로, 없으면 raw dp/sp 값으로 기록
- 파일이 없는 항목은 "해당 없음" + 탐색 명령 결과를 근거로 기록
- 같은 수치라도 **구조적 차이**(예: padding vs margin)는 별도 항목으로 기록
