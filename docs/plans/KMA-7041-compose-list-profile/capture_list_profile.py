#!/usr/bin/env python3
"""
KMA-7041 ListProfileActivity 스크린샷 캡처 스크립트

탐색 경로:
  앱 실행 → 마이컬리 탭 → (스크롤) → 나의 컬리 스타일 → 뷰티 프로필 → ListProfileActivity

사용법:
  python3 capture_list_profile.py production  # before_production.png
  python3 capture_list_profile.py beta         # before_beta.png
  python3 capture_list_profile.py both         # 둘 다 (기본값)
  python3 capture_list_profile.py after        # after_beta.png

사전 준비:
  pip3 install uiautomator2 Pillow
"""

import subprocess
import sys
import time
import os
import re

# --- 설정 -----------------------------------------------------------------

DEVICE_SERIAL = "R3CT10A3JCE"

APPS = {
    "production": {
        "package": "com.dbs.kurly.m2",
        "starter_activity": "com.dbs.kurly.m2.a_new_presentation.start.AppStarterActivity",
        "output_filename": "before_production.png",
    },
    "beta": {
        "package": "com.dbs.kurly.m2.beta",
        "starter_activity": "com.dbs.kurly.m2.a_new_presentation.start.AppStarterActivity",
        "output_filename": "before_beta.png",
    },
}

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREENSHOT_DIR = os.path.join(REPO_ROOT, "docs", "screenshot")

# uiautomator2 연결 대기 타임아웃 (초)
U2_CONNECT_TIMEOUT = 30

# --- uiautomator2 / adb 유틸 -----------------------------------------------


def get_u2_device():
    """uiautomator2 Device 객체 반환. 실패 시 None."""
    try:
        import uiautomator2 as u2
        d = u2.connect(DEVICE_SERIAL)
        _ = d.info  # 연결 확인
        return d
    except Exception as e:
        print(f"  [경고] uiautomator2 연결 실패: {e}")
        return None


def adb(*args):
    """adb 명령 실행. stdout+stderr 문자열 반환."""
    cmd = ["adb", "-s", DEVICE_SERIAL] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout + result.stderr


def adb_bytes(*args):
    """adb 명령 실행. stdout bytes 반환 (screencap 용)."""
    cmd = ["adb", "-s", DEVICE_SERIAL] + list(args)
    result = subprocess.run(cmd, capture_output=True)
    return result.stdout


def current_activity():
    """현재 포커스된 Activity (패키지/클래스) 반환."""
    out = adb("shell", "dumpsys", "activity", "activities")
    m = re.search(r"mCurrentFocus=Window\{[^ ]+ u0 ([^}]+)\}", out)
    if m:
        return m.group(1).strip()
    return "(알 수 없음)"


def take_screenshot(output_path):
    """스크린샷을 output_path 로 저장."""
    data = adb_bytes("exec-out", "screencap", "-p")
    if not data:
        raise RuntimeError("screencap 데이터가 비어 있습니다.")
    with open(output_path, "wb") as f:
        f.write(data)
    print(f"  스크린샷 저장: {output_path}")


# --- uiautomator2 기반 탐색 ------------------------------------------------


