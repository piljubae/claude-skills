# Build Info Overlay Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 개발자 모드 활성화 시 빌드 타입·플레이버·버전·빌드 시간을 화면 우측 하단에 항상 표시해, 스크린샷에 빌드 정보가 자동으로 찍히도록 한다.

**Architecture:** `DebuggingView`(드래그 버튼)와 완전 독립된 `BuildInfoOverlayView`를 새로 만들어 매 Activity의 `decorView`에 별도로 attach한다. `BuildInfoOverlayController`가 SharedPreferences 기반 ON/OFF 상태를 관리하고 개발자 메뉴 토글 항목을 등록한다. 빌드 시간은 `buildConfigField`로 빌드 타임에 주입한다.

**Tech Stack:** Android View (FrameLayout/TextView), SharedPreferences, WeakHashMap, BuildConfig

---

## 변경 파일 목록

| 파일 | 변경 종류 |
|------|-----------|
| `app/build.gradle.kts` | 수정 — BUILD_TIME buildConfigField 추가 |
| `debug-helper/src/main/res/values/ids.xml` | 수정 — overlay view ID 추가 |
| `debug-helper/src/main/java/.../di/DebuggingModuleConfig.kt` | 수정 — buildInfoText 필드 추가 |
| `debug-helper/src/main/java/.../BuildInfoOverlayView.kt` | 신규 |
| `debug-helper/src/main/java/.../BuildInfoOverlayController.kt` | 신규 |
| `debug-helper/src/main/java/.../tracking/DebuggingViewLifecycleCallbacks.kt` | 수정 — overlay attach/detach |
| `app/src/main/kotlin/.../KurlyApplication.kt` | 수정 — buildInfoText 주입, controller 전달 |

---

## Task 1: BUILD_TIME buildConfigField 추가

**Files:**
- Modify: `app/build.gradle.kts`

현재 `defaultConfig` 블록에 buildConfigField가 없다. `versionCode` 아래에 추가한다.

**Step 1: build.gradle.kts 수정**

`app/build.gradle.kts`의 `defaultConfig { }` 블록을:

```kotlin
defaultConfig {
    applicationId = "com.dbs.kurly.m2"
    testApplicationId = "com.dbs.kurly.m2.test"
    versionCode = 649
    versionName = "3.71.1"
}
```

아래로 변경:

```kotlin
defaultConfig {
    applicationId = "com.dbs.kurly.m2"
    testApplicationId = "com.dbs.kurly.m2.test"
    versionCode = 649
    versionName = "3.71.1"
    buildConfigField(
        "String",
        "BUILD_TIME",
        "\"${java.text.SimpleDateFormat("MM/dd HH:mm").format(java.util.Date())}\"",
    )
}
```

**Step 2: 컴파일 검증**

```bash
./gradlew :app:compileDebugKotlin
```

Expected: BUILD SUCCESSFUL

**Step 3: 커밋**

```bash
git add app/build.gradle.kts
git commit -m "build: BUILD_TIME buildConfigField 추가"
```

---

## Task 2: View ID 리소스 추가

**Files:**
- Modify: `debug-helper/src/main/res/values/ids.xml`

**Step 1: ids.xml 수정**

현재:
```xml
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <item name="debug_helper_debugging_view_id" type="id" />
</resources>
```

변경:
```xml
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <item name="debug_helper_debugging_view_id" type="id" />
    <item name="debug_helper_build_info_overlay_id" type="id" />
</resources>
```

**Step 2: 컴파일 검증**

```bash
./gradlew :debug-helper:compileDebugKotlin
```

Expected: BUILD SUCCESSFUL

---

## Task 3: DebuggingModuleConfig에 buildInfoText 추가

**Files:**
- Modify: `debug-helper/src/main/java/com/kurly/android/debugging/di/DebuggingModuleConfig.kt`

`debug-helper` 모듈은 `app`의 `BuildConfig`에 접근할 수 없다. 따라서 빌드 정보 텍스트를 앱 계층에서 조립해 이 config 객체를 통해 전달한다.

**Step 1: DebuggingModuleConfig 수정**

```kotlin
package com.kurly.android.debugging.di

object DebuggingModuleConfig {
    var useDebuggingModule: Boolean = false
    var useWebViewDebugging: Boolean = false
    var buildInfoText: String = ""
}
```

**Step 2: 컴파일 검증**

```bash
./gradlew :debug-helper:compileDebugKotlin
```

---

