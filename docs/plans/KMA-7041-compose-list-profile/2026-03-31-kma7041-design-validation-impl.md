# KMA-7041 ListProfileActivity 디자인 검증 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Production(View 기반) vs Beta(Compose 전환) ListProfileActivity 화면을 비교해 시각적 차이를 찾고 Compose 코드를 수정한다.

**Architecture:** Phase 1(병렬 분석) → Phase 2(Before 스크린샷) → Phase 3(코드 수정) → Phase 4(After 스크린샷). Code Analyzer와 Script Writer가 병렬로 실행되고, Fix Applier가 두 결과를 합산해 수정한다.

**Tech Stack:** Kotlin/Compose, Python uiautomator2, ADB, Pillow

---

## 사전 준비

```bash
# Python 의존성 설치 (없으면)
pip3 install uiautomator2 Pillow

# ADB 기기 확인 (실기기: R3CT10A3JCE 사용)
adb devices
# 출력 예: R3CT10A3JCE  device

# 두 앱 모두 로그인 상태인지 수동 확인
# - com.dbs.kurly.m2 (production)
# - com.dbs.kurly.m2.beta (beta)
```

---

## Task 1: Code Analyzer — 스타일 차이 리포트 생성

**목적:** git 히스토리의 원본 XML과 현재 Compose 코드를 비교해 차이점 문서화

**Files:**
- Read (git history): 삭제된 XML들은 commit `c8d31de1e0`의 diff에 있음
- Read: `features/src/main/java/com/kurly/features/mykurlystyle/siteprofile/list/ListProfileScreen.kt`
- Read: `features/src/main/java/com/kurly/features/mykurlystyle/siteprofile/StepBodyContent.kt`
- Create: `docs/plans/design-diff-report.md`

**Step 1: 원본 XML 데이터 수집**

이미 분석된 내용 (추가 확인 필요한 것들):

```bash
# 삭제된 XML 전체 diff 확인
git show c8d31de1e0 -- features/src/main/res/layout/list_item_profile_image_button_description.xml
git show c8d31de1e0 -- features/src/main/res/layout/list_item_profile_recycler_view.xml

# StepBodyContent의 세그먼트 아이템 Compose 스타일 확인
# SegmentTextButtonItem, SegmentTagButtonItem, SegmentImageButtonItem, SegmentDescriptionItem
grep -r "fun Segment" features/src/main/java/com/kurly/features/mykurlystyle/siteprofile/
```

**Step 2: 이미 파악된 주요 차이점**

| # | 항목 | XML (Production) | Compose (Beta) | 상태 |
|---|------|-----------------|----------------|------|
| 1 | RecyclerView 가로 padding | `paddingHorizontal="15dp"` | `padding(horizontal=16.dp)` per category | 수정 필요 |
| 2 | Top guide 텍스트 | "피부정보 및 관심 키워드를 선택해 주세요." (`list_item_profile_top_guide.xml`) | **없음** | 누락 여부 확인 |
| 3 | 저장 버튼 가로 margin | `marginHorizontal="12dp"` | `padding(horizontal=16.dp)` | 수정 필요 |
| 4 | 저장 버튼 배경 | `view_bottom_button_gradient` (gradient drawable) | 없음 (흰 배경) | 확인 필요 |
| 5 | 텍스트 버튼 카드 radius | `cardCornerRadius="4dp"` | SegmentTextButtonItem 확인 필요 | 확인 필요 |
| 6 | 이미지 버튼 카드 radius | `cardCornerRadius="6dp"` | SegmentImageButtonItem 확인 필요 | 확인 필요 |
| 7 | 다이얼로그 제목 크기 | `textSize="18sp"` + `kurlyGray800` | `KurlyTheme.typography.bold20` | 수정 필요 |
| 8 | Segment info 설명 텍스트 | `textSize="13sp"` | `KurlyTheme.typography.regular14` | 수정 필요 |
| 9 | KPDS 비적용 값 목록 | - | - | 별도 문서화 |

**Step 3: 차이점 리포트 저장**

```bash
# docs/plans/design-diff-report.md 에 위 표 + 추가 발견 항목 저장
```

---

## Task 2: Script Writer — uiautomator2 탐색 스크립트 작성

**목적:** 두 앱에서 ListProfileActivity까지 자동 탐색 후 스크린샷 캡처

**Files:**
- Create: `scripts/capture_list_profile.py`
- Create: `scripts/README.md` (사용법)

**Step 1: 의존성 설치 확인**

```bash
pip3 install uiautomator2 Pillow
python3 -m uiautomator2 init  # ATX agent 설치 (처음만)
```

**Step 2: 스크립트 작성** (`scripts/capture_list_profile.py`)

