# 앱 딥링크 & 스킴 처리 구조 분석

> 작성일: 2026-04-06

---

## 1. 지원 스킴

| 스킴 | 용도 |
|------|------|
| `kurly://` | 일반 내부 딥링크 |
| `kurly-sso://` | SSO 인증 |
| `https://www.kurly.com/*` | App Links → 자동 변환 |

스킴 정의 파일: `link/src/main/kotlin/com/kurly/link/extensions/UriExt.kt`

```kotlin
const val SCHEME_DEEP_LINK = "kurly"
const val SCHEME_DEEP_LINK_SSO = "kurly-sso"

fun Uri.isDeepLink(): Boolean {
    return this.scheme in listOf(SCHEME_DEEP_LINK, SCHEME_DEEP_LINK_SSO)
}
```

---

## 2. 전체 처리 흐름

```
외부 딥링크 수신 (AppStarterActivity)
  ↓
DeferredDeepLinkHandler.fetchDeepLink()
  ├── kurly:// → 그대로 사용
  └── https://kurly.com → TotalDeepLinkConverterImpl로 변환
  ↓
LinkParser.parseUri()
  ↓
InternalDeepLinkIntentGeneratorImpl
  ↓ (host 기준으로 Generator 선택)
각 IntentGenerator → Intent 생성 → 화면 이동
```

### 웹투앱 흐름 (WebView에서 진입 시)

```
WebView 내 링크 클릭 / JS Interface 호출
  ↓
BasicWebViewClient.shouldOverrideUrlLoading()
또는
NavigateWebInterfaceAdapter.handleDeepLink()
  ↓
WebViewFacade.navigateUrl()
  ↓
UriNavigator.navigate()
  ↓
LinkParser.parseUri()
  ↓
Intent 생성 → 화면 이동
```

---

## 3. 핵심 클래스 및 파일

| 클래스 | 파일 경로 | 역할 |
|--------|----------|------|
| `LinkParser` | `link/src/main/kotlin/com/kurly/link/LinkParser.kt` | URL 파싱 중앙 진입점 |
| `TotalDeepLinkConverterImpl` | `app/.../link/TotalDeepLinkConverterImpl.kt` | HTTP → kurly:// 변환 총괄 |
| `InternalDeepLinkIntentGeneratorImpl` | `app/.../link/InternalDeepLinkIntentGeneratorImpl.kt` | kurly:// → Intent 생성 총괄 |
| `ExternalSchemeIntentGeneratorImpl` | `app/.../link/ExternalSchemeIntentGeneratorImpl.kt` | 외부 스킴 Intent 생성 (NEW_TASK) |
| `DeferredDeepLinkHandler` | `app/.../start/DeferredDeepLinkHandler.kt` | 앱 시작 시 딥링크 추출 |
| `AppStarterActivity` | `app/.../start/AppStarterActivity.kt` | 딥링크 수신 진입점 |
| `BasicWebViewClient` | `features/.../webviewclient/BasicWebViewClient.kt` | WebView URL 인터셉트 |
| `NavigateWebInterfaceAdapter` | `features/.../navigate/NavigateWebInterfaceAdapter.kt` | JS Interface 구현 |
| `UriNavigator` | `navigation/uri/UriNavigator.kt` | WebView → LinkParser 연결 |
| `DeepLinkHost` | `link/.../generator/builder/DeepLinkHost.kt` | 지원 host 상수 목록 |
| `DeepLinkBuilder` | `link/.../generator/builder/DeepLinkBuilder.kt` | kurly:// URI 빌더 |

---

## 4. host → 화면 매핑