## Task 4: BuildInfoOverlayView 생성

**Files:**
- Create: `debug-helper/src/main/java/com/kurly/android/debugging/BuildInfoOverlayView.kt`

**Step 1: 파일 생성**

```kotlin
package com.kurly.android.debugging

import android.app.Activity
import android.content.Context
import android.graphics.Color
import android.util.AttributeSet
import android.view.Gravity
import android.view.ViewGroup
import android.widget.FrameLayout
import android.widget.TextView
import com.kurly.android.debugging.di.DebuggingModuleConfig

class BuildInfoOverlayView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : FrameLayout(context, attrs) {

    private val textView: TextView

    init {
        val horizontalPadding = (8 * resources.displayMetrics.density).toInt()
        val verticalPadding = (4 * resources.displayMetrics.density).toInt()
        val margin = (8 * resources.displayMetrics.density).toInt()

        textView = TextView(context).apply {
            textSize = 10f
            setTextColor(Color.WHITE)
            setBackgroundColor(Color.parseColor("#80000000"))
            setPadding(horizontalPadding, verticalPadding, horizontalPadding, verticalPadding)
        }

        val layoutParams = LayoutParams(
            LayoutParams.WRAP_CONTENT,
            LayoutParams.WRAP_CONTENT,
            Gravity.BOTTOM or Gravity.END,
        ).apply {
            setMargins(0, 0, margin, margin)
        }

        addView(textView, layoutParams)
        elevation = 9998f
        isClickable = false
        isFocusable = false
    }

    fun addToWindow(activity: Activity?) {
        if (!DebuggingModuleConfig.useDebuggingModule) return
        if (activity == null) return
        removeFromWindow(activity)
        id = R.id.debug_helper_build_info_overlay_id
        textView.text = DebuggingModuleConfig.buildInfoText
        (activity.window.decorView as ViewGroup).addView(
            this,
            ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT,
            ),
        )
    }

    companion object {
        fun removeFromWindow(activity: Activity) {
            activity.findViewById<BuildInfoOverlayView>(R.id.debug_helper_build_info_overlay_id)?.let {
                (it.parent as? ViewGroup)?.removeView(it)
            }
        }
    }
}
```

**Step 2: 컴파일 검증**

```bash
./gradlew :debug-helper:compileDebugKotlin
```

Expected: BUILD SUCCESSFUL

---

## Task 5: BuildInfoOverlayController 생성

**Files:**
- Create: `debug-helper/src/main/java/com/kurly/android/debugging/BuildInfoOverlayController.kt`

ON/OFF 상태를 SharedPreferences에 저장하고, 현재 화면에 붙어있는 overlay view들을 일괄 show/hide하며, 개발자 메뉴 토글 항목을 등록한다.

**Step 1: 파일 생성**

```kotlin
package com.kurly.android.debugging

import android.app.Activity
import android.content.Context
import android.view.View
import com.kurly.android.debugging.model.DebuggingItem
import com.kurly.android.debugging.model.DebuggingItemRepository
import java.util.WeakHashMap

class BuildInfoOverlayController(
    applicationContext: Context,
    private val debuggingItemRepository: DebuggingItemRepository,
) {
    private val prefs = applicationContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
    private val overlays = WeakHashMap<Activity, BuildInfoOverlayView>()

    private var isEnabled: Boolean
        get() = prefs.getBoolean(KEY_ENABLED, true)
        set(value) { prefs.edit().putBoolean(KEY_ENABLED, value).apply() }

    fun registerOverlay(activity: Activity, view: BuildInfoOverlayView) {
        overlays[activity] = view
        view.visibility = if (isEnabled) View.VISIBLE else View.GONE
    }

    fun unregisterOverlay(activity: Activity) {
        overlays.remove(activity)
    }

    fun registerToggleItem() {
        val item = DebuggingItem.createItem(
            title = "빌드 정보 오버레이",
            action = {
                isEnabled = !isEnabled
                val visibility = if (isEnabled) View.VISIBLE else View.GONE
                overlays.values.forEach { it.visibility = visibility }
            },
        )
        debuggingItemRepository.addDebuggingItem(item)
    }

    companion object {
        private const val PREFS_NAME = "debug_helper_build_info_overlay"
        private const val KEY_ENABLED = "key_enabled"
    }
}
```

**Step 2: 컴파일 검증**

```bash
./gradlew :debug-helper:compileDebugKotlin
```

Expected: BUILD SUCCESSFUL

---

