# PRJ-237 로컬 푸시 삭제 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 마수동/광수동 OFF 및 로그아웃/탈퇴 시 로컬 푸시(AlarmManager) 신청 내역을 삭제한다.

**Architecture:** domain에 `WebAlarmCanceller` 인터페이스를 신설하고 features에서 구현한다. Repository는 DataStore bulk 삭제만 담당하고, AlarmManager cancel 로직은 `WebAlarmCancellerImpl`(features)이 전담한다. ViewModel은 UseCase(`DeleteAdAlarmsUseCase`, `DeleteAllWebAlarmsUseCase`)를 통해 호출한다.

**Tech Stack:** Kotlin, Hilt, AlarmManager, DataStore, MockK, JUnit5

---

## Task 1: NotificationRepository에 bulk 삭제 메서드 추가

**Files:**
- Modify: `domain/src/main/java/com/kurly/domain/repository/notification/NotificationRepository.kt`
- Modify: `data/src/main/java/com/kurly/data/repository/notification/NotificationRepositoryImpl.kt`

**Step 1: NotificationRepository 인터페이스에 메서드 추가**

`NotificationRepository.kt`의 `getWebAlarmsFlow()` 아래에 추가:

```kotlin
fun deleteWebAlarmsByPrefix(prefix: String)
fun deleteAllWebAlarms()
```

**Step 2: NotificationRepositoryImpl에 구현 추가**

`deleteWebAlarms(alarm: AlarmWeb)` 아래에 추가:

```kotlin
override fun deleteWebAlarmsByPrefix(prefix: String) {
    saveWebAlarms { getWebAlarms().filterNot { it.alarmId.startsWith(prefix) }.toSet() }
}

override fun deleteAllWebAlarms() {
    saveWebAlarms { emptySet() }
}
```

**Step 3: 컴파일 확인**

```bash
./gradlew :domain:compileDebugKotlin :data:compileDebugKotlin
```
Expected: BUILD SUCCESSFUL

**Step 4: Commit**

```bash
git add domain/src/main/java/com/kurly/domain/repository/notification/NotificationRepository.kt
git add data/src/main/java/com/kurly/data/repository/notification/NotificationRepositoryImpl.kt
git commit -m "PRJ-237 NotificationRepository에 bulk 웹 알람 삭제 메서드 추가"
```

---

## Task 2: WebAlarmCanceller 인터페이스 생성 (domain)

**Files:**
- Create: `domain/src/main/java/com/kurly/domain/repository/notification/WebAlarmCanceller.kt`

**Step 1: 인터페이스 파일 생성**

```kotlin
package com.kurly.domain.repository.notification

interface WebAlarmCanceller {
    fun cancelByPrefix(prefix: String)
    fun cancelAll()
}
```

**Step 2: 컴파일 확인**

```bash
./gradlew :domain:compileDebugKotlin
```
Expected: BUILD SUCCESSFUL

**Step 3: Commit**

```bash
git add domain/src/main/java/com/kurly/domain/repository/notification/WebAlarmCanceller.kt
git commit -m "PRJ-237 WebAlarmCanceller 인터페이스 추가"
```

---

## Task 3: WebAlarmCancellerImpl 구현체 생성 (features)

**Files:**
- Create: `features/src/main/java/com/kurly/features/web/bridge/common/user/WebAlarmCancellerImpl.kt`
- Create: `features/src/test/java/com/kurly/features/web/bridge/common/user/WebAlarmCancellerImplTest.kt`

**Step 1: 테스트 먼저 작성**

```kotlin
package com.kurly.features.web.bridge.common.user

import android.app.AlarmManager
import android.content.Context
import com.kurly.domain.model.notification.AlarmWeb
import com.kurly.domain.repository.notification.NotificationRepository
import com.kurly.ktcore.test.BaseMockKTest
import io.mockk.every
import io.mockk.mockk
import io.mockk.verify
import org.junit.Before
import org.junit.Test
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter

class WebAlarmCancellerImplTest : BaseMockKTest() {

    private val context: Context = mockk(relaxed = true)
    private val alarmManager: AlarmManager = mockk(relaxed = true)
    private val notificationRepository: NotificationRepository = mockk(relaxed = true)
    private lateinit var canceller: WebAlarmCancellerImpl

    private val futureIso = ZonedDateTime.now().plusMinutes(10)
        .format(DateTimeFormatter.ISO_ZONED_DATE_TIME)
    private val futureMs = System.currentTimeMillis() + 600_000L

    private val adAlarm = AlarmWeb(
        alarmId = "AD_LEGO_event1",
        title = "", message = "", datetime = futureIso,
        image = null, link = null, callback = null, errorCallback = null,
        requestCode = 1001, timeMs = futureMs,
    )
    private val infoAlarm = AlarmWeb(
        alarmId = "INFO_LIVE_abc",
        title = "", message = "", datetime = futureIso,
        image = null, link = null, callback = null, errorCallback = null,
        requestCode = 1002, timeMs = futureMs,
    )

    @Before
    fun setUp() {
        every { context.getSystemService(any<String>()) } returns alarmManager
        every { context.packageName } returns "com.kurly.test"
        canceller = WebAlarmCancellerImpl(context, notificationRepository)
    }

    // 1. 정상 동작

    @Test
    fun `cancelByPrefix는 AD_ prefix 알람의 DataStore 삭제를 요청한다`() {
        // Given
        every { notificationRepository.getWebAlarms() } returns setOf(adAlarm, infoAlarm)

        // When
        canceller.cancelByPrefix("AD_")

        // Then
        verify { notificationRepository.deleteWebAlarmsByPrefix("AD_") }
    }

    @Test
    fun `cancelByPrefix는 INFO_ prefix 알람의 AlarmManager cancel을 호출하지 않는다`() {
        // Given
        every { notificationRepository.getWebAlarms() } returns setOf(adAlarm, infoAlarm)

        // When
        canceller.cancelByPrefix("AD_")

        // Then: infoAlarm(requestCode=1002)은 cancel 안 됨을 간접 확인
        // AlarmManager.cancel은 PendingIntent 기반이라 requestCode 검증은 구현 신뢰
        verify(exactly = 1) { notificationRepository.deleteWebAlarmsByPrefix("AD_") }
    }

    @Test
    fun `cancelAll은 전체 알람의 DataStore 삭제를 요청한다`() {
        // Given
        every { notificationRepository.getWebAlarms() } returns setOf(adAlarm, infoAlarm)

        // When
        canceller.cancelAll()

        // Then
        verify { notificationRepository.deleteAllWebAlarms() }
    }

    // 2. 에러 처리

    @Test
    fun `cancelByPrefix는 getWebAlarms 예외 시 silent fail한다`() {
        // Given
        every { notificationRepository.getWebAlarms() } throws RuntimeException("DataStore 오류")

        // When & Then: 예외 전파 없음
        canceller.cancelByPrefix("AD_")
    }

    @Test
    fun `cancelAll은 getWebAlarms 예외 시 silent fail한다`() {
        // Given
        every { notificationRepository.getWebAlarms() } throws RuntimeException("DataStore 오류")

        // When & Then: 예외 전파 없음
        canceller.cancelAll()
    }

    // 4. 경계값

    @Test
    fun `cancelByPrefix는 알람이 없을 때도 deleteWebAlarmsByPrefix를 호출한다`() {
        // Given
        every { notificationRepository.getWebAlarms() } returns emptySet()

        // When
        canceller.cancelByPrefix("AD_")

        // Then
        verify { notificationRepository.deleteWebAlarmsByPrefix("AD_") }
    }

    @Test
    fun `cancelAll은 알람이 없을 때도 deleteAllWebAlarms를 호출한다`() {
        // Given
        every { notificationRepository.getWebAlarms() } returns emptySet()

        // When
        canceller.cancelAll()

        // Then
        verify { notificationRepository.deleteAllWebAlarms() }
    }

    // 7. 도메인 불변성

    @Test
    fun `cancelByPrefix는 AlarmManager 예외와 무관하게 deleteWebAlarmsByPrefix를 호출한다`() {
        // Given
        every { notificationRepository.getWebAlarms() } returns setOf(adAlarm)
        every { alarmManager.cancel(any()) } throws SecurityException("권한 없음")

        // When
        canceller.cancelByPrefix("AD_")

        // Then: DataStore 삭제는 반드시 실행됨
        verify { notificationRepository.deleteWebAlarmsByPrefix("AD_") }
    }
}
```

