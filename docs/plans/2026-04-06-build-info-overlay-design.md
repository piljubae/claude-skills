# Build Info Overlay 디자인

## 목표

개발자 모드 활성화 시, 스크린샷에 빌드 정보(flavor, build type, version, 빌드 시간)가 항상 찍히도록 화면 우측 하단에 오버레이를 표시한다.

## 배경

- 디자이너/QA가 스크린샷을 공유할 때 "이게 beta 빌드야 store야?", "어느 버전이야?" 질문이 반복됨
- 스크린샷 자체에 빌드 정보가 포함되면 커뮤니케이션 비용 감소

## 결정 사항

### 표시 위치
- 화면 우측 하단 고정
- 드래그 불가, 터치 이벤트 없음

### 표시 내용
```
beta·debug
v3.12.1 (456)
04/06 14:30
```
- `BuildConfig.FLAVOR` · `BuildConfig.BUILD_TYPE`
- `BuildConfig.VERSION_NAME` (`BuildConfig.VERSION_CODE`)
- 빌드 시간: `buildConfigField`로 빌드 타임에 주입

### 스타일
- 텍스트 크기: 10sp
- 텍스트 색: 흰색
- 배경: 반투명 (`#80000000`), 4dp rounded corner
- 패딩: 4dp horizontal, 2dp vertical

### 온오프
- `SharedPreferences`에 boolean 저장 (기본값: true)
- 기존 개발자 메뉴(`DebuggingItem`)에 토글 항목 추가
- 토글 시 `View.VISIBLE` / `View.GONE` 전환

## 구조

### 새 파일

**`BuildInfoOverlayView`** (`debug-helper` 모듈)
- `FrameLayout` 서브클래스 (또는 단순 `TextView`)
- `addToWindow(activity)` / `removeFromWindow(activity)` 메서드
- `DebuggingView`와 완전 독립 — 같은 `decorView`에 별도로 attach

**`BuildInfoOverlayController`** (또는 `DebuggingModuleConfig` 확장)
- `SharedPreferences` 기반 표시 여부 관리
- `show()` / `hide()` / `isEnabled` 제공

### 변경 파일

**`DebuggingViewLifecycleCallbacks`**
- `onActivityCreated`: `BuildInfoOverlayView.addToWindow(activity)` 추가
- `onActivityDestroyed`: `BuildInfoOverlayView.removeFromWindow(activity)` 추가

**`build.gradle.kts` (`:app`)**
- `buildConfigField("String", "BUILD_TIME", ...)` 추가

**개발자 메뉴 항목 등록 위치 (앱 초기화 시점)**
- `BuildInfoOverlayController` 토글 `DebuggingItem` 등록

## 고려하지 않은 것 (YAGNI)

- 오버레이 위치 변경 (우측 하단 고정으로 충분)
- 표시 내용 커스터마이즈
- 비디오 녹화 시 자동 숨김