def navigate_and_capture_u2(d, pkg, starter_activity, output_path):
    """
    uiautomator2 d를 사용해 ListProfileActivity까지 탐색 후 스크린샷 저장.
    성공 시 True, 실패 시 RuntimeError.
    """
    # 1. 앱 강제 종료 후 재시작
    print(f"  [1] 앱 시작: {pkg}")
    d.app_stop(pkg)
    time.sleep(1.5)
    d.app_start(pkg, activity=starter_activity, wait=True)
    time.sleep(6)

    act = current_activity()
    print(f"  현재 Activity: {act}")
    if pkg not in act:
        raise RuntimeError(f"앱이 시작되지 않았습니다. 현재: {act}")

    # 다이얼로그 처리
    _dismiss_dialog_u2(d)

    # 2. 마이컬리 탭 클릭
    print("  [2] 마이컬리 탭 탐색 중...")
    mykurly_tab = None
    for selector in [
        d(description="마이컬리"),
        d(text="마이컬리"),
        d(resourceId=f"{pkg}:id/mykurly"),
    ]:
        if selector.exists(timeout=3):
            mykurly_tab = selector
            break

    if mykurly_tab is None:
        raise RuntimeError(
            f"마이컬리 탭을 찾을 수 없습니다.\n현재 Activity: {current_activity()}"
        )

    mykurly_tab.click()
    time.sleep(3)

    # 3. '나의 컬리 스타일' 탐색 (스크롤)
    print("  [3] '나의 컬리 스타일' 탐색 (최대 5회 스크롤)...")
    style_item = None
    for i in range(5):
        el = d(text="나의 컬리 스타일")
        if el.exists(timeout=2):
            style_item = el
            print(f"  발견 ({i}회 스크롤 후)")
            break
        print(f"  스크롤 {i + 1}/5...")
        # 탭 좌표는 기기 해상도에 따라 조정 필요 (1080x2340 기준)
        d.swipe(540, 1500, 540, 500, duration=0.8)
        time.sleep(2)

    if style_item is None:
        raise RuntimeError(
            f"'나의 컬리 스타일' 항목을 찾을 수 없습니다.\n현재 Activity: {current_activity()}"
        )

    # 4. '나의 컬리 스타일' 클릭
    print("  [4] '나의 컬리 스타일' 클릭...")
    style_item.click()
    time.sleep(4)

    act = current_activity()
    print(f"  현재 Activity: {act}")
    if "MyKurlyStyle" not in act and "mykurlystyle" not in act.lower():
        raise RuntimeError(
            f"MyKurlyStyleActivity로 이동 실패.\n현재 Activity: {act}"
        )

    # 5. '뷰티 프로필' 클릭
    print("  [5] '뷰티 프로필' 탐색 중...")
    beauty_profile = d(text="뷰티 프로필")
    if not beauty_profile.exists(timeout=5):
        raise RuntimeError(
            f"'뷰티 프로필' 항목을 찾을 수 없습니다.\n현재 Activity: {current_activity()}"
        )

    beauty_profile.click()
    time.sleep(4)

    act = current_activity()
    print(f"  현재 Activity: {act}")
    if "ListProfile" not in act:
        raise RuntimeError(
            f"ListProfileActivity로 이동 실패.\n현재 Activity: {act}"
        )

    # 6. 스크린샷
    print("  [6] ListProfileActivity 스크린샷 촬영...")
    time.sleep(1)
    take_screenshot(output_path)
    return True


def _dismiss_dialog_u2(d):
    """방해 다이얼로그(현재 페이지는 종료되었습니다 등) 처리."""
    confirm = d(text="확인")
    if confirm.exists(timeout=2):
        # 다이얼로그 내 '확인' 버튼인지 확인 (messagePanel 등)
        print("  다이얼로그 '확인' 감지 → 클릭")
        confirm.click()
        time.sleep(1.5)


# --- adb 전용 폴백 탐색 (uiautomator2 사용 불가 시) -----------------------


def _adb_xml_dump():
    """
    기기 UI를 XML로 덤프해 문자열 반환.
    uiautomator dump가 실패하면 None 반환.
    """
    # uiautomator2 Python 라이브러리를 통해 dump_hierarchy 시도
    try:
        import uiautomator2 as u2
        d = u2.connect(DEVICE_SERIAL)
        return d.dump_hierarchy()
    except Exception:
        pass
    return None