## Task 6: DebuggingViewLifecycleCallbacks 수정

**Files:**
- Modify: `debug-helper/src/main/java/com/kurly/android/debugging/tracking/DebuggingViewLifecycleCallbacks.kt`

`BuildInfoOverlayController`를 생성자로 받아, `onActivityCreated`에서 overlay attach + 토글 항목 등록, `onActivityDestroyed`에서 overlay detach한다.

**Step 1: 파일 수정**

```kotlin
package com.kurly.android.debugging.tracking

import android.app.Activity
import android.app.Application
import android.os.Bundle
import android.view.ViewGroup
import androidx.appcompat.app.AppCompatActivity
import androidx.fragment.app.Fragment
import androidx.fragment.app.FragmentActivity
import androidx.fragment.app.FragmentManager
import com.kurly.android.debugging.BuildInfoOverlayController
import com.kurly.android.debugging.BuildInfoOverlayView
import com.kurly.android.debugging.FloatingLogController
import com.kurly.android.debugging.R
import com.kurly.android.debugging.di.DebuggingModuleConfig
import com.kurly.android.debugging.model.DebuggingItem
import com.kurly.android.debugging.model.DebuggingItemHolder
import com.kurly.android.debugging.model.DebuggingItemRepository
import com.kurly.android.debugging.model.DebuggingViewController
import com.kurly.android.debugging.view.DebuggingView
import com.kurly.android.debugging.view.explorer.DebuggingItemExplorerDialogFragment
import java.util.WeakHashMap

class DebuggingViewLifecycleCallbacks(
    private val debuggingItemRepository: DebuggingItemRepository,
    private val floatingLogController: FloatingLogController,
    private val buildInfoOverlayController: BuildInfoOverlayController,
) : Application.ActivityLifecycleCallbacks {

    private val fragmentCallbacks = WeakHashMap<Activity, FragmentManager.FragmentLifecycleCallbacks>()

    private fun createFragmentCallbacks() = object : FragmentManager.FragmentLifecycleCallbacks() {
        override fun onFragmentResumed(fm: FragmentManager, f: Fragment) {
            val tag = f.tag
            if (tag != null && tag.startsWith("android:")) return
            if (f.javaClass.name.startsWith("com.kurly.android.debugging")) return
            DebuggingScreenTracker.setFragment(f.javaClass.simpleName)
        }
    }

    override fun onActivityCreated(activity: Activity, savedInstanceState: Bundle?) {
        if (!DebuggingModuleConfig.useDebuggingModule) return

        // 기존 디버깅 버튼
        val debuggingView = DebuggingView(activity).apply {
            id = R.id.debug_helper_debugging_view_id
        }

        (activity as? AppCompatActivity)?.let { appCompatActivity ->
            debuggingView.debuggingViewController = object : DebuggingViewController {
                override fun openDebuggingExplorer() {
                    DebuggingItemExplorerDialogFragment.show(
                        appCompatActivity.supportFragmentManager,
                    )
                }
            }
        }

        (activity as? DebuggingItemHolder)?.let { holder ->
            val lifecycleOwner = activity as? AppCompatActivity ?: return@let
            debuggingItemRepository.addDebuggingItemsWithAutoCleared(
                lifecycleOwner = lifecycleOwner,
                debuggingItem = DebuggingItem.createGroup(
                    title = activity.javaClass.simpleName,
                    childItems = holder.debuggingItems,
                ),
            )
        }

        debuggingView.addToWindow(activity)
        floatingLogController.onActivityCreated(activity)

        // 빌드 정보 오버레이
        val overlayView = BuildInfoOverlayView(activity)
        overlayView.addToWindow(activity)
        buildInfoOverlayController.registerOverlay(activity, overlayView)
        buildInfoOverlayController.registerToggleItem()

        val callbacks = createFragmentCallbacks()
        fragmentCallbacks[activity] = callbacks
        (activity as? FragmentActivity)?.supportFragmentManager
            ?.registerFragmentLifecycleCallbacks(callbacks, true)
    }

    override fun onActivityResumed(activity: Activity) {
        DebuggingScreenTracker.setActivity(activity.javaClass.simpleName)
    }

    override fun onActivityDestroyed(activity: Activity) {
        fragmentCallbacks.remove(activity)?.let { callbacks ->
            (activity as? FragmentActivity)?.supportFragmentManager
                ?.unregisterFragmentLifecycleCallbacks(callbacks)
        }

        activity.findViewById<DebuggingView>(R.id.debug_helper_debugging_view_id)?.let {
            (it.parent as? ViewGroup)?.removeView(it)
        }

        BuildInfoOverlayView.removeFromWindow(activity)
        buildInfoOverlayController.unregisterOverlay(activity)

        floatingLogController.onActivityDestroyed(activity)
    }

    override fun onActivityStarted(activity: Activity) {}
    override fun onActivityStopped(activity: Activity) {}
    override fun onActivityPaused(activity: Activity) {}
    override fun onActivitySaveInstanceState(activity: Activity, outState: Bundle) {}
}
```