```python
#!/usr/bin/env python3
"""
ListProfileActivity 스크린샷 캡처 스크립트
Usage:
  python3 capture_list_profile.py production   # production 앱만
  python3 capture_list_profile.py beta         # beta 앱만
  python3 capture_list_profile.py both         # 둘 다 (기본값)
  python3 capture_list_profile.py after        # after_beta.png 저장
"""

import sys
import time
import uiautomator2 as u2
from pathlib import Path
from PIL import Image

DEVICE_SERIAL = "R3CT10A3JCE"
OUTPUT_DIR = Path(__file__).parent.parent / "docs" / "screenshot"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PACKAGES = {
    "production": "com.dbs.kurly.m2",
    "beta": "com.dbs.kurly.m2.beta",
}

def connect_device():
    d = u2.connect(DEVICE_SERIAL)
    print(f"Connected: {d.info['productName']}")
    return d

def navigate_to_list_profile(d, package_name: str):
    """마이컬리 탭 → 커뮤니티&스타일 → 프로필 클릭"""
    print(f"[{package_name}] 앱 실행...")
    d.app_start(package_name)
    time.sleep(3)

    # 마이컬리 탭 클릭
    print("  마이컬리 탭...")
    d(description="마이컬리").click()
    time.sleep(2)

    # 커뮤니티&스타일 / 코드웨이터브 네비 탐색
    # uiautomator dump로 실제 텍스트 확인 필요
    # 아래는 탐색 시도 순서 (앱 버전에 따라 조정 필요)
    for text in ["커뮤니티&스타일", "스타일", "코드웨이터브"]:
        try:
            d(textContains=text).click()
            time.sleep(2)
            break
        except Exception:
            continue

    # 프로필 수정 버튼 (재진입 = ListProfileActivity)
    for text in ["프로필 수정", "프로필 편집", "수정"]:
        try:
            d(textContains=text).click()
            time.sleep(3)
            break
        except Exception:
            continue

    print(f"  현재 Activity: {d.app_current()['activity']}")

def take_screenshot(d, filename: str):
    path = OUTPUT_DIR / filename
    d.screenshot(str(path))
    print(f"  저장: {path}")
    return path

def capture(target: str = "both"):
    d = connect_device()

    if target in ("production", "both"):
        navigate_to_list_profile(d, PACKAGES["production"])
        take_screenshot(d, "before_production.png")
        d.press("back")
        time.sleep(1)

    if target in ("beta", "both"):
        navigate_to_list_profile(d, PACKAGES["beta"])
        take_screenshot(d, "before_beta.png")
        d.press("back")

    if target == "after":
        navigate_to_list_profile(d, PACKAGES["beta"])
        take_screenshot(d, "after_beta.png")
        d.press("back")

    print("완료!")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "both"
    capture(target)
```

**Step 3: uiautomator dump로 실제 UI 텍스트 확인**

스크립트 실행 전, 실제 앱에서 화면 구조를 확인해야 함:

```bash
# production 앱 실행 후 마이컬리 탭까지 수동 이동한 상태에서
adb -s R3CT10A3JCE shell uiautomator dump /sdcard/ui_dump.xml
adb -s R3CT10A3JCE pull /sdcard/ui_dump.xml /tmp/ui_dump.xml
cat /tmp/ui_dump.xml | grep -i "프로필\|style\|스타일" | head -20
```

실제 텍스트를 확인한 후 `navigate_to_list_profile()` 함수의 텍스트 목록을 업데이트.

**Step 4: 스크립트 테스트 실행**

```bash
cd /Users/pilju.bae/AndroidStudioProjects/kurly-android
python3 scripts/capture_list_profile.py production
# 예상 출력:
# Connected: SM-S918N
# [com.dbs.kurly.m2] 앱 실행...
#   마이컬리 탭...
#   현재 Activity: .../ListProfileActivity
#   저장: docs/screenshot/before_production.png
```

---

## Task 3: Before 스크린샷 캡처

**사전 조건:**
- Task 2 스크립트 완성 + 테스트 통과
- R3CT10A3JCE 기기에 두 앱 로그인 완료

**Step 1: 스크린샷 캡처**

```bash
cd /Users/pilju.bae/AndroidStudioProjects/kurly-android
python3 scripts/capture_list_profile.py both
```

예상 저장 파일:
- `docs/screenshot/before_production.png`
- `docs/screenshot/before_beta.png`

**Step 2: 스크린샷 확인**

```bash
ls -lh docs/screenshot/
open docs/screenshot/before_production.png
open docs/screenshot/before_beta.png
```

---

## Task 4: Fix Applier — Compose 코드 수정

**목적:** `design-diff-report.md` + 스크린샷 비교를 기반으로 `ListProfileScreen.kt` 수정

