# Order Alarm INFO_ORDER_ Prefix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 주문 시간 알람을 DataStore에 `INFO_ORDER_KURLY_SHOPPING_ALARM` alarmId로 저장하여, 개발자 모드 로컬 푸시 내역에 표시되게 하고 prefix 기반 알람 분류 체계를 완성한다.

**Architecture:**
기존 `NotificationRepository.saveWebAlarm()`을 재활용해 AlarmWeb 형태로 DataStore에 저장/삭제한다. BootBroadcastReceiver에서의 주문 알람 복구는 기존 SharedPrefs 경로를 유지하고, `WebAlarmDispatcherImpl.getAlarmIfNotTriggered()`에서 `INFO_ORDER_` 알람을 필터링해 중복 복구를 방지한다. 알람 등록/취소는 `KurlyNotificationViewModel`에서 담당한다.

**Tech Stack:** Kotlin, Hilt, DataStore, AlarmManager, Coroutines, JUnit4, MockK

---

## 배경 지식

### 두 가지 알람 저장 구조

| 구분 | 웹뷰 알람 (LIVE/LEGO/CLAY) | 주문 시간 알람 |
|------|--------------------------|--------------|
| 저장소 | DataStore (`Set<AlarmWeb>`) | SharedPrefs `KEY_KURLY_ALARM_SETTING` |
| 식별자 | `alarmId: String` (prefix 포함) | requestCode = `52525566` (고정 int) |
| 로컬 푸시 내역 | 표시됨 | **표시 안됨 (이번에 수정)** |

### 로컬 푸시 내역 (`LocalPushScreen`)

`LocalPushScreen`은 `notificationRepository.getWebAlarmsFlow()`(DataStore)만 읽는다.
이번 작업 후 주문 알람도 DataStore에 저장되므로 내역에 표시된다.

### `AlarmWeb` 모델

```kotlin
data class AlarmWeb(
    val alarmId: String,    // "INFO_ORDER_KURLY_SHOPPING_ALARM"
    val title: String,
    val message: String,
    val datetime: String,   // ISO_ZONED_DATE_TIME 형식
    val image: String?,
    val link: String?,
    val callback: String?,
    val errorCallback: String?,
    val requestCode: Int,   // KurlyAlarmBroadcastReceiver.NOTIFICATION_ID = 52525566
    val timeMs: Long        // epoch ms, isNotTriggered = timeMs > now
)
```

### 코드 확인 사항

- **`AlarmWeb.toWebModel()`**: `WebAlarmDispatcherImpl.kt` 내부의 private extension function. 테스트에서 직접 호출하지 않으므로 접근성 문제 없음.
- **`NotificationRepository` Hilt 바인딩**: `data/src/main/java/com/kurly/data/di/repository/RepositoryModule.kt`에 `@Binds @InstallIn(SingletonComponent::class)` 로 이미 등록됨. 별도 Hilt 모듈 추가 불필요.
- **`AlarmMessage()`**: no-arg 생성자 있음 (title/message 모두 기본값 있음).
- **`BaseViewModelTest`**: `Dispatchers.setMain(StandardTestDispatcher())`를 `@Before`에서 호출. `runTest { advanceUntilIdle() }`의 스케줄러와 `viewModelScope`의 스케줄러가 달라 코루틴이 진행되지 않을 수 있음 → 서브클래스 `@Before`에서 `UnconfinedTestDispatcher`로 덮어써야 함.

---

## Task 1: KurlyNotificationViewModel — DataStore 저장/삭제

**수정 파일:**
- Modify: `features/src/main/java/com/kurly/features/notification/KurlyNotificationViewModel.kt`
- Create: `features/src/test/java/com/kurly/features/notification/KurlyNotificationViewModelTest.kt`

### Step 1: 테스트 파일 생성 (실패 확인용)

