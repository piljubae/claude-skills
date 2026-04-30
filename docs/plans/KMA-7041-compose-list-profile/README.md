# scripts/

## capture_list_profile.py

KMA-7041 디자인 검증용 ListProfileActivity 스크린샷 자동 캡처 스크립트.

실기기(Samsung, serial: R3CT10A3JCE)에서 두 앱(production/beta)의 ListProfileActivity까지
자동으로 탐색한 뒤 스크린샷을 `docs/screenshot/` 에 저장한다.

탐색 경로:
```
앱 실행
  → 마이컬리 탭
  → 아래로 스크롤 (최대 5회, '나의 컬리 스타일' 항목 탐색)
  → 나의 컬리 스타일
  → 뷰티 프로필
  → ListProfileActivity (스크린샷 촬영)
```

### 사전 준비

**Python 패키지 설치**

```bash
pip3 install uiautomator2 Pillow
```

macOS 시스템 Python 환경에서 PEP 668 오류가 발생하면 아래 옵션 추가:

```bash
pip3 install uiautomator2 Pillow --break-system-packages
```

**기기 연결 확인**

```bash
adb devices
# R3CT10A3JCE  device  ← 이 serial이 있어야 함
```

**앱 로그인 상태 확인**

- `com.dbs.kurly.m2` (production) 및 `com.dbs.kurly.m2.beta` (beta) 앱이
  기기에 설치되어 있고 로그인 완료 상태여야 한다.

### 사용법

```bash
cd /path/to/kurly-android

# production 앱 캡처 → docs/screenshot/before_production.png
python3 scripts/capture_list_profile.py production

# beta 앱 캡처 → docs/screenshot/before_beta.png
python3 scripts/capture_list_profile.py beta

# 두 앱 모두 캡처 (기본값)
python3 scripts/capture_list_profile.py both
python3 scripts/capture_list_profile.py        # 인수 없으면 both와 동일

# Compose 전환 후 after 스크린샷 → docs/screenshot/after_beta.png
python3 scripts/capture_list_profile.py after
```

### 출력 파일

| 명령 | 파일 |
|------|------|
| `production` | `docs/screenshot/before_production.png` |
| `beta` | `docs/screenshot/before_beta.png` |
| `after` | `docs/screenshot/after_beta.png` |
| 실패 시 디버그 | `docs/screenshot/debug_{app}_failed.png` |

### 탐색 실패 시

스크립트는 각 단계에서 실패하면 현재 Activity 이름과 어디서 막혔는지 출력한다.
예:

```
[오류] beta 캡처 실패:
  '나의 컬리 스타일' 항목을 찾을 수 없습니다 (5회 스크롤).
  현재 Activity: com.dbs.kurly.m2.beta/com.dbs.kurly.m2.MainActivity
```

실패 시 `docs/screenshot/debug_beta_failed.png` 파일이 저장되므로
해당 스크린샷으로 현재 화면 상태를 확인할 수 있다.

### 주의 사항

- 스크립트 내 tap 좌표 및 swipe 좌표는 해상도 1080x2340 기준이다.
  다른 해상도 기기를 사용하면 `tap()` / `swipe_up()` 함수 내 좌표를 조정해야 한다.
- 기기 serial은 스크립트 상단 `DEVICE_SERIAL` 변수에 하드코딩되어 있다.
  다른 기기 사용 시 변경이 필요하다.