**Step 2: 컴파일 검증**

```bash
./gradlew :debug-helper:compileDebugKotlin
```

Expected: BUILD SUCCESSFUL

---

## Task 7: KurlyApplication 수정 — buildInfoText 주입 및 controller 전달

**Files:**
- Modify: `app/src/main/kotlin/com/dbs/kurly/m2/KurlyApplication.kt`

`BuildConfig`가 `app` 모듈에 있으므로 여기서 텍스트를 조립한다. `BuildInfoOverlayController` 인스턴스를 생성해 `DebuggingViewLifecycleCallbacks`에 전달한다.

**Step 1: 변경 위치 파악**

현재 코드:
```kotlin
if (DebuggingModuleConfig.useDebuggingModule) {
    val entryPoint = dagger.hilt.android.EntryPointAccessors
        .fromApplication(this, com.dbs.kurly.m2.app.SingletonEntryPoint::class.java)
    registerActivityLifecycleCallbacks(
        DebuggingViewLifecycleCallbacks(
            debuggingItemRepository = entryPoint.debuggingItemRepository(),
            floatingLogController = entryPoint.floatingLogController(),
        ),
    )
}
```

**Step 2: 수정**

```kotlin
if (DebuggingModuleConfig.useDebuggingModule) {
    DebuggingModuleConfig.buildInfoText = buildString {
        append("${BuildConfig.FLAVOR}·${BuildConfig.BUILD_TYPE}")
        append("\nv${BuildConfig.VERSION_NAME} (${BuildConfig.VERSION_CODE})")
        append("\n${BuildConfig.BUILD_TIME}")
    }

    val entryPoint = dagger.hilt.android.EntryPointAccessors
        .fromApplication(this, com.dbs.kurly.m2.app.SingletonEntryPoint::class.java)
    val buildInfoOverlayController = BuildInfoOverlayController(
        applicationContext = this,
        debuggingItemRepository = entryPoint.debuggingItemRepository(),
    )
    registerActivityLifecycleCallbacks(
        DebuggingViewLifecycleCallbacks(
            debuggingItemRepository = entryPoint.debuggingItemRepository(),
            floatingLogController = entryPoint.floatingLogController(),
            buildInfoOverlayController = buildInfoOverlayController,
        ),
    )
}
```

필요한 import 추가:
```kotlin
import com.kurly.android.debugging.BuildInfoOverlayController
```

**Step 3: 컴파일 검증 (전체)**

```bash
./gradlew :app:compileDebugKotlin
```

Expected: BUILD SUCCESSFUL

**Step 4: 커밋**

```bash
git add \
  debug-helper/src/main/res/values/ids.xml \
  debug-helper/src/main/java/com/kurly/android/debugging/di/DebuggingModuleConfig.kt \
  debug-helper/src/main/java/com/kurly/android/debugging/BuildInfoOverlayView.kt \
  debug-helper/src/main/java/com/kurly/android/debugging/BuildInfoOverlayController.kt \
  debug-helper/src/main/java/com/kurly/android/debugging/tracking/DebuggingViewLifecycleCallbacks.kt \
  app/src/main/kotlin/com/dbs/kurly/m2/KurlyApplication.kt
git commit -m "feat: 개발자 모드 빌드 정보 오버레이 추가"
```

---

## 검증 체크리스트

- [ ] 개발자 모드 ON → 화면 우측 하단에 `beta·debug / v3.71.1 (649) / MM/dd HH:mm` 표시
- [ ] 개발자 메뉴 → "빌드 정보 오버레이" 탭 → 오버레이 사라짐
- [ ] 다시 탭 → 오버레이 다시 표시
- [ ] 앱 재시작 후 ON/OFF 상태 유지
- [ ] 기존 "디버깅" 드래그 버튼 정상 동작
- [ ] 개발자 모드 OFF 상태에서는 오버레이 미표시