```kotlin
// features/src/test/java/com/kurly/features/notification/KurlyNotificationViewModelTest.kt
package com.kurly.features.notification

import com.kurly.domain.model.notification.AlarmInfo
import com.kurly.domain.model.notification.AlarmWeb
import com.kurly.domain.repository.notification.NotificationRepository
import com.kurly.domain.usecase.notification.GetKurlyAlarmMessage
import com.kurly.domain.usecase.notification.GetKurlyAlarmSetting
import com.kurly.domain.usecase.notification.UpdateKurlyAlarmSetting
import com.kurly.domain.usecase.notification.UpdateNotificationSettings
import com.kurly.features.BaseViewModelTest
import com.kurly.features.notification.model.AlarmInfoUiModel
import io.mockk.every
import io.mockk.just
import io.mockk.mockk
import io.mockk.runs
import io.mockk.slot
import io.mockk.verify
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

@ExperimentalCoroutinesApi
class KurlyNotificationViewModelTest : BaseViewModelTest() {

    private lateinit var viewModel: KurlyNotificationViewModel
    private val notificationRepository: NotificationRepository = mockk(relaxed = true)
    private val updateKurlyAlarmSetting: UpdateKurlyAlarmSetting = mockk(relaxed = true)
    private val getKurlyAlarmSetting: GetKurlyAlarmSetting = mockk(relaxed = true)
    private val getKurlyAlarmMessage: GetKurlyAlarmMessage = mockk(relaxed = true)
    private val updateNotificationSettings: UpdateNotificationSettings = mockk(relaxed = true)

    @Before
    fun overrideMainDispatcher() {
        // BaseViewModelTest.before()의 StandardTestDispatcher를 덮어씀
        // viewModelScope 코루틴이 즉시 실행되도록 UnconfinedTestDispatcher 사용
        Dispatchers.setMain(UnconfinedTestDispatcher())
    }

    @Before
    fun setUp() {
        viewModel = KurlyNotificationViewModel(
            dispatcherProvider = dispatcherProvider,
            notificationRepository = notificationRepository,
            updateNotificationSettings = updateNotificationSettings,
            updateKurlyAlarmSetting = updateKurlyAlarmSetting,
            getKurlyAlarmSetting = getKurlyAlarmSetting,
            getKurlyAlarmMessage = getKurlyAlarmMessage,
        )
    }

    @Test
    fun `알람 활성화 시 INFO_ORDER_ prefix로 DataStore에 저장된다`() = runTest {
        val alarmInfo = AlarmInfoUiModel.create(AlarmInfo(isEnable = true, hour = 21, minute = 0))
        val savedAlarmSlot = slot<AlarmWeb>()
        every { notificationRepository.saveWebAlarm(capture(savedAlarmSlot)) } just runs

        viewModel.updateAlarmInfo(alarmInfo)

        verify { notificationRepository.saveWebAlarm(any()) }
        assertTrue(savedAlarmSlot.captured.alarmId.startsWith("INFO_ORDER_"))
        assertEquals(
            KurlyNotificationViewModel.ORDER_ALARM_ID,
            savedAlarmSlot.captured.alarmId,
        )
    }

    @Test
    fun `알람 비활성화 시 DataStore에서 삭제된다`() = runTest {
        val alarmInfo = AlarmInfoUiModel.create(AlarmInfo(isEnable = false))
        val existingAlarm = AlarmWeb(
            alarmId = KurlyNotificationViewModel.ORDER_ALARM_ID,
            title = "test", message = "", datetime = "", image = null,
            link = null, callback = null, errorCallback = null,
            requestCode = 52525566, timeMs = 0L,
        )
        every { notificationRepository.getWebAlarms() } returns setOf(existingAlarm)

        viewModel.updateAlarmInfo(alarmInfo)

        verify { notificationRepository.deleteWebAlarms(existingAlarm) }
    }
}
```

### Step 2: 테스트 실행 → 실패 확인