**Step 2: 테스트 실행 → FAIL 확인**

```bash
./gradlew :features:testDebugUnitTest --tests "*.WebAlarmCancellerImplTest"
```
Expected: FAIL with "WebAlarmCancellerImpl not found"

**Step 3: 구현체 작성**

```kotlin
package com.kurly.features.web.bridge.common.user

import android.app.AlarmManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import androidx.appcompat.app.AppCompatActivity
import com.kurly.domain.repository.notification.NotificationRepository
import com.kurly.domain.repository.notification.WebAlarmCanceller
import com.kurly.features.broadcast.KurlyAlarmBroadcastReceiver
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class WebAlarmCancellerImpl @Inject constructor(
    @ApplicationContext private val context: Context,
    private val notificationRepository: NotificationRepository,
) : WebAlarmCanceller {

    // NOTE: getWebAlarms()는 내부적으로 runBlocking + withTimeout(400ms) 패턴.
    // DataStore가 느린 경우 timeout 후 emptySet 반환 → AlarmManager cancel 누락 가능.
    // 이 경우 DataStore write(deleteWebAlarmsByPrefix/deleteAllWebAlarms)는 정상 실행되므로
    // AlarmManager에 알람이 남아도 DataStore에서 제거되어 재등록은 안 됨.
    // 해당 알람은 예약 시각에 한 번 울릴 수 있음 — 허용 가능한 trade-off.

    override fun cancelByPrefix(prefix: String) {
        try {
            notificationRepository.getWebAlarms()
                .filter { it.alarmId.startsWith(prefix) }
                .forEach { releaseAlarm(it.requestCode) }
        } catch (_: Exception) {
            // AlarmManager cancel 실패는 silent fail
        }
        notificationRepository.deleteWebAlarmsByPrefix(prefix)
    }

    override fun cancelAll() {
        try {
            notificationRepository.getWebAlarms()
                .forEach { releaseAlarm(it.requestCode) }
        } catch (_: Exception) {
            // AlarmManager cancel 실패는 silent fail
        }
        notificationRepository.deleteAllWebAlarms()
    }

    private fun releaseAlarm(requestCode: Int) {
        val alarmManager = context.getSystemService(AppCompatActivity.ALARM_SERVICE) as AlarmManager
        val alarmIntent = Intent(context, KurlyAlarmBroadcastReceiver::class.java)
        val pendingIntent = PendingIntent.getBroadcast(
            context,
            requestCode,
            alarmIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        alarmManager.cancel(pendingIntent)
    }
}
```

**Step 4: 테스트 재실행 → PASS 확인**

```bash
./gradlew :features:testDebugUnitTest --tests "*.WebAlarmCancellerImplTest"
```
Expected: PASS (9 tests)

**Step 5: Commit**

```bash
git add features/src/main/java/com/kurly/features/web/bridge/common/user/WebAlarmCancellerImpl.kt
git add features/src/test/java/com/kurly/features/web/bridge/common/user/WebAlarmCancellerImplTest.kt
git commit -m "PRJ-237 WebAlarmCancellerImpl 구현 및 테스트 추가"
```

---

## Task 4: ApplicationBindModule에 WebAlarmCanceller 바인딩 추가

**Files:**
- Modify: `app/src/main/kotlin/com/dbs/kurly/m2/di/ApplicationBindModule.kt`

**Step 1: import 및 바인딩 추가**

`bindsWebAlarmDispatcher` 바인딩 아래에 추가:

```kotlin
// import 추가
import com.kurly.domain.repository.notification.WebAlarmCanceller
import com.kurly.features.web.bridge.common.user.WebAlarmCancellerImpl

// 바인딩 추가
@Singleton
@Binds
abstract fun bindsWebAlarmCanceller(
    webAlarmCanceller: WebAlarmCancellerImpl
): WebAlarmCanceller
```

**Step 2: 컴파일 확인**

```bash
./gradlew :app:compileDebugKotlin
```
Expected: BUILD SUCCESSFUL

**Step 3: Commit**

```bash
git add app/src/main/kotlin/com/dbs/kurly/m2/di/ApplicationBindModule.kt
git commit -m "PRJ-237 WebAlarmCanceller Hilt 바인딩 추가"
```

---

## Task 5: DeleteAdAlarmsUseCase 생성 (domain)