def _xml_find_bounds(xml, text=None, resource_id=None, content_desc=None):
    """XML에서 text/resource_id/content_desc 에 매칭되는 노드의 bounds 반환."""
    if not xml:
        return None
    for attr, val in [
        ("text", text),
        ("resource-id", resource_id),
        ("content-desc", content_desc),
    ]:
        if val is None:
            continue
        escaped = re.escape(f'{attr}="{val}"')
        for m in re.finditer(escaped, xml):
            node_start = xml.rfind("<node", 0, m.start())
            node_end = xml.find("/>", m.end())
            if node_start < 0 or node_end < 0:
                continue
            node_str = xml[node_start:node_end + 2]
            bm = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', node_str)
            if bm:
                return tuple(int(x) for x in bm.groups())
    return None


def _xml_find_clickable_parent(xml, text):
    """텍스트 앞 가장 가까운 clickable=true 부모의 bounds 반환."""
    if not xml:
        return None
    idx = xml.find(f'text="{text}"')
    if idx < 0:
        return None
    zone = xml[max(0, idx - 3000):idx]
    matches = list(re.finditer(
        r'clickable="true"[^>]+bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', zone
    ))
    if matches:
        m = matches[-1]
        return tuple(int(x) for x in m.groups())
    return None


def _center(bounds):
    x1, y1, x2, y2 = bounds
    return (x1 + x2) // 2, (y1 + y2) // 2


def navigate_and_capture_adb(pkg, starter_activity, output_path):
    """
    adb shell + XML dump 기반 폴백 탐색.
    uiautomator2 미사용, adb input tap + XML 파싱으로 동작.
    """
    print("  [fallback] adb 전용 모드로 탐색합니다.")

    def tap(x, y):
        # 탭 좌표는 기기 해상도에 따라 조정 필요
        adb("shell", "input", "tap", str(x), str(y))

    def swipe_up():
        # 탭 좌표는 기기 해상도에 따라 조정 필요
        adb("shell", "input", "swipe", "540", "1500", "540", "500", "1000")

    # 1. 앱 시작
    print(f"  [1] 앱 시작: {pkg}")
    adb("shell", "am", "force-stop", pkg)
    time.sleep(1.5)
    adb("shell", "am", "start", "-n", f"{pkg}/{starter_activity}")
    time.sleep(6)

    act = current_activity()
    print(f"  현재 Activity: {act}")
    if pkg not in act:
        raise RuntimeError(f"앱이 시작되지 않았습니다. 현재: {act}")

    # 다이얼로그 처리
    xml = _adb_xml_dump()
    if xml and "확인" in xml and ("종료" in xml or "페이지" in xml):
        print("  다이얼로그 '확인' 감지 → 클릭")
        bounds = _xml_find_bounds(xml, text="확인")
        if bounds:
            tap(*_center(bounds))
            time.sleep(1.5)

    # 2. 마이컬리 탭
    print("  [2] 마이컬리 탭 탐색 중...")
    xml = _adb_xml_dump()
    bounds = (
        _xml_find_bounds(xml, content_desc="마이컬리") or
        _xml_find_bounds(xml, text="마이컬리") or
        _xml_find_bounds(xml, resource_id=f"{pkg}:id/mykurly")
    )
    if not bounds:
        raise RuntimeError(f"마이컬리 탭을 찾을 수 없습니다. 현재: {current_activity()}")
    print(f"  마이컬리 탭: {bounds}")
    tap(*_center(bounds))
    time.sleep(3)

    # 3. 나의 컬리 스타일 탐색
    print("  [3] '나의 컬리 스타일' 탐색...")
    xml = None
    for i in range(5):
        xml = _adb_xml_dump()
        if xml and "나의 컬리 스타일" in xml:
            print(f"  발견 ({i}회 스크롤 후)")
            break
        print(f"  스크롤 {i + 1}/5...")
        swipe_up()
        time.sleep(2)
    else:
        raise RuntimeError(
            f"'나의 컬리 스타일' 항목을 찾을 수 없습니다. 현재: {current_activity()}"
        )

    # 4. 나의 컬리 스타일 클릭
    print("  [4] '나의 컬리 스타일' 클릭...")
    bounds = (
        _xml_find_clickable_parent(xml, "나의 컬리 스타일") or
        _xml_find_bounds(xml, text="나의 컬리 스타일")
    )
    if not bounds:
        raise RuntimeError("'나의 컬리 스타일' 버튼을 찾을 수 없습니다.")
    tap(*_center(bounds))
    time.sleep(4)

    act = current_activity()
    print(f"  현재 Activity: {act}")
    if "MyKurlyStyle" not in act and "mykurlystyle" not in act.lower():
        raise RuntimeError(f"MyKurlyStyleActivity 이동 실패. 현재: {act}")

    # 5. 뷰티 프로필 클릭
    print("  [5] '뷰티 프로필' 탐색 중...")
    xml = _adb_xml_dump()
    if not xml or "뷰티 프로필" not in xml:
        raise RuntimeError(f"'뷰티 프로필' 항목을 찾을 수 없습니다. 현재: {current_activity()}")
    bounds = (
        _xml_find_clickable_parent(xml, "뷰티 프로필") or
        _xml_find_bounds(xml, text="뷰티 프로필")
    )
    if not bounds:
        raise RuntimeError("'뷰티 프로필' 버튼을 찾을 수 없습니다.")
    tap(*_center(bounds))
    time.sleep(4)

    act = current_activity()
    print(f"  현재 Activity: {act}")
    if "ListProfile" not in act:
        raise RuntimeError(f"ListProfileActivity 이동 실패. 현재: {act}")

    # 6. 스크린샷
    print("  [6] ListProfileActivity 스크린샷 촬영...")
    time.sleep(1)
    take_screenshot(output_path)
    return True