```bash
cd /Users/pilju.bae/AndroidStudioProjects/kurly-android
./gradlew :features:testDebugUnitTest --tests "com.kurly.features.notification.KurlyNotificationViewModelTest" 2>&1 | tail -20
```

기대 결과: `KurlyNotificationViewModel` 생성자에 `notificationRepository` 파라미터 없어서 컴파일 에러

### Step 3: ViewModel 수정

`KurlyNotificationViewModel.kt`를 다음과 같이 수정한다:

```kotlin
// features/src/main/java/com/kurly/features/notification/KurlyNotificationViewModel.kt

import com.kurly.domain.model.notification.AlarmInfo
import com.kurly.domain.model.notification.AlarmMessage
import com.kurly.domain.model.notification.AlarmWeb
import com.kurly.domain.repository.notification.NotificationRepository
import com.kurly.features.broadcast.KurlyAlarmBroadcastReceiver
import java.time.ZoneId
import java.time.format.DateTimeFormatter

@HiltViewModel
class KurlyNotificationViewModel @Inject constructor(
    private val dispatcherProvider: DispatcherProvider,
    private val notificationRepository: NotificationRepository,   // ← 추가
    private val updateNotificationSettings: UpdateNotificationSettings,
    private val updateKurlyAlarmSetting: UpdateKurlyAlarmSetting,
    private val getKurlyAlarmSetting: GetKurlyAlarmSetting,
    private val getKurlyAlarmMessage: GetKurlyAlarmMessage,
) : ViewModel() {

    // ... 기존 코드 유지 ...

    fun updateAlarmInfo(info: AlarmInfoUiModel) {
        alarmInfo.postValue(info)

        // DataStore 저장/삭제 (로컬 푸시 내역 표시용)
        viewModelScope.launch(dispatcherProvider.io()) {
            if (info.isEnable) {
                val message = alarmMessage.value ?: AlarmMessageUiModel.create(AlarmMessage())
                notificationRepository.saveWebAlarm(createOrderAlarmWeb(info, message))
            } else {
                notificationRepository.getWebAlarms()
                    .find { it.alarmId == ORDER_ALARM_ID }
                    ?.let { notificationRepository.deleteWebAlarms(it) }
            }
        }

        // 기존: SharedPrefs 저장
        with(info) {
            UpdateKurlyAlarmSetting.Params(
                isEnable = isEnable,
                hour = hour,
                minute = minute,
                repeatType = repeatType.name,
                alarmDays = alarmDays.map { it.isChecked },
                alarmDate = if (repeatType == AlarmRepeatType.ONCE) parseDateToString() else null,
            )
        }.let {
            viewModelScope.launch(dispatcherProvider.io()) {
                updateKurlyAlarmSetting.execute(it)
            }
        }
    }

    private fun createOrderAlarmWeb(info: AlarmInfoUiModel, message: AlarmMessageUiModel): AlarmWeb {
        val zonedDateTime = info.getLocalDateTime().atZone(ZoneId.systemDefault())
        return AlarmWeb(
            alarmId = ORDER_ALARM_ID,
            title = message.title,
            message = message.message,
            datetime = zonedDateTime.format(DateTimeFormatter.ISO_ZONED_DATE_TIME),
            image = null,
            link = message.deeplink,
            callback = null,
            errorCallback = null,
            requestCode = KurlyAlarmBroadcastReceiver.NOTIFICATION_ID,
            timeMs = zonedDateTime.toInstant().toEpochMilli(),
        )
    }

    companion object {
        const val ORDER_ALARM_ID = "INFO_ORDER_KURLY_SHOPPING_ALARM"
    }
}
```

### Step 4: 테스트 실행 → 성공 확인

```bash
./gradlew :features:testDebugUnitTest --tests "com.kurly.features.notification.KurlyNotificationViewModelTest" 2>&1 | tail -20
```

기대 결과: `BUILD SUCCESSFUL`, 2개 테스트 통과

### Step 5: 컴파일 확인