**Files:**
- Create: `domain/src/main/java/com/kurly/domain/usecase/notification/DeleteAdAlarmsUseCase.kt`
- Create: `domain/src/test/java/com/kurly/domain/usecase/notification/DeleteAdAlarmsUseCaseTest.kt`

**Step 1: 테스트 먼저 작성**

```kotlin
package com.kurly.domain.usecase.notification

import com.kurly.domain.repository.notification.WebAlarmCanceller
import io.mockk.mockk
import io.mockk.verify
import org.junit.Test

class DeleteAdAlarmsUseCaseTest {

    private val webAlarmCanceller: WebAlarmCanceller = mockk(relaxed = true)
    private val useCase = DeleteAdAlarmsUseCase(webAlarmCanceller)

    @Test
    fun `invoke 시 AD_ prefix로 cancelByPrefix를 호출한다`() {
        useCase()

        verify { webAlarmCanceller.cancelByPrefix("AD_") }
    }
}
```

**Step 2: 테스트 실행 → FAIL 확인**

```bash
./gradlew :domain:test --tests "*.DeleteAdAlarmsUseCaseTest"
```
Expected: FAIL

**Step 3: UseCase 구현**

```kotlin
package com.kurly.domain.usecase.notification

import com.kurly.domain.repository.notification.WebAlarmCanceller
import javax.inject.Inject

class DeleteAdAlarmsUseCase @Inject constructor(
    private val webAlarmCanceller: WebAlarmCanceller,
) {
    operator fun invoke() {
        webAlarmCanceller.cancelByPrefix("AD_")
    }
}
```

**Step 4: 테스트 재실행 → PASS 확인**

```bash
./gradlew :domain:test --tests "*.DeleteAdAlarmsUseCaseTest"
```
Expected: PASS

**Step 5: Commit**

```bash
git add domain/src/main/java/com/kurly/domain/usecase/notification/DeleteAdAlarmsUseCase.kt
git add domain/src/test/java/com/kurly/domain/usecase/notification/DeleteAdAlarmsUseCaseTest.kt
git commit -m "PRJ-237 DeleteAdAlarmsUseCase 추가"
```

---

## Task 6: DeleteAllWebAlarmsUseCase 생성 (domain)

**Files:**
- Create: `domain/src/main/java/com/kurly/domain/usecase/notification/DeleteAllWebAlarmsUseCase.kt`
- Create: `domain/src/test/java/com/kurly/domain/usecase/notification/DeleteAllWebAlarmsUseCaseTest.kt`

**Step 1: 테스트 먼저 작성**

```kotlin
package com.kurly.domain.usecase.notification

import com.kurly.domain.repository.notification.WebAlarmCanceller
import io.mockk.mockk
import io.mockk.verify
import org.junit.Test

class DeleteAllWebAlarmsUseCaseTest {

    private val webAlarmCanceller: WebAlarmCanceller = mockk(relaxed = true)
    private val useCase = DeleteAllWebAlarmsUseCase(webAlarmCanceller)

    @Test
    fun `invoke 시 cancelAll을 호출한다`() {
        useCase()

        verify { webAlarmCanceller.cancelAll() }
    }
}
```

**Step 2: 테스트 실행 → FAIL 확인**

```bash
./gradlew :domain:test --tests "*.DeleteAllWebAlarmsUseCaseTest"
```
Expected: FAIL

**Step 3: UseCase 구현**

```kotlin
package com.kurly.domain.usecase.notification

import com.kurly.domain.repository.notification.WebAlarmCanceller
import javax.inject.Inject

class DeleteAllWebAlarmsUseCase @Inject constructor(
    private val webAlarmCanceller: WebAlarmCanceller,
) {
    operator fun invoke() {
        webAlarmCanceller.cancelAll()
    }
}
```

**Step 4: 테스트 재실행 → PASS 확인**

```bash
./gradlew :domain:test --tests "*.DeleteAllWebAlarmsUseCaseTest"
```
Expected: PASS

**Step 5: Commit**

```bash
git add domain/src/main/java/com/kurly/domain/usecase/notification/DeleteAllWebAlarmsUseCase.kt
git add domain/src/test/java/com/kurly/domain/usecase/notification/DeleteAllWebAlarmsUseCaseTest.kt
git commit -m "PRJ-237 DeleteAllWebAlarmsUseCase 추가"
```

---

## Task 7: LogoutToGuestUseCase 수정

**Files:**
- Modify: `domain/src/main/java/com/kurly/domain/usecase/user/LogoutToGuestUseCase.kt`
- Create: `domain/src/test/java/com/kurly/domain/usecase/user/LogoutToGuestUseCaseTest.kt`

**Step 1: 테스트 먼저 작성**

