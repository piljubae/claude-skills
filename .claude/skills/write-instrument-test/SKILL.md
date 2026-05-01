---
name: write-instrument-test
description: Composable/Screen 파일 또는 Jira 티켓을 받아 Android instrumented test 코드를 작성한다. UiState 렌더링·인터랙션·impression 타이밍 케이스 자동 분석 후 시나리오 목록 확인 → 코드 작성. 사용자가 "/write-instrument-test", "instrumented test 작성", "UI 테스트 작성" 표현을 쓸 때 이 스킬을 사용한다.
argument-hint: [path/to/Screen.kt | KMA-XXXX] [--help]
---

# Write Instrument Test Skill

Composable 또는 Jira 티켓을 입력받아 **2단계** (분석 → 코드 작성) 로 instrumented test를 생성한다.

## 0. `--help`

`$ARGUMENTS` 에 `--help` 포함 시 아래 사용법만 출력하고 종료:

```
/write-instrument-test path/to/ProductDetailScreen.kt
/write-instrument-test KMA-XXXX
/write-instrument-test features/.../BannerContent.kt  # 특정 Composable
```

## 1. 레퍼런스 로드

`references/android-instrument-testing.md` 를 Read — 이후 모든 판단의 기준으로 삼는다.

## 2. 대상 파일 결정

`$ARGUMENTS` 파싱:

| 입력 형태 | 처리 |
|----------|------|
| `.kt` 파일 경로 | 해당 파일을 직접 사용 |
| `{UPPERCASE}-{DIGITS}` 티켓 키 | Jira 티켓 조회 후 연관 Composable/Screen 파일 탐색 |
| 인수 없음 | `"대상 파일 경로 또는 티켓 번호를 입력해주세요"` 출력 후 종료 |

### 티켓 키인 경우 — 파일 탐색

`mcp__claude_ai_Atlassian__getJiraIssue` 로 티켓 조회:
- cloudId: `kurly0521.atlassian.net`
- issueIdOrKey: `{TICKET_KEY}`

티켓 summary/description 에서 화면명·ViewModel명 키워드 추출 후 Glob + Grep 으로 파일 탐색.
복수 파일 발견 시 목록 제시 → 사용자 선택.

## 3. 대상 분석

대상 파일과 연관 파일들을 읽어 아래 7차원에 필요한 정보를 파악한다.

### 3-1. UiState 구조 (차원 1·2·4 기반)
- UiState data class 프로퍼티 목록
- Loading / Success / Error / Empty 분기 존재 여부
- nullable 프로퍼티 → 경계값 케이스 후보
- 상태 전이 경로: 어떤 액션이 어떤 상태로 전이를 유발하는가

### 3-2. 조건부 UI 노출 (차원 3 기반)
`if` / `when` / `isXxx` 분기로 UI가 달라지는 지점 전체 목록:
- 예: `if (uiState.isAd)`, `when (uiState.badge)`, `isSoldOut`, `isEmpty()`
- 다중 조건이 겹치는 경우 → 결정 테이블 케이스 후보

### 3-3. 인터랙션 (차원 5 기반)
Composable 파라미터 중 `() -> Unit` / `(T) -> Unit` 콜백 목록:
- 예: `onProductClick`, `onAddToCartClick`, `onRetryClick`
- enabled/disabled 조건이 있는 버튼 파악

### 3-4. 접근성 요소 (차원 6 기반)
- `contentDescription` 지정 여부
- `Modifier.testTag()` 지정 여부
- `enabled` 파라미터를 받는 컴포넌트 (버튼, 체크박스 등)
- LazyColumn 존재 여부 → `performScrollToNode` 필요 여부

### 3-5. Impression 추적 (차원 7 기반)
`AnalyticsEventConsumer` / `FakeAnalyticsEventConsumer` / impression 관련 파라미터 포함 여부.
존재하면 → 차원 7 시나리오 추가.

## 4. 시나리오 목록 출력 (CP)

분석 결과를 바탕으로 **7차원** 시나리오 목록을 출력한다.
각 차원은 분석에서 해당 요소가 발견된 경우에만 포함. 없으면 차원 생략.