# --- 메인 캡처 함수 -------------------------------------------------------


def capture(app_key, output_filename):
    """app_key('production' or 'beta')의 ListProfileActivity 스크린샷 캡처."""
    cfg = APPS[app_key]
    pkg = cfg["package"]
    starter = cfg["starter_activity"]
    output_path = os.path.join(SCREENSHOT_DIR, output_filename)

    print(f"\n=== {app_key.upper()} ({pkg}) 캡처 시작 ===")

    try:
        # uiautomator2 사용 시도
        d = get_u2_device()
        if d is not None:
            navigate_and_capture_u2(d, pkg, starter, output_path)
        else:
            # 폴백: adb + XML dump
            navigate_and_capture_adb(pkg, starter, output_path)

        print(f"  완료: {output_path}")
        return True

    except RuntimeError as e:
        print(f"\n[오류] {app_key} 캡처 실패:")
        print(f"  {e}")
        # 실패 시 현재 화면 저장 (디버그용)
        debug_path = os.path.join(SCREENSHOT_DIR, f"debug_{app_key}_failed.png")
        try:
            take_screenshot(debug_path)
            print(f"  실패 시 화면 저장: {debug_path}")
        except Exception as ex:
            print(f"  디버그 스크린샷도 실패: {ex}")
        return False


# --- 진입점 ---------------------------------------------------------------


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "both"

    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    if mode == "production":
        ok = capture("production", APPS["production"]["output_filename"])
        sys.exit(0 if ok else 1)

    elif mode == "beta":
        ok = capture("beta", APPS["beta"]["output_filename"])
        sys.exit(0 if ok else 1)

    elif mode == "after":
        ok = capture("beta", "after_beta.png")
        sys.exit(0 if ok else 1)

    elif mode == "both":
        ok_prod = capture("production", APPS["production"]["output_filename"])
        ok_beta = capture("beta", APPS["beta"]["output_filename"])
        if ok_prod and ok_beta:
            print("\n모든 캡처 완료.")
        else:
            print("\n일부 캡처 실패. 위 오류 메시지를 확인하세요.")
            sys.exit(1)

    else:
        print(f"알 수 없는 모드: {mode!r}")
        print("사용법: python3 capture_list_profile.py [production|beta|both|after]")
        sys.exit(1)


if __name__ == "__main__":
    main()