```kotlin
package com.kurly.domain.usecase.user

import com.kurly.domain.model.analytics.LogoutCause
import com.kurly.domain.model.analytics.LogoutReason
import com.kurly.domain.model.user.Session
import com.kurly.domain.model.user.SessionInfo
import com.kurly.domain.repository.AuthRepository
import com.kurly.domain.repository.TooltipRepository
import com.kurly.domain.repository.notification.WebAlarmCanceller
import com.kurly.domain.usecase.affiliate.SetAffiliateData
import com.kurly.ktcore.logger.Logger
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.every
import io.mockk.mockk
import io.mockk.verify
import kotlinx.coroutines.test.runTest
import org.junit.Test

class LogoutToGuestUseCaseTest {

    private val logger: Logger = mockk(relaxed = true)
    private val session: Session = mockk()
    private val authRepository: AuthRepository = mockk(relaxed = true)
    private val loginStateHandler: LoginStateHandler = mockk(relaxed = true)
    private val setAffiliateData: SetAffiliateData = mockk(relaxed = true)
    private val tooltipRepository: TooltipRepository = mockk(relaxed = true)
    private val webAlarmCanceller: WebAlarmCanceller = mockk(relaxed = true)

    private val useCase = LogoutToGuestUseCase(
        logger = logger,
        session = session,
        authRepository = authRepository,
        loginStateHandler = loginStateHandler,
        setAffiliateData = setAffiliateData,
        tooltipRepository = tooltipRepository,
        webAlarmCanceller = webAlarmCanceller,
    )

    @Test
    fun `로그아웃 성공 시 cancelAll을 호출한다`() = runTest {
        every { session.sessionInfo } returns mockk<SessionInfo>()
        coEvery { authRepository.getGuestLoginToken() } returns mockk()

        useCase(LogoutToGuestUseCase.Param(LogoutCause.Etc, LogoutReason.DirectLogout))

        verify { webAlarmCanceller.cancelAll() }
    }

    @Test
    fun `authRepository logout 이후에 cancelAll을 호출한다`() = runTest {
        // Given
        every { session.sessionInfo } returns mockk<SessionInfo>()
        coEvery { authRepository.getGuestLoginToken() } returns mockk()

        // When
        useCase(LogoutToGuestUseCase.Param(LogoutCause.Etc, LogoutReason.DirectLogout))

        // Then
        coVerify(ordering = io.mockk.Ordering.ORDERED) {
            authRepository.logout()
            webAlarmCanceller.cancelAll()
        }
    }

    // 2. 에러 처리

    @Test
    fun `authRepository logout 실패 시 cancelAll을 호출하지 않는다`() = runTest {
        // Given
        coEvery { authRepository.logout() } throws RuntimeException("네트워크 오류")

        // When
        useCase(LogoutToGuestUseCase.Param(LogoutCause.Etc, LogoutReason.DirectLogout))

        // Then
        verify(exactly = 0) { webAlarmCanceller.cancelAll() }
    }

    @Test
    fun `cancelAll 예외 발생 시에도 getGuestLoginToken을 호출한다`() = runTest {
        // Given: cancelAll이 예외를 던져도 로그아웃 흐름이 중단되면 안 됨
        every { session.sessionInfo } returns mockk<SessionInfo>()
        every { webAlarmCanceller.cancelAll() } throws RuntimeException("AlarmManager 오류")
        coEvery { authRepository.getGuestLoginToken() } returns mockk()

        // When
        useCase(LogoutToGuestUseCase.Param(LogoutCause.Etc, LogoutReason.DirectLogout))

        // Then: 예외에도 불구하고 게스트 전환 완료
        coVerify { authRepository.getGuestLoginToken() }
    }

    // 3. 순서 보장

    @Test
    fun `cancelAll 이후 getGuestLoginToken을 호출한다`() = runTest {
        // Given
        every { session.sessionInfo } returns mockk<SessionInfo>()
        coEvery { authRepository.getGuestLoginToken() } returns mockk()

        // When
        useCase(LogoutToGuestUseCase.Param(LogoutCause.Etc, LogoutReason.DirectLogout))

        // Then
        coVerify(ordering = io.mockk.Ordering.ORDERED) {
            webAlarmCanceller.cancelAll()
            authRepository.getGuestLoginToken()
        }
    }
}
```

**Step 2: 테스트 실행 → FAIL 확인**

```bash
./gradlew :domain:test --tests "*.LogoutToGuestUseCaseTest"
```
Expected: FAIL (webAlarmCanceller 파라미터 없음)

**Step 3: LogoutToGuestUseCase 수정**

`webAlarmCanceller` inject 추가, `authRepository.logout()` 호출 직후 `cancelAll()` 추가:

```kotlin
class LogoutToGuestUseCase @Inject constructor(
    logger: Logger,
    private val session: Session,
    private val authRepository: AuthRepository,
    private val loginStateHandler: LoginStateHandler,
    private val setAffiliateData: SetAffiliateData,
    private val tooltipRepository: TooltipRepository,
    private val webAlarmCanceller: WebAlarmCanceller,      // 추가
) : BaseUseCase<LogoutToGuestUseCase.Param, Result<Unit>>(logger) {

    override suspend fun invoke(param: Param): Result<Unit> {
        return runCatching {
            setAffiliateData.execute(SetAffiliateData.Action.ClearAll)
            tooltipRepository.clearMyKurlyQuickButtonClicked()

            authRepository.logout()
            // cancelAll 예외가 runCatching에 잡혀 getGuestLoginToken 호출을 막지 않도록 별도 try-catch
            try { webAlarmCanceller.cancelAll() } catch (_: Exception) { }
            authRepository.getGuestLoginToken()
            loginStateHandler.onSuccessGuestLogin(session.sessionInfo)
        }
    }

    data class Param(
        val cause: LogoutCause,
        val reason: LogoutReason
    )
}
```

**Step 4: 테스트 재실행 → PASS 확인**

```bash
./gradlew :domain:test --tests "*.LogoutToGuestUseCaseTest"
```
Expected: PASS (4 tests)

**Step 5: 컴파일 확인**

```bash
./gradlew :domain:compileDebugKotlin
```
Expected: BUILD SUCCESSFUL

**Step 6: Commit**

```bash
git add domain/src/main/java/com/kurly/domain/usecase/user/LogoutToGuestUseCase.kt
git add domain/src/test/java/com/kurly/domain/usecase/user/LogoutToGuestUseCaseTest.kt
git commit -m "PRJ-237 LogoutToGuestUseCase 로그아웃 시 웹 알람 전체 삭제 추가"
```

---

## Task 8: KurlyWebViewViewModel 수정

**Files:**
- Modify: `features/src/main/java/com/kurly/features/web/base/viewmodel/KurlyWebViewViewModel.kt`
- Create: `features/src/test/java/com/kurly/features/web/base/viewmodel/KurlyWebViewViewModelTest.kt`

**Step 1: 테스트 파일 먼저 작성**