```
## Test List — {파일명}

### 1. UiState 렌더링  ← Equivalence Partitioning: 각 상태 파티션
- [ ] 로딩 상태에서 로딩 인디케이터가 표시된다
- [ ] 데이터가 있을 때 {주요 UI 요소}가 표시된다
- [ ] 빈 목록일 때 빈 화면 안내 문구가 표시된다
- [ ] 에러 상태에서 에러 UI와 재시도 버튼이 표시된다

### 2. 상태 전이  ← FST: 전이 경로 커버
- [ ] 로딩 완료 후 데이터가 표시되고 로딩 인디케이터가 사라진다
- [ ] 에러 상태에서 재시도 클릭 시 로딩 상태로 전이된다

### 3. 조건부 노출  ← Decision Table: 다중 조건 조합
- [ ] {조건A} 일 때 {UI 요소}가 표시된다
- [ ] {조건B} 일 때 {UI 요소}가 표시되지 않는다

### 4. 경계값  ← BVA: null·빈값·최대값
- [ ] 빈 목록(0개)에서 크래시 없이 빈 화면이 표시된다
- [ ] 긴 텍스트({필드명})가 말줄임 처리된다             (해당 시)
- [ ] null 이미지에서 크래시 없이 placeholder가 표시된다 (해당 시)

### 5. 인터랙션 → 콜백  ← SIVT-I
- [ ] {버튼/카드} 클릭 시 {onXxxClick}이 호출된다
- [ ] 비활성화 상태에서 클릭이 동작하지 않는다           (해당 시)

### 6. 접근성 / Semantics  ← SIVT-V
- [ ] {인터랙티브 요소}에 contentDescription이 존재한다
- [ ] 비활성 버튼이 semantics에 disabled로 전달된다      (해당 시)

### 7. Impression 타이밍  ← SIVT-T (impression 있을 때만)
- [ ] 화면 진입 시 impression 이벤트가 발화된다
- [ ] 스크롤 중에는 impression 이벤트가 발화되지 않는다
- [ ] 스크롤 종료 후 impression 이벤트가 발화된다

---
시나리오를 추가/제거하거나 [Enter] 로 코드 작성을 시작하세요.
[Enter] 진행  [e] 수정  [q] 종료
```

**규칙:**
- UiState sealed class 있으면 모든 하위 타입이 차원 1에 등장해야 한다
- 조건부 분기가 2개 이상 겹치면 차원 3에 결정 테이블 케이스 추가
- `contentDescription` / `testTag` 없는 인터랙티브 요소 발견 시 차원 6에 명시
- 차원 7은 `AnalyticsEventConsumer` 파라미터가 있을 때만 포함

`e` 입력 시 사용자 수정 내용을 반영 후 재출력.

## 5. 테스트 코드 작성

### 출력 경로 결정

소스 파일 경로 기준으로 `androidTest` 미러 경로 계산:

```
src/main/java/com/kurly/.../ProductDetailScreen.kt
→ src/androidTest/java/com/kurly/.../ProductDetailScreenTest.kt
```

파일이 이미 존재하면:
```
ProductDetailScreenTest.kt 이 이미 존재합니다.
[Enter] 기존 파일에 추가  [o] 덮어쓰기  [n] 새 파일명 지정
```

### 의존성 체크

대상 모듈의 `build.gradle.kts` 를 읽어 아래 의존성 존재 여부 확인:

```kotlin
androidTestImplementation(libs.androidx.compose.ui.test.junit4)
debugImplementation(libs.androidx.compose.ui.test.manifest)
```

없으면 추가 필요 항목을 안내하고 진행. 자동 수정은 하지 않음.

### 코드 생성 규칙

`references/android-instrument-testing.md` 의 패턴을 그대로 따른다:

- `@RunWith(AndroidJUnit4::class)` 필수
- `createAndroidComposeRule<ComponentActivity>()` 사용
- UiState 직접 주입 (ViewModel/Hilt 없음)
- `KurlyTheme { }` 래핑 필수
- 한글 백틱 메서드명
- Given-When-Then 구조
- string resource 는 `composeTestRule.activity.getString(R.string.xxx)` 로 획득
- impression 시나리오는 `mainClock.autoAdvance = false` + `FakeAnalyticsEventConsumer` 패턴

생성 후:
```
✅ 테스트 파일 작성 완료: {경로}

실행 명령어:
./gradlew :{module}:connectedDebugAndroidTest \
  --tests "*.{TestClassName}"
```
