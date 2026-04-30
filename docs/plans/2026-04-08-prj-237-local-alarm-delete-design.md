# PRJ-237 로컬 푸시 삭제 — 설계 문서

**날짜**: 2026-04-08  
**티켓**: [PRJ-237](https://kurly0521.atlassian.net/browse/PRJ-237)  
**작업**: 마수동/광수동 미동의 및 로그아웃/탈퇴 시 로컬 푸시 신청 내역 삭제

---

## 삭제 정책

| 트리거 | 삭제 범위 |
|---|---|
| 마수동 OFF | `AD_` prefix 알람만 |
| 광수동 OFF | `AD_` prefix 알람만 |
| 직접 로그아웃 (웹뷰) | 전체 |
| 마이컬리 탭 로그아웃 / 토큰 만료(401-1003) | 전체 |
| 탈퇴 (본 기기, WV3200) | 전체 |
| 탈퇴 (타 기기) | 별도 액션 없음 — 토큰 만료 시 자연 처리 |

---

## 아키텍처 결정

### WebAlarmCanceller 인터페이스 신설 (domain)

AlarmManager cancel 로직은 현재 `WebAlarmDispatcherImpl`(features) 내부에만 존재.  
`LogoutToGuestUseCase`(domain)에서도 호출해야 하므로, domain에 인터페이스를 추가하고 features에서 구현한다.

Repository에 AlarmManager 로직을 넣는 방안(단순하지만 관심사 분리 위반)은 채택하지 않음.

```kotlin
// domain
interface WebAlarmCanceller {
    fun cancelByPrefix(prefix: String)
    fun cancelAll()
}
```

### UseCase 래핑

ViewModel → UseCase → WebAlarmCanceller 흐름을 유지한다.  
`LogoutToGuestUseCase`는 이미 UseCase이므로 `WebAlarmCanceller`를 직접 inject.

| UseCase | 동작 | 사용처 |
|---|---|---|
| `DeleteAdAlarmsUseCase` | `cancelByPrefix("AD_")` | 마수동/광수동 OFF ViewModel |
| `DeleteAllWebAlarmsUseCase` | `cancelAll()` | 로그아웃/탈퇴 ViewModel |

---

## 신규 컴포넌트

### WebAlarmCanceller (domain 인터페이스)
- `cancelByPrefix(prefix: String)` — prefix로 시작하는 알람 일괄 취소
- `cancelAll()` — 전체 알람 취소

### WebAlarmCancellerImpl (features)
- `@ApplicationContext` + `NotificationRepository` inject
- `cancelByPrefix`: `getWebAlarms()` → prefix 필터 → 각 requestCode로 AlarmManager.cancel → DataStore 업데이트
- `cancelAll`: `getWebAlarms()` 전체 → 각 requestCode로 AlarmManager.cancel → DataStore 비우기
- AlarmManager cancel 로직은 기존 `WebAlarmDispatcherImpl.releaseAlarm()`과 동일 패턴

### DeleteAdAlarmsUseCase (domain)
```kotlin
class DeleteAdAlarmsUseCase @Inject constructor(
    private val webAlarmCanceller: WebAlarmCanceller,
) {
    operator fun invoke() = webAlarmCanceller.cancelByPrefix("AD_")
}
```

### DeleteAllWebAlarmsUseCase (domain)
```kotlin
class DeleteAllWebAlarmsUseCase @Inject constructor(
    private val webAlarmCanceller: WebAlarmCanceller,
) {
    operator fun invoke() = webAlarmCanceller.cancelAll()
}
```

---

## 기존 파일 수정

### LogoutToGuestUseCase (domain)
- `WebAlarmCanceller` inject 추가
- `authRepository.logout()` 직후 `webAlarmCanceller.cancelAll()` 호출

```kotlin
authRepository.logout()
webAlarmCanceller.cancelAll()  // 추가
authRepository.getGuestLoginToken()
loginStateHandler.onSuccessGuestLogin(session.sessionInfo)
```

### KurlyWebViewViewModel (features)
- `DeleteAdAlarmsUseCase`, `DeleteAllWebAlarmsUseCase` inject 추가
- `updateMarketingNotificationAllow()`: `result is Success && isAllow == false` 시 `deleteAdAlarmsUseCase.invoke()`
- `logout()`: `loginUseCase.execute()` 전에 `deleteAllWebAlarmsUseCase.invoke()`
- `deleteAllWebAlarms()` 메서드 추가 — Fragment의 `onSuccessUnRegister()`에서 호출용

### NotificationSettingsViewModel (features)
- `DeleteAdAlarmsUseCase` inject 추가
- `updateNotificationSetting()`: `result is Success && !setting.isMarketingNotificationAllow` 시 `deleteAdAlarmsUseCase.invoke()`

### BaseKurlyWebViewFragment (features)
- `onSuccessUnRegister()` 내 `webViewViewModel.deleteAllWebAlarms()` 호출 추가
- 기존 `finishWithPostMessageCode()` 및 `globalEventPublisher.publish()` 순서 유지

---

## WV3200 탈퇴 흐름 상세

```
onSuccessUnRegister()
  → webViewViewModel.deleteAllWebAlarms()      ← 즉시 삭제 (신규)
  → finishWithPostMessageCode(WV3200)
  → globalEventPublisher.publish(UnExpectedLogoutEvent(..., Unregister))
      → GlobalEventHandler: 다이얼로그 표시만 (LogoutToGuestUseCase 호출 없음)
  → 실제 세션 정리는 이후 401 시점
```

GlobalEventHandler는 UI/dialog 담당이므로 알람 삭제 로직 추가하지 않음.

---

## Hilt 바인딩

`WebAlarmCanceller` → `WebAlarmCancellerImpl` 바인딩 모듈 추가 필요.  
위치: `features` 모듈 DI 모듈 (기존 `WebAlarmDispatcher` 바인딩과 동일한 파일 또는 근처).

---

## 에러 처리

- 알람 삭제 실패는 silent fail (로그아웃/탈퇴 흐름을 블로킹하지 않음)
- `WebAlarmDispatcherImpl.delete()` 기존 패턴과 동일하게 예외 무시

---

## 수정 파일 목록

| 파일 | 모듈 | 변경 유형 |
|---|---|---|
| `WebAlarmCanceller.kt` | domain | 신규 |
| `DeleteAdAlarmsUseCase.kt` | domain | 신규 |
| `DeleteAllWebAlarmsUseCase.kt` | domain | 신규 |
| `WebAlarmCancellerImpl.kt` | features | 신규 |
| `ApplicationBindModule.kt` | app | 수정 |
| `LogoutToGuestUseCase.kt` | domain | 수정 |
| `KurlyWebViewViewModel.kt` | features | 수정 |
| `NotificationSettingsViewModel.kt` | features | 수정 |
| `BaseKurlyWebViewFragment.kt` | features | 수정 |

---

## 테스트 플랜

### 기반 클래스
- `BaseMockKTest` — MockK 초기화 + MainDispatcher 교체 자동 처리 (기본)
- `WebAlarmCancellerImplTest`는 Context mockk 직접 선언 (`BaseContextMockkTest`는 app 모듈 전용)

### 기존 테스트 파일 현황
- `KurlyWebViewViewModel` — 테스트 파일 없음 → 신규 작성
- `NotificationSettingsViewModel` — 테스트 파일 없음 → 신규 작성
- `WebAlarmDispatcherImplTest` — 기존 있음 (참고용)

---

### Test List — WebAlarmCancellerImpl

**1. 정상 동작**
- [ ] `cancelByPrefix("AD_")` 시 `AD_` prefix 알람의 requestCode로 AlarmManager cancel 호출
- [ ] `cancelByPrefix("AD_")` 시 `notificationRepository.deleteWebAlarmsByPrefix("AD_")` 호출
- [ ] `cancelAll()` 시 전체 알람 requestCode로 AlarmManager cancel 호출
- [ ] `cancelAll()` 시 `notificationRepository.deleteAllWebAlarms()` 호출
- [ ] `cancelByPrefix("AD_")` 시 `INFO_` prefix 알람 AlarmManager cancel 호출 안 함

**2. 에러 처리**
- [ ] `getWebAlarms()`가 예외를 던지면 → silent fail (예외 전파 안 함)

**4. 경계값**
- [ ] 알람 없을 때 `cancelByPrefix` → AlarmManager 호출 없이 `deleteWebAlarmsByPrefix` 호출
- [ ] 알람 없을 때 `cancelAll` → AlarmManager 호출 없이 `deleteAllWebAlarms` 호출

**7. 도메인 불변성**
- [ ] AlarmManager cancel 실패 여부와 무관하게 `deleteWebAlarmsByPrefix`/`deleteAllWebAlarms` 반드시 호출

---

### Test List — LogoutToGuestUseCase (수정분)

**1. 정상 동작**
- [ ] 로그아웃 성공 시 `webAlarmCanceller.cancelAll()` 호출

**2. 에러 처리**
- [ ] `authRepository.logout()` 실패 시 `cancelAll()` 호출 안 함

**3. 상태 전이 / 순서**
- [ ] `authRepository.logout()` → `cancelAll()` → `authRepository.getGuestLoginToken()` 순서 보장

---

### Test List — DeleteAdAlarmsUseCase / DeleteAllWebAlarmsUseCase

- [ ] `DeleteAdAlarmsUseCase.invoke()` → `webAlarmCanceller.cancelByPrefix("AD_")` 호출
- [ ] `DeleteAllWebAlarmsUseCase.invoke()` → `webAlarmCanceller.cancelAll()` 호출

---

### Test List — KurlyWebViewViewModel (수정분, 신규 파일)

**1. 정상 동작**
- [ ] `updateMarketingNotificationAllow(false)` + 서버 성공 → `deleteAdAlarmsUseCase()` 호출
- [ ] `logout()` 호출 시 `deleteAllWebAlarmsUseCase()` 호출

**2. 에러 처리**
- [ ] `updateMarketingNotificationAllow(false)` + 서버 실패 → `deleteAdAlarmsUseCase()` 호출 안 함

**3. 순서**
- [ ] `logout()` 시 `deleteAllWebAlarmsUseCase()` 먼저, `loginUseCase` 나중

**4. 경계값**
- [ ] `updateMarketingNotificationAllow(true)` + 서버 성공 → `deleteAdAlarmsUseCase()` 호출 안 함
- [ ] `updateMarketingNotificationAllow(null)` + 서버 성공 → `deleteAdAlarmsUseCase()` 호출 안 함

---

### Test List — NotificationSettingsViewModel (수정분, 신규 파일)

**1. 정상 동작**
- [ ] `updateNotificationSetting(isMarketingNotificationAllow = false)` + 서버 성공 → `deleteAdAlarmsUseCase()` 호출

**2. 에러 처리**
- [ ] 서버 실패 시 → `deleteAdAlarmsUseCase()` 호출 안 함

**4. 경계값**
- [ ] `updateNotificationSetting(isMarketingNotificationAllow = true)` + 서버 성공 → `deleteAdAlarmsUseCase()` 호출 안 함