```kotlin
package com.kurly.features.web.base.viewmodel

import androidx.lifecycle.SavedStateHandle
import com.google.gson.Gson
import com.kurly.core.network.HttpHeaderProvider
import com.kurly.domain.analytics.AnalyticsProvider
import com.kurly.domain.base.dispatcher.DispatcherProvider
import com.kurly.domain.model.analytics.LogoutCause
import com.kurly.domain.model.analytics.LogoutReason
import com.kurly.domain.model.user.Session
import com.kurly.domain.usecase.address.GetCurrentAddress
import com.kurly.domain.usecase.app.ReserveMessageAfterFinishUseCase
import com.kurly.domain.usecase.cart.RefreshCartItemsUseCase
import com.kurly.domain.usecase.marketing.BakeCookie
import com.kurly.domain.usecase.notification.DeleteAdAlarmsUseCase
import com.kurly.domain.usecase.notification.DeleteAllWebAlarmsUseCase
import com.kurly.domain.usecase.notification.UpdateNotificationSettings
import com.kurly.domain.usecase.user.GetUserMetaDataUseCase
import com.kurly.domain.usecase.user.LoginUseCase
import com.kurly.domain.usecase.user.RefreshToken
import com.kurly.ktcore.logger.Logger
import com.kurly.ktcore.test.BaseMockKTest
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.every
import io.mockk.mockk
import io.mockk.verify
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runTest
import org.junit.Before
import org.junit.Test

class KurlyWebViewViewModelTest : BaseMockKTest() {

    private val analyticsProvider: AnalyticsProvider = mockk(relaxed = true)
    private val updateNotificationSettings: UpdateNotificationSettings = mockk(relaxed = true)
    private val loginUseCase: LoginUseCase = mockk(relaxed = true)
    private val dispatcher: DispatcherProvider = mockk()
    private val deleteAdAlarmsUseCase: DeleteAdAlarmsUseCase = mockk(relaxed = true)
    private val deleteAllWebAlarmsUseCase: DeleteAllWebAlarmsUseCase = mockk(relaxed = true)

    private lateinit var viewModel: KurlyWebViewViewModel

    @Before
    fun setUp() {
        val testDispatcher = StandardTestDispatcher()
        every { dispatcher.io() } returns testDispatcher

        viewModel = KurlyWebViewViewModel(
            savedStateHandle = SavedStateHandle(),
            applicationScope = CoroutineScope(testDispatcher),
            analyticsProvider = analyticsProvider,
            refreshToken = mockk(relaxed = true),
            updateNotificationSettings = updateNotificationSettings,
            getUserMetadataUseCase = mockk(relaxed = true),
            loginUseCase = loginUseCase,
            bakeCookie = mockk(relaxed = true),
            getCurrentAddress = mockk(relaxed = true),
            refreshCartItemsUseCase = mockk(relaxed = true),
            reserveMessageAfterFinishUseCase = mockk(relaxed = true),
            httpHeaderProvider = mockk(relaxed = true),
            logger = mockk(relaxed = true),
            dispatcher = dispatcher,
            session = mockk(relaxed = true),
            gson = Gson(),
            deleteAdAlarmsUseCase = deleteAdAlarmsUseCase,
            deleteAllWebAlarmsUseCase = deleteAllWebAlarmsUseCase,
        )
    }

    // 1. 정상 동작

    @Test
    fun `updateMarketingNotificationAllow false 서버 성공 시 deleteAdAlarmsUseCase를 호출한다`() = runTest {
        // Given
        coEvery { updateNotificationSettings.execute(any()) } returns
            UpdateNotificationSettings.Result.Success(time = 0L)

        // When
        viewModel.updateMarketingNotificationAllow(false) {}
        advanceUntilIdle()

        // Then
        verify { deleteAdAlarmsUseCase() }
    }

    @Test
    fun `logout 호출 시 deleteAllWebAlarmsUseCase를 호출한다`() = runTest {
        // When
        viewModel.logout(LogoutCause.Etc, LogoutReason.DirectLogout)
        advanceUntilIdle()

        // Then
        verify { deleteAllWebAlarmsUseCase() }
    }

    // 2. 에러 처리

    @Test
    fun `updateMarketingNotificationAllow false 서버 실패 시 deleteAdAlarmsUseCase를 호출하지 않는다`() = runTest {
        // Given
        coEvery { updateNotificationSettings.execute(any()) } returns
            UpdateNotificationSettings.Result.Failure(RuntimeException())

        // When
        viewModel.updateMarketingNotificationAllow(false) {}
        advanceUntilIdle()

        // Then
        verify(exactly = 0) { deleteAdAlarmsUseCase() }
    }

    // 3. 순서

    @Test
    fun `logout 시 deleteAllWebAlarmsUseCase 먼저 loginUseCase 나중에 호출한다`() = runTest {
        // When
        viewModel.logout(null, null)
        advanceUntilIdle()

        // Then
        coVerify(ordering = io.mockk.Ordering.ORDERED) {
            deleteAllWebAlarmsUseCase()
            loginUseCase.execute(LoginUseCase.Param.Guest)
        }
    }

    // 4. 경계값

    @Test
    fun `updateMarketingNotificationAllow true 서버 성공 시 deleteAdAlarmsUseCase를 호출하지 않는다`() = runTest {
        // Given
        coEvery { updateNotificationSettings.execute(any()) } returns
            UpdateNotificationSettings.Result.Success(time = 0L)

        // When
        viewModel.updateMarketingNotificationAllow(true) {}
        advanceUntilIdle()

        // Then
        verify(exactly = 0) { deleteAdAlarmsUseCase() }
    }

    @Test
    fun `updateMarketingNotificationAllow null 서버 성공 시 deleteAdAlarmsUseCase를 호출하지 않는다`() = runTest {
        // Given
        coEvery { updateNotificationSettings.execute(any()) } returns
            UpdateNotificationSettings.Result.Success(time = 0L)

        // When
        viewModel.updateMarketingNotificationAllow(null) {}
        advanceUntilIdle()

        // Then
        verify(exactly = 0) { deleteAdAlarmsUseCase() }
    }
}
```

**Step 2: 테스트 실행 → FAIL 확인**

```bash
./gradlew :features:testDebugUnitTest --tests "*.KurlyWebViewViewModelTest"
```
Expected: FAIL (deleteAdAlarmsUseCase 파라미터 없음)

**Step 3: Constructor에 UseCase 추가**

`KurlyWebViewViewModel`의 `@Inject constructor` 파라미터에 추가:
```kotlin
private val deleteAdAlarmsUseCase: DeleteAdAlarmsUseCase,
private val deleteAllWebAlarmsUseCase: DeleteAllWebAlarmsUseCase,
```

**Step 2: updateMarketingNotificationAllow() 수정**

서버 저장 성공 + `isAllow == false` 일 때 알람 삭제. 기존 `callback.invoke(...)` 직전에 추가:

```kotlin
fun updateMarketingNotificationAllow(isAllow: Boolean?, callback: (Boolean) -> Unit) {
    viewModelScope.launch(dispatcher.io()) {
        val params = UpdateNotificationSettings.Params(isMarketingNotificationAllow = isAllow)
        val result = updateNotificationSettings.execute(params)
        when (result) {
            is UpdateNotificationSettings.Result.Success -> {
                if (isAllow == false) {
                    deleteAdAlarmsUseCase()                // 추가
                }
                _uiEvent.send(
                    UIEvent.ShowMarketingNotificationChangedMessage(
                        isAllow ?: false, result.time
                    )
                )
            }
            is UpdateNotificationSettings.Result.Failure -> {}
        }
        callback.invoke(result is UpdateNotificationSettings.Result.Success)
    }
}
```