| Deep Link | 화면 |
|-----------|------|
| `kurly://home` | 홈 |
| `kurly://product?no=ID` | 상품 상세 |
| `kurly://category?no=ID` | 카테고리 목록 |
| `kurly://collection?id=ID` | 컬렉션 |
| `kurly://collection-groups` | 컬렉션 그룹 |
| `kurly://brand?id=ID` | 브랜드 |
| `kurly://search?keyword=` | 검색 |
| `kurly://cart` | 장바구니 |
| `kurly://order` | 주문 내역 |
| `kurly://claim` | 클레임 |
| `kurly://mykurly` | 마이쿨리 |
| `kurly://login` | 로그인 |
| `kurly://signup` | 회원가입 |
| `kurly://auth` | 인증 |
| `kurly://event?id=ID` | 이벤트 |
| `kurly://lounge` | 라운지 |
| `kurly://kurlylog` | 쿨리로그 |
| `kurly://recipe` | 레시피 |
| `kurly://brand` | 브랜드 |
| `kurly://games` | 게임 |
| `kurly://gift` | 선물하기 |
| `kurly://now` | 컬리나우 |
| `kurly://labs` | 컬리랩스 |
| `kurly://kurlypay` | 컬리페이 |
| `kurly://mission` | 미션 |
| `kurly://panel` | 패널 |
| `kurly://notice` | 공지사항 |
| `kurly://delivery` | 배송 |
| `kurly://address` | 주소 |
| `kurly://user-info` | 사용자 정보 |
| `kurly://vip-prediction` | VIP 예측 |
| `kurly://appcard` | 앱카드 |
| `kurly://notificationCenter` | 알림센터 |
| `kurly://pushAlarmSetter` | 푸시 알람 설정 |
| `kurly://frequently-products` | 자주 사는 상품 |
| `kurly://personal-product` | 개인 맞춤 상품 |
| `kurly://best-products` | 베스트 상품 |
| `kurly://new-products` | 신상품 |
| `kurly://sale` | 세일 |
| `kurly://web` | 웹뷰 |
| `kurly://compose` | Compose 화면 |
| `kurly://growth` | 그로스 |
| `kurly://open` | 오픈 |

---

## 5. HTTP → kurly:// 변환 예시

총 **29개의 DeepLinkConverter** 존재. `app/.../link/converter/` 디렉토리에 위치.

| HTTP URL | 변환 결과 |
|----------|----------|
| `https://www.kurly.com/goods/5088325` | `kurly://product?no=5088325` |
| `https://www.kurly.com/goods/ID?dealNo=N` | `kurly://product?no=ID&dealNo=N` |
| `https://www.kurly.com/categories/912011` | `kurly://category?no=912011` |
| `https://www.kurly.com/search?keyword=딸기` | `kurly://search?keyword=딸기` |
| `https://www.kurly.com/curated/collection/ID` | `kurly://collection?id=ID` |
| `https://www.kurly.com/brands/ID` | `kurly://brand?id=ID` |
| `https://www.kurly.com/events/ID` | `kurly://event?id=ID` |
| `https://www.kurly.com/recipe/*` | `kurly://recipe?*` |
| `https://www.kurly.com/lounge/*` | `kurly://lounge?*` |

---

## 6. 웹투앱 진입 방식 (WebView)

### 등록된 JavaScript Interface 목록

`WebViewFacade.kt` 에서 등록:

| Interface 등록명 | 클래스 | 용도 |
|----------------|--------|------|
| `Android_Navigate` | `NavigateWebInterface` | 화면 전환, 딥링크 |
| `Android` | `AndroidWebInterface` | 레거시 (토스트, 다이얼로그) |
| `Android_User` | `UserWebInterface` | 사용자 권한, 연락처 |
| `Android_Analytics` | `AnalyticsWebInterface` | 분석 이벤트 |
| `Android_Device` | `DeviceWebInterface` | 기기 정보 |
| `Android_View` | `ViewWebInterface` | UI 조작 |

### 웹에서 호출하는 주요 메서드

```javascript
// 딥링크로 이동
Android_Navigate.handleDeepLink(JSON.stringify({
    url: "kurly://product?no=12345"
}));

// 새 WebView 열기
Android_Navigate.openWebView(JSON.stringify({
    url: "https://kurly.com/search",
    title: "검색"
}));

// WebView 닫기
Android_Navigate.closeWebView(JSON.stringify({ ... }));

// 레거시 방식
Android.postWebViewController(JSON.stringify({
    code: "OpenDeepLink",
    url: "kurly://product?no=12345"
}));
```

---

## 7. LinkResult 모델

`link/src/main/kotlin/com/kurly/link/result/LinkResult.kt`

```kotlin
sealed class LinkResult {
    data class Success(val intent: Intent, val uri: Uri) : LinkResult()
    data object HandledWithoutAction : LinkResult()
    data class Failure(val cause: LinkHandleException, val failedUri: Uri?) : LinkResult()
}
```

---

## 8. 내부 vs 외부 딥링크 처리 차이

| 구분 | 진입점 | Task 처리 |
|------|--------|----------|
| WebView 내 클릭 | `BasicWebViewClient.shouldOverrideUrlLoading()` | 같은 태스크 |
| JS Interface 호출 | `NavigateWebInterfaceAdapter.handleDeepLink()` | 같은 태스크 |
| 외부 앱/알림/공유 | `AppStarterActivity.onCreate/onNewIntent()` | 같은 태스크 |
| 외부 스킴 (market://, tel:// 등) | `ExternalSchemeIntentGeneratorImpl` | `FLAG_ACTIVITY_NEW_TASK` |