```bash
./gradlew :features:compileDebugKotlin 2>&1 | tail -20
```

기대 결과: `BUILD SUCCESSFUL`

### Step 6: 커밋

```bash
git add features/src/main/java/com/kurly/features/notification/KurlyNotificationViewModel.kt \
        features/src/test/java/com/kurly/features/notification/KurlyNotificationViewModelTest.kt
git commit -m "PRJ-276 주문 알람 등록/취소 시 DataStore INFO_ORDER_ 저장"
```

---

## Task 2: WebAlarmDispatcherImpl — INFO_ORDER_ 부팅 복구 제외

부팅 시 `BootBroadcastReceiver`가 주문 알람을 이미 SharedPrefs에서 복구하므로, `webAlarmDispatcher.setAlarmIfNotTriggered()`에서 INFO_ORDER_ 알람을 건너뛰어야 한다. 그렇지 않으면 주문 알람이 웹뷰 알람 경로(ONCE 타입, 잘못된 방식)로 이중 등록된다.

**수정 파일:**
- Modify: `features/src/main/java/com/kurly/features/web/bridge/common/user/WebAlarmDispatcherImpl.kt`
- Create: `features/src/test/java/com/kurly/features/web/bridge/common/user/WebAlarmDispatcherImplTest.kt`

### Step 1: 테스트 작성

```kotlin
// features/src/test/java/com/kurly/features/web/bridge/common/user/WebAlarmDispatcherImplTest.kt
package com.kurly.features.web.bridge.common.user

import com.kurly.domain.model.notification.AlarmWeb
import com.kurly.domain.repository.notification.NotificationRepository
import io.mockk.every
import io.mockk.mockk
import org.junit.Before
import org.junit.Test
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter

class WebAlarmDispatcherImplTest {

    private val notificationRepository: NotificationRepository = mockk(relaxed = true)
    private lateinit var dispatcher: WebAlarmDispatcherImpl

    @Before
    fun setUp() {
        dispatcher = WebAlarmDispatcherImpl(notificationRepository)
    }

    @Test
    fun `getAlarmIfNotTriggered는 INFO_ORDER_ 알람을 제외한다`() {
        val futureTimeMs = System.currentTimeMillis() + 60_000L
        val futureIso = ZonedDateTime.now()
            .plusMinutes(10)
            .format(DateTimeFormatter.ISO_ZONED_DATE_TIME)

        val orderAlarm = AlarmWeb(
            alarmId = "INFO_ORDER_KURLY_SHOPPING_ALARM",
            title = "주문 알람", message = "", datetime = futureIso,
            image = null, link = null, callback = null, errorCallback = null,
            requestCode = 52525566, timeMs = futureTimeMs,
        )
        val liveAlarm = AlarmWeb(
            alarmId = "INFO_LIVE_abc123",
            title = "라이브 알람", message = "", datetime = futureIso,
            image = null, link = null, callback = null, errorCallback = null,
            requestCode = 1001, timeMs = futureTimeMs,
        )
        every { notificationRepository.getWebAlarms() } returns setOf(orderAlarm, liveAlarm)

        val result = dispatcher.getAlarmIfNotTriggered()

        assert(result.none { it.alarmId == "INFO_ORDER_KURLY_SHOPPING_ALARM" }) {
            "INFO_ORDER_ 알람이 복구 대상에 포함되면 안됨"
        }
        assert(result.any { it.alarmId == "INFO_LIVE_abc123" }) {
            "INFO_LIVE_ 알람은 복구 대상에 포함되어야 함"
        }
    }
}
```

### Step 2: 테스트 실행 → 실패 확인

```bash
./gradlew :features:testDebugUnitTest --tests "com.kurly.features.web.bridge.common.user.WebAlarmDispatcherImplTest" 2>&1 | tail -20
```

기대 결과: FAIL — `INFO_ORDER_KURLY_SHOPPING_ALARM`이 필터링 안됨