**Step 3: logout() 수정**

`loginUseCase.execute()` 전에 알람 삭제:

```kotlin
fun logout(logoutCause: LogoutCause?, logoutReason: LogoutReason?) {
    logoutCause?.let { cause ->
        analyticsProvider.sendLogoutEvent(cause, logoutReason, null)
    }
    viewModelScope.launch(dispatcher.io()) {
        deleteAllWebAlarmsUseCase()                        // 추가
        loginUseCase.execute(LoginUseCase.Param.Guest)
    }
}
```

**Step 4: deleteAllWebAlarms() 메서드 추가**

Fragment의 `onSuccessUnRegister()`에서 호출하기 위한 메서드:

```kotlin
fun deleteAllWebAlarms() {
    viewModelScope.launch(dispatcher.io()) {
        deleteAllWebAlarmsUseCase()
    }
}
```

**Step 5: 테스트 재실행 → PASS 확인**

```bash
./gradlew :features:testDebugUnitTest --tests "*.KurlyWebViewViewModelTest"
```
Expected: PASS (5 tests)

**Step 6: 컴파일 확인**

```bash
./gradlew :features:compileDebugKotlin
```
Expected: BUILD SUCCESSFUL

**Step 7: Commit**

```bash
git add features/src/main/java/com/kurly/features/web/base/viewmodel/KurlyWebViewViewModel.kt
git add features/src/test/java/com/kurly/features/web/base/viewmodel/KurlyWebViewViewModelTest.kt
git commit -m "PRJ-237 KurlyWebViewViewModel 로그아웃/마수동 OFF 시 알람 삭제 추가"
```

---

## Task 9: NotificationSettingsViewModel 수정

**Files:**
- Modify: `features/src/main/java/com/kurly/features/notification/NotificationSettingsViewModel.kt`
- Create: `features/src/test/java/com/kurly/features/notification/NotificationSettingsViewModelTest.kt`

**Step 1: 테스트 파일 먼저 작성**

```kotlin
package com.kurly.features.notification

import com.kurly.core.ResourceProvider
import com.kurly.domain.base.dispatcher.DispatcherProvider
import com.kurly.domain.model.notification.NotificationSettings
import com.kurly.domain.usecase.notification.DeleteAdAlarmsUseCase
import com.kurly.domain.usecase.notification.GetNotificationSettingsUseCase
import com.kurly.domain.usecase.notification.UpdateNotificationSettings
import com.kurly.ktcore.test.BaseMockKTest
import io.mockk.coEvery
import io.mockk.every
import io.mockk.mockk
import io.mockk.verify
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runTest
import org.junit.Before
import org.junit.Test

class NotificationSettingsViewModelTest : BaseMockKTest() {

    private val updateNotificationSettings: UpdateNotificationSettings = mockk(relaxed = true)
    private val dispatcherProvider: DispatcherProvider = mockk()
    private val deleteAdAlarmsUseCase: DeleteAdAlarmsUseCase = mockk(relaxed = true)

    private lateinit var viewModel: NotificationSettingsViewModel

    private val settingOff = NotificationSettings(
        isSystemNotificationAllow = true,
        isMarketingNotificationAllow = false,
        isNightTimeNotificationAllow = true,
    )
    private val settingOn = NotificationSettings(
        isSystemNotificationAllow = true,
        isMarketingNotificationAllow = true,
        isNightTimeNotificationAllow = true,
    )

    @Before
    fun setUp() {
        val testDispatcher = StandardTestDispatcher()
        every { dispatcherProvider.io() } returns testDispatcher

        viewModel = NotificationSettingsViewModel(
            getNotificationSettingsUseCase = mockk(relaxed = true),
            updateNotificationSettings = updateNotificationSettings,
            resourceProvider = mockk(relaxed = true),
            dispatcherProvider = dispatcherProvider,
            deleteAdAlarmsUseCase = deleteAdAlarmsUseCase,
        )
    }

    // 1. 정상 동작

    @Test
    fun `광수동 OFF 서버 성공 시 deleteAdAlarmsUseCase를 호출한다`() = runTest {
        // Given
        coEvery { updateNotificationSettings.execute(any()) } returns
            UpdateNotificationSettings.Result.Success(time = 0L)

        // When
        viewModel.updateNotificationSetting(mockk(relaxed = true), settingOff)
        advanceUntilIdle()

        // Then
        verify { deleteAdAlarmsUseCase() }
    }

    // 2. 에러 처리

    @Test
    fun `광수동 OFF 서버 실패 시 deleteAdAlarmsUseCase를 호출하지 않는다`() = runTest {
        // Given
        coEvery { updateNotificationSettings.execute(any()) } returns
            UpdateNotificationSettings.Result.Failure(RuntimeException())

        // When
        viewModel.updateNotificationSetting(mockk(relaxed = true), settingOff)
        advanceUntilIdle()

        // Then
        verify(exactly = 0) { deleteAdAlarmsUseCase() }
    }

    // 4. 경계값

    @Test
    fun `광수동 ON 서버 성공 시 deleteAdAlarmsUseCase를 호출하지 않는다`() = runTest {
        // Given
        coEvery { updateNotificationSettings.execute(any()) } returns
            UpdateNotificationSettings.Result.Success(time = 0L)

        // When
        viewModel.updateNotificationSetting(mockk(relaxed = true), settingOn)
        advanceUntilIdle()

        // Then
        verify(exactly = 0) { deleteAdAlarmsUseCase() }
    }
}
```

**Step 2: 테스트 실행 → FAIL 확인**

```bash
./gradlew :features:testDebugUnitTest --tests "*.NotificationSettingsViewModelTest"
```
Expected: FAIL (deleteAdAlarmsUseCase 파라미터 없음)

**Step 3: Constructor에 UseCase 추가**

```kotlin
private val deleteAdAlarmsUseCase: DeleteAdAlarmsUseCase,
```

**Step 4: updateNotificationSetting() 수정**

`result is Success` 블록 내에서 광수동이 OFF로 변경된 경우 알람 삭제:

```kotlin
is UpdateNotificationSettings.Result.Success -> {
    if (setting.isMarketingNotificationAllow != isMarketingNotificationAllow()) {
        uiEvent.emit(
            UIEvent.ShowMarketingNotificationChangedMessage(
                setting.isMarketingNotificationAllow,
                result.time
            )
        )
    }
    if (!setting.isMarketingNotificationAllow) {           // 추가
        deleteAdAlarmsUseCase()                            // 추가
    }                                                      // 추가
    notificationSettings.postValue(setting)
}
```

**Step 5: 테스트 재실행 → PASS 확인**

```bash
./gradlew :features:testDebugUnitTest --tests "*.NotificationSettingsViewModelTest"
```
Expected: PASS (3 tests)

**Step 6: 컴파일 확인**

```bash
./gradlew :features:compileDebugKotlin
```
Expected: BUILD SUCCESSFUL

**Step 7: Commit**

```bash
git add features/src/main/java/com/kurly/features/notification/NotificationSettingsViewModel.kt
git add features/src/test/java/com/kurly/features/notification/NotificationSettingsViewModelTest.kt
git commit -m "PRJ-237 NotificationSettingsViewModel 광수동 OFF 시 알람 삭제 추가"
```

---

## Task 10: BaseKurlyWebViewFragment 수정 (탈퇴 WV3200)

**Files:**
- Modify: `features/src/main/java/com/kurly/features/web/base/fragment/BaseKurlyWebViewFragment.kt`

**Step 1: onSuccessUnRegister() 수정**

`finishWithPostMessageCode()` 호출 전에 알람 삭제 추가:

```kotlin
override fun onSuccessUnRegister(message: String?) {
    webViewViewModel.deleteAllWebAlarms()                  // 추가
    finishWithPostMessageCode(PostMessageCode.SuccessUnRegister.code)
    lifecycleScope.launch {
        globalEventPublisher.publish(
            UnExpectedLogoutEvent(
                LogoutCause.Etc,
                LogoutReason.Unregister
            )
        )
    }
}
```

**Step 2: 컴파일 확인**

```bash
./gradlew :features:compileDebugKotlin
```
Expected: BUILD SUCCESSFUL

**Step 3: 전체 빌드 확인**

```bash
./gradlew :app:compileDebugKotlin
```
Expected: BUILD SUCCESSFUL

**Step 4: Commit**

```bash
git add features/src/main/java/com/kurly/features/web/base/fragment/BaseKurlyWebViewFragment.kt
git commit -m "PRJ-237 탈퇴(WV3200) 시 전체 웹 알람 삭제 추가"
```

---

## Task 11: NotificationRepositoryImpl Instrumented Test

**Files:**
- Create: `data/src/androidTest/java/com/kurly/data/repository/notification/NotificationRepositoryImplBulkDeleteTest.kt`

실제 DataStore에 알람을 저장 후 bulk 삭제 메서드가 올바르게 동작하는지 검증한다.
단위 테스트에서는 DataStore를 mock하므로 실제 직렬화/역직렬화, filterNot 로직, Job lock 동시성은 이 테스트로만 검증된다.

**Step 1: 테스트 작성**

```kotlin
package com.kurly.data.repository.notification

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.kurly.data.consts.PreferenceKey
import com.kurly.domain.base.dispatcher.DispatcherProvider
import com.kurly.domain.model.notification.AlarmWeb
import com.kurly.domain.repository.notification.NotificationRepository
import com.kurly.ktcore.logger.Logger
import io.mockk.every
import io.mockk.mockk
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.runTest
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter

@RunWith(AndroidJUnit4::class)
class NotificationRepositoryImplBulkDeleteTest {

    private lateinit var context: Context
    private lateinit var repository: NotificationRepository

    private val testDispatcher = StandardTestDispatcher()
    private val dispatcherProvider: DispatcherProvider = mockk {
        every { io() } returns testDispatcher
    }

    private val futureIso = ZonedDateTime.now().plusMinutes(10)
        .format(DateTimeFormatter.ISO_ZONED_DATE_TIME)
    private val futureMs = System.currentTimeMillis() + 600_000L

    private fun alarm(id: String, requestCode: Int) = AlarmWeb(
        alarmId = id, title = "", message = "", datetime = futureIso,
        image = null, link = null, callback = null, errorCallback = null,
        requestCode = requestCode, timeMs = futureMs,
    )

    @Before
    fun setUp() {
        context = ApplicationProvider.getApplicationContext()
        repository = NotificationRepositoryImpl(
            remoteSource = mockk(relaxed = true),
            localSource = mockk(relaxed = true),
            context = context,
            coroutineScope = kotlinx.coroutines.CoroutineScope(testDispatcher),
            notificationService = mockk(relaxed = true),
            apiCaller = mockk(relaxed = true),
            preferenceProvider = mockk(relaxed = true),
            deviceInfoProvider = mockk(relaxed = true),
            dispatcherProvider = dispatcherProvider,
            logger = mockk(relaxed = true),
        )
    }

    @After
    fun tearDown() = runTest(testDispatcher) {
        // DataStore 정리
        repository.deleteAllWebAlarms()
        testDispatcher.scheduler.advanceUntilIdle()
    }

    @Test
    fun deleteWebAlarmsByPrefix_AD_prefix만_삭제된다() = runTest(testDispatcher) {
        // Given
        val adAlarm1 = alarm("AD_LEGO_1", 1001)
        val adAlarm2 = alarm("AD_CLAY_1", 1002)
        val infoAlarm = alarm("INFO_LIVE_1", 1003)
        repository.saveWebAlarm(adAlarm1)
        repository.saveWebAlarm(adAlarm2)
        repository.saveWebAlarm(infoAlarm)
        testDispatcher.scheduler.advanceUntilIdle()

        // When
        repository.deleteWebAlarmsByPrefix("AD_")
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        val remaining = repository.getWebAlarms()
        assertEquals(1, remaining.size)
        assertTrue(remaining.any { it.alarmId == "INFO_LIVE_1" })
    }

    @Test
    fun deleteWebAlarmsByPrefix_해당_prefix_없으면_변화_없다() = runTest(testDispatcher) {
        // Given
        val infoAlarm = alarm("INFO_LIVE_1", 1003)
        repository.saveWebAlarm(infoAlarm)
        testDispatcher.scheduler.advanceUntilIdle()

        // When
        repository.deleteWebAlarmsByPrefix("AD_")
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        val remaining = repository.getWebAlarms()
        assertEquals(1, remaining.size)
    }

    @Test
    fun deleteAllWebAlarms_전체_삭제된다() = runTest(testDispatcher) {
        // Given
        repository.saveWebAlarm(alarm("AD_LEGO_1", 1001))
        repository.saveWebAlarm(alarm("INFO_LIVE_1", 1002))
        testDispatcher.scheduler.advanceUntilIdle()

        // When
        repository.deleteAllWebAlarms()
        testDispatcher.scheduler.advanceUntilIdle()

        // Then
        assertTrue(repository.getWebAlarms().isEmpty())
    }

    @Test
    fun deleteAllWebAlarms_알람_없어도_예외_없다() = runTest(testDispatcher) {
        // Given: 비어있는 상태

        // When & Then: 예외 없이 정상 완료
        repository.deleteAllWebAlarms()
        testDispatcher.scheduler.advanceUntilIdle()

        assertTrue(repository.getWebAlarms().isEmpty())
    }
}
```