**Files:**
- Modify: `features/src/main/java/com/kurly/features/mykurlystyle/siteprofile/list/ListProfileScreen.kt`
- Modify (필요 시): `features/src/main/java/com/kurly/features/mykurlystyle/siteprofile/StepBodyContent.kt`
- Create: `docs/plans/non-kpds-values.md` (KPDS 근사치 목록)

**Step 1: 각 차이점 수정**

이미 확인된 수정 사항들:

### 수정 1: 섹션 가로 padding (15dp → 수정)
```kotlin
// ListProfileScreen.kt ProfileCategorySection 내부
// Before:
modifier = Modifier
    .fillMaxWidth()
    .padding(horizontal = 16.dp, vertical = 12.dp)

// production 값이 paddingHorizontal=15dp이면:
// → KPDS에 15dp 없음 → 16dp 유지하거나 production 기준 따름
// → Code Analyzer 리포트 기반으로 결정
```

### 수정 2: 저장 버튼 margin
```kotlin
// ListProfileScreen.kt KurlyBoxButton modifier
// Before:
modifier = Modifier
    .fillMaxWidth()
    .navigationBarsPadding()
    .padding(horizontal = 16.dp, vertical = 12.dp)

// XML은 marginHorizontal="12dp" → KPDS 12dp spacer 있음
// production 기준 맞추려면:
modifier = Modifier
    .fillMaxWidth()
    .navigationBarsPadding()
    .padding(horizontal = 12.dp, vertical = 12.dp)
```

### 수정 3: 다이얼로그 제목 typography
```kotlin
// SegmentInfoComposeDialog
// Before: style = KurlyTheme.typography.bold20
// XML: textSize="18sp" → KPDS에 bold18 있으면 사용, 없으면 bold20 유지
// Code Analyzer가 KPDS typography 목록 확인 후 결정
```

### 수정 4: Segment info description 텍스트
```kotlin
// SegmentInfoComposeDialog segments forEach → Text(description)
// Before: style = KurlyTheme.typography.regular14
// XML: textSize="13sp" → KPDS에 regular13 없음 → regular14 유지 (근사치)
// → non-kpds-values.md에 기록
```

### 수정 5: 저장 버튼 gradient 배경 (확인 필요)
```kotlin
// XML: android:background="@drawable/view_bottom_button_gradient"
// Compose: 없음
// → production 앱 스크린샷 확인 후 gradient 추가 여부 결정
// gradient 필요시:
Box(modifier = Modifier.background(
    brush = Brush.verticalGradient(
        colors = listOf(Color.Transparent, BackgroundColorTokens.Background1.toColor())
    )
)) {
    KurlyBoxButton(...)
}
```

**Step 2: 차이점 수정 후 KPDS 근사치 목록 문서화**

```markdown
# docs/plans/non-kpds-values.md
## KPDS 근사치 사용 목록 (KMA-7041)

| 항목 | Production 값 | 적용한 KPDS 값 | 사유 |
|------|--------------|---------------|------|
| segment info desc | 13sp | regular14 (14sp) | KPDS에 13sp 없음 |
| ...  | ...          | ...            | ...  |
```

**Step 3: 빌드 확인**

```bash
./gradlew :features:compileBetaDebugKotlin
# Expected: BUILD SUCCESSFUL
```

---

## Task 5: After 스크린샷 캡처

**Step 1: Beta 앱 재빌드 및 설치**

```bash
./gradlew :app:installBetaDebug
# 또는 Android Studio에서 Run 'app' (beta flavor)
```

**Step 2: After 스크린샷**

```bash
python3 scripts/capture_list_profile.py after
# 저장: docs/screenshot/after_beta.png
```

**Step 3: 최종 비교**

```bash
open docs/screenshot/before_production.png
open docs/screenshot/before_beta.png
open docs/screenshot/after_beta.png
```

`after_beta.png`가 `before_production.png`와 시각적으로 일치하면 완료.

---

## 완료 기준

- [ ] `docs/screenshot/before_production.png` 저장됨
- [ ] `docs/screenshot/before_beta.png` 저장됨
- [ ] `docs/plans/design-diff-report.md` 생성됨
- [ ] `ListProfileScreen.kt` 수정 완료
- [ ] `docs/screenshot/after_beta.png` 저장됨
- [ ] `docs/plans/non-kpds-values.md` 생성됨
- [ ] 빌드 통과

## 커밋

```bash
git add features/src/main/java/com/kurly/features/mykurlystyle/siteprofile/list/ListProfileScreen.kt
git add docs/plans/design-diff-report.md docs/plans/non-kpds-values.md
git add scripts/capture_list_profile.py
git commit -m "KMA-7041 디자인 검증 및 Compose 스타일 수정"
```