### Step 3: WebAlarmDispatcherImpl 수정

`getAlarmIfNotTriggered()` 메서드에 필터 조건 추가:

```kotlin
// Before
override fun getAlarmIfNotTriggered(): Set<AlarmWebModel> {
    return notificationRepository.getWebAlarms()
        .filter { it.isNotTriggered }
        .map { it.toWebModel() }
        .toSet()
}

// After
override fun getAlarmIfNotTriggered(): Set<AlarmWebModel> {
    return notificationRepository.getWebAlarms()
        .filter { it.isNotTriggered && !it.alarmId.startsWith(ORDER_ALARM_PREFIX) }
        .map { it.toWebModel() }
        .toSet()
}

companion object {
    private const val ORDER_ALARM_PREFIX = "INFO_ORDER_"
}
```

### Step 4: 테스트 실행 → 성공 확인

```bash
./gradlew :features:testDebugUnitTest --tests "com.kurly.features.web.bridge.common.user.WebAlarmDispatcherImplTest" 2>&1 | tail -20
```

기대 결과: `BUILD SUCCESSFUL`, 1개 테스트 통과

### Step 5: 컴파일 확인

```bash
./gradlew :features:compileDebugKotlin 2>&1 | tail -20
```

### Step 6: 커밋

```bash
git add features/src/main/java/com/kurly/features/web/bridge/common/user/WebAlarmDispatcherImpl.kt \
        features/src/test/java/com/kurly/features/web/bridge/common/user/WebAlarmDispatcherImplTest.kt
git commit -m "PRJ-276 부팅 복구 시 INFO_ORDER_ 알람 중복 등록 방지"
```

---

## Task 3: 전체 테스트 및 수동 검증

> **기획 확인 (2026-03-27)**: 기존 prefix 없는 알람은 삭제하지 않고 유지한다. (혜린님 확인)

### Step 1: 전체 유닛 테스트

```bash
./gradlew :features:testDebugUnitTest 2>&1 | tail -30
```

기대 결과: `BUILD SUCCESSFUL`

### Step 2: 수동 검증 체크리스트

STG 빌드 설치 후 아래 순서로 확인:

```
[ ] 1. 앱 설치 → 개발자 모드 → Local Push 목록 확인 (비어있거나 기존 알람만 있음)

[ ] 2. 마켓 → 특가/혜택 → LEGO 배너 → 알람 신청
        → Local Push에 AD_LEGO_xxx 표시 확인

[ ] 3. 설정 → 알림 설정 → 주문 시간 알람 ON
        → Local Push에 INFO_ORDER_KURLY_SHOPPING_ALARM 표시 확인

[ ] 4. 주문 시간 알람 OFF
        → Local Push에서 INFO_ORDER_KURLY_SHOPPING_ALARM 사라짐 확인

[ ] 5. 주문 시간 알람 ON → 기기 재부팅
        → 재부팅 후 AlarmManager에 주문 알람 등록 확인 (중복 등록 없음)
        → Local Push 목록에 INFO_ORDER_KURLY_SHOPPING_ALARM 여전히 있음 확인

[ ] 6. 설정한 시간에 주문 알람 정상 발화 확인
```

### Step 3: 최종 빌드 확인

```bash
./gradlew assembleDebug 2>&1 | tail -10
```

---

## 수정 파일 요약

| 파일 | 변경 내용 |
|------|---------|
| `features/.../notification/KurlyNotificationViewModel.kt` | `NotificationRepository` 주입, 알람 ON/OFF 시 DataStore 저장/삭제 |
| `features/.../web/bridge/common/user/WebAlarmDispatcherImpl.kt` | `getAlarmIfNotTriggered()`에서 `INFO_ORDER_` 필터링 |
| ~~`app/.../app/start/KurlyApplicationInitializer.kt`~~ | ~~삭제 마이그레이션~~ → 기존 알람 유지 (기획 확인) |