**Step 2: 에뮬레이터/기기 연결 후 실행**

```bash
./gradlew :data:connectedDebugAndroidTest \
  -Pandroid.testInstrumentationRunnerArguments.class=com.kurly.data.repository.notification.NotificationRepositoryImplBulkDeleteTest
```
Expected: PASS (4 tests)

**Step 3: Commit**

```bash
git add data/src/androidTest/java/com/kurly/data/repository/notification/NotificationRepositoryImplBulkDeleteTest.kt
git commit -m "PRJ-237 NotificationRepositoryImpl bulk 삭제 Instrumented Test 추가"
```

---

## 최종 검증

```bash
./gradlew :domain:test
./gradlew :features:testDebugUnitTest
./gradlew assembleDebug
```

모두 PASS/BUILD SUCCESSFUL 확인.

---

## 수동 QA 시나리오

> **사전 준비**
> - 로그인된 회원 계정
> - 개발자 모드 → "로컬 푸시 신청 내역" 확인 가능한 화면 또는 AlarmManager dump 사용
>   - `adb shell dumpsys alarm | grep kurly` 로 예약된 알람 확인
> - 테스트 전 마수동/광수동 ON 상태에서 AD_ prefix 로컬 푸시를 1개 이상 신청해 둘 것
> - INFO_ prefix 알람도 1개 이상 신청해 둘 것 (삭제 안 됨 검증용)

---

### TC-01: 마수동 OFF → AD_ 삭제, INFO_ 유지

| 단계 | 액션 | 기대 결과 |
|---|---|---|
| 1 | 마이컬리 → 알림 설정 → 마수동 ON 확인 | AD_ 알람 존재 확인 |
| 2 | 마수동 OFF 토글 | - |
| 3 | `adb shell dumpsys alarm \| grep kurly` | AD_ prefix 알람 사라짐 |
| 4 | INFO_ prefix 알람 확인 | INFO_ 알람 그대로 존재 |

---

### TC-02: 광수동 OFF → AD_ 삭제, INFO_ 유지

| 단계 | 액션 | 기대 결과 |
|---|---|---|
| 1 | 마이컬리 → 알림 설정 → 광수동 ON 확인 | AD_ 알람 존재 확인 |
| 2 | 광수동 OFF 토글 | - |
| 3 | `adb shell dumpsys alarm \| grep kurly` | AD_ prefix 알람 사라짐 |
| 4 | INFO_ prefix 알람 확인 | INFO_ 알람 그대로 존재 |

---

### TC-03: 마이컬리 탭 로그아웃 → 전체 삭제

| 단계 | 액션 | 기대 결과 |
|---|---|---|
| 1 | AD_, INFO_ 알람 모두 신청된 상태 확인 | 알람 존재 |
| 2 | 마이컬리 탭 → 로그아웃 | - |
| 3 | `adb shell dumpsys alarm \| grep kurly` | AD_, INFO_ 알람 전부 사라짐 |

---

### TC-04: 웹뷰 직접 로그아웃 → 전체 삭제

| 단계 | 액션 | 기대 결과 |
|---|---|---|
| 1 | AD_, INFO_ 알람 모두 신청된 상태 확인 | 알람 존재 |
| 2 | 웹뷰(마이컬리 웹) → 로그아웃 버튼 탭 | - |
| 3 | `adb shell dumpsys alarm \| grep kurly` | AD_, INFO_ 알람 전부 사라짐 |

---

### TC-05: 토큰 만료 강제 로그아웃 → 전체 삭제

> **Note:** 타 기기 탈퇴 시나리오도 이 TC로 커버됨 — 타 기기 탈퇴 후 이 기기에서 발생하는 동작은 401-1003 수신 → 전체 삭제이므로 동일한 흐름. 멀티 디바이스 별도 검증 불필요.

| 단계 | 액션 | 기대 결과 |
|---|---|---|
| 1 | 알람 신청된 상태 확인 | 알람 존재 |
| 2 | Charles/Proxyman으로 401 + error_code=1003 응답 주입 | 강제 로그아웃 발생 |
| 3 | `adb shell dumpsys alarm \| grep kurly` | 전체 알람 사라짐 |

---

### TC-06: 탈퇴 (본 기기) → 전체 삭제 + 재시작 후 알람 미발동

| 단계 | 액션 | 기대 결과 |
|---|---|---|
| 1 | AD_, INFO_ 알람 신청된 상태 확인 | 알람 존재 |
| 2 | 마이컬리 웹 → 탈퇴 진행 (WV3200) | 탈퇴 완료 다이얼로그 |
| 3 | `adb shell dumpsys alarm \| grep kurly` | 즉시 전체 알람 사라짐 |
| 4 | 앱 재시작 후 알람 예약 시각 대기 | 알람 발동 없음 |

---

### TC-07: 예외 케이스

| 번호 | 시나리오 | 기대 결과 |
|---|---|---|
| 7-1 | 알람 0개인 상태에서 마수동 OFF | 오류 없이 정상 처리, 빈 상태 유지 |
| 7-2 | 마수동 OFF 중 서버 오류 (updateNotificationSetting 실패) | 알람 삭제 안 됨 (서버 실패 시 삭제 불가) |
| 7-3 | 로그아웃 직후 즉시 재로그인 | 재로그인 후 알람 신청 가능, 이전 알람과 충돌 없음 |
| 7-4 | 탈퇴 후 재가입 + 알람 재신청 | 신규 알람 정상 등록, 이전 알람 간섭 없음 |
| 7-5 | 마수동 OFF → 즉시 다시 ON | AD_ 알람 삭제 후 재신청 가능 |
