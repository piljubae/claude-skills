# PRJ-237 로컬 알람 삭제 — 수동 QA 시나리오

## 트리거 × 삭제 범위 요약

| 트리거 | 진입 경로 | 삭제 범위 |
|--------|----------|----------|
| 광수동 OFF (설정 화면) | 마이컬리 → 알림 설정 → 마케팅 정보 수신 동의 OFF | `AD_*` 알람만 |
| 마수동 OFF (WebView) | WebView 마케팅 동의 체크박스 해제 | `AD_*` 알람만 |
| 로그아웃 (앱 내) | 마이컬리 → 설정 → 로그아웃 | 전체 알람 |
| 로그아웃 (WebView) | WebView 로그아웃 버튼 | 전체 알람 |
| 회원 탈퇴 (WV3200) | WebView 회원 탈퇴 완료 콜백 | 전체 알람 |

---

## 알람 확인 방법

```bash
# DataStore에 저장된 알람 조회
adb shell run-as com.kurly.android \
  cat /data/data/com.kurly.android/files/datastore/preferences_name_local_push.preferences_pb | strings

# AlarmManager 등록 알람 확인
adb shell dumpsys alarm | grep kurly
```

Logcat 필터: `tag:NotificationRepositoryImpl`

---

## TC-01: 광고성 알림 해제 팝업 문구 확인

> **변경 내역** (language_packs.xml:348~351)
>
> | 위치 | AS-IS | TO-BE |
> |------|-------|-------|
> | 타이틀 | 알림 설정 | 광고성 알림을 해제하시겠어요? |
> | 본문 | 혜택 정보를 수신하는 분들이\n평균 4% 저렴하게 구매하고 계세요.\n그래도 알림을 끄시겠어요? | 알림을 해제하면 모든 이벤트 혜택과 할인 쿠폰 알림을 받을 수 없어요. |
> | 긍정 버튼 | 알림 유지 | 유지 |
> | 부정 버튼 | 알림 끄기 | 해제 |

**진입 경로:** 마이컬리 → 알림 설정 → 마케팅 정보 수신 동의 (ON → OFF 토글)

**사전 조건:**
- 회원 로그인
- 마케팅 정보 수신 동의 **ON** 상태
- 기기 앱 알림 허용 상태

**테스트 단계:**
1. 마이컬리 → 알림 설정 진입
2. "마케팅 정보 수신 동의" 토글을 OFF 방향으로 탭

**검증:**
- [ ] 타이틀: **"광고성 알림을 해제하시겠어요?"**
- [ ] 본문: **"알림을 해제하면 모든 이벤트 혜택과 할인 쿠폰 알림을 받을 수 없어요."**
- [ ] 부정 버튼: **"해제"**
- [ ] 긍정 버튼: **"유지"**
- [ ] 구버전 문구("알림 설정" / "알림 끄기" / "알림 유지") 미노출

---

## TC-02: 팝업 "유지" → 설정 변경 없음

**사전 조건:** TC-01 팝업 노출 상태

**테스트 단계:**
1. 팝업에서 **"유지"** 버튼 탭

**검증:**
- [ ] 팝업 닫힘
- [ ] 마케팅 정보 수신 동의 토글 **ON 유지** (변경 없음)
- [ ] `AD_*` 알람 유지됨

---

## TC-03: 광수동 OFF → AD_ 알람만 삭제

**진입 경로:** 마이컬리 → 알림 설정 → 마케팅 정보 수신 동의

**사전 조건:**
- 회원 로그인
- 마케팅 수신 동의 **ON** 상태
- DataStore에 `AD_*` 알람 1개 이상
- DataStore에 `INFO_*` 알람 1개 이상

**테스트 단계:**
1. 알림 설정 진입
2. "마케팅 정보 수신 동의" OFF 토글 → 팝업에서 **"해제"** 탭
3. 저장 완료 확인
4. adb로 DataStore 조회

**검증:**
- [ ] `AD_*` 알람 → 삭제됨
- [ ] `INFO_*` 알람 → 유지됨
- [ ] AlarmManager에서 `AD_*` requestCode 알람 취소됨
- [ ] 서버 업데이트 **실패** 시 알람 삭제 **안 됨** (서버 성공 후에만 삭제)

**엣지케이스:**
- 이미 OFF 상태에서 다시 OFF → 알람 삭제 실행 안 됨 (상태 변화 없음)
- `AD_*` 알람 없을 때 OFF → 예외 없이 정상 완료

---

## TC-04: 광수동 ON → 알람 삭제 안 됨

**진입 경로:** 마이컬리 → 알림 설정 → 마케팅 정보 수신 동의

**사전 조건:**
- `AD_*` 알람 등록된 상태
- 마케팅 수신 동의 **OFF** 상태

**테스트 단계:**
1. "마케팅 정보 수신 동의" ON으로 변경 후 저장

**검증:**
- [ ] 팝업 미노출 (ON 전환 시 팝업 없음)
- [ ] `AD_*` 알람 → 유지됨 (삭제 안 됨)

---

## TC-05: 기기 알림 OFF 상태에서 토글 탭 → 기기 설정 유도 팝업 (회귀)

**사전 조건:**
- 기기 설정에서 앱 알림 **비허용** 상태

**테스트 단계:**
1. 마케팅 정보 수신 동의 토글 탭

**검증:**
- [ ] 광고성 알림 해제 팝업 **미노출**
- [ ] 기기 알림 설정 유도 팝업 정상 노출

---

## TC-06: 마수동 OFF (WebView) → AD_ 알람만 삭제

**진입 경로:** WebView → 마케팅 동의 체크박스 해제

**사전 조건:**
- WebView 마케팅 동의 ON 상태
- `AD_*` 알람 존재

**테스트 단계:**
1. WebView 마케팅 동의 체크박스 OFF
2. 팝업 확인 클릭

**검증:**
- [ ] `AD_*` 알람 → 삭제됨
- [ ] 마케팅 알림 변경 메시지 노출

---

## TC-07: 로그아웃 → 전체 알람 삭제

### 경로 A: 앱 내 로그아웃

**진입:** 마이컬리 → 설정 → 로그아웃

**사전 조건:**
- 회원 로그인
- `AD_*`, `INFO_*` 알람 각각 1개 이상

**테스트 단계:**
1. 로그아웃 버튼 클릭
2. 확인

**검증:**
- [ ] `AD_*`, `INFO_*` 알람 **모두** 삭제됨
- [ ] AlarmManager 등록 알람 모두 취소됨
- [ ] 다시 로그인 후 이전 알람 복원 안 됨

**엣지케이스:**
- 비회원 토큰 갱신 (`session.isGuest == true`) → `cancelAll()` 실행 **안 됨**, 알람 유지

### 경로 B: WebView 내 로그아웃

**진입:** WebView → JS 브릿지 logout 호출 화면

**검증:** 경로 A와 동일 (전체 알람 삭제)

---

## TC-08: 회원 탈퇴 (WV3200) → 전체 알람 삭제

**진입 경로:** WebView → 회원 탈퇴 완료 콜백 (`onSuccessUnRegister`)

**사전 조건:**
- 탈퇴 가능한 테스트 계정
- `AD_*`, `INFO_*` 알람 모두 등록

**테스트 단계:**
1. 마이컬리 → 계정 설정 → 회원 탈퇴 WebView 진입
2. 탈퇴 절차 완료

**검증:**
- [ ] 전체 알람 삭제됨
- [ ] Activity finish **이후**에도 DataStore 삭제 완료 (`applicationScope` 보장)

> **타이밍 주의:** `applicationScope.launch` 이므로 Activity 종료 후 약 300~600ms 뒤 DataStore 쓰기 완료.
> 탈퇴 직후 즉시 DataStore 조회 시 알람이 아직 남아있을 수 있음 — 잠시 대기 후 재확인.

---

## TC-09: 알람 없을 때 각 트리거 → 예외 없이 정상 완료

| 트리거 | 기대 결과 |
|--------|----------|
| 광수동 OFF (알람 없음) | 예외 없이 설정 저장 완료 |
| 로그아웃 (알람 없음) | 예외 없이 로그아웃 완료 |
| 탈퇴 (알람 없음) | 예외 없이 탈퇴 완료 |

---

## TC-10: AlarmManager 취소 실패 → DataStore는 정상 삭제

**시나리오:** requestCode 불일치 등으로 AlarmManager cancel이 실패하는 상황

**검증:**
- [ ] AlarmManager cancel 실패해도 DataStore에서 알람 삭제됨
- [ ] 해당 알람은 예약 시각에 한 번 울릴 수 있음 (허용된 trade-off)
- [ ] 이후 재등록은 안 됨

---

## TC-11: 연속 조작 (race condition)

**시나리오:** 알람 등록 중 광수동 OFF

**테스트 단계:**
1. WebView에서 알람 등록 트리거
2. 즉시 설정 화면에서 광수동 OFF

**검증:**
- [ ] 알람이 중복 남거나 일부만 삭제되는 이상 상태 없음
- [ ] DataStore 최종 상태 일관성 유지

---

## 회귀 체크리스트

- [ ] 알람 등록 (WebView setAlarm) 정상 동작
- [ ] 알람 수신 (AlarmManager 트리거 → 알림 노출) 정상 동작
- [ ] 광수동 OFF → ON → 알람 재등록 가능한지 확인
- [ ] 알림 설정 화면 전체 항목 저장/로드 정상 동작
- [ ] 비회원 상태에서 알림 설정 진입 시 크래시 없음

---

## Logcat 확인 포인트

```
# 알람 삭제 흐름
NotificationRepositoryImpl: deleteWebAlarmsByPrefix prefix: AD_
NotificationRepositoryImpl: deleteAllWebAlarms

# applicationScope DataStore 완료 확인
DataStore 관련 로그 (preferences_name_local_push)
```

---

## 관련 파일

| 파일 | 경로 | 역할 |
|------|------|------|
| 팝업 문구 리소스 | `features/src/main/res/values/language_packs.xml:348~351` | 광고성 알림 해제 팝업 문구 |
| 팝업 호출 | `features/.../notification/NotificationSettingsActivity.kt:showMarketingNotificationOffPopup()` | 팝업 노출 진입점 |
| DeleteAdAlarmsUseCase | `domain/.../usecase/notification/DeleteAdAlarmsUseCase.kt` | AD_ 알람 삭제 UseCase |
| DeleteAllWebAlarmsUseCase | `domain/.../usecase/notification/DeleteAllWebAlarmsUseCase.kt` | 전체 알람 삭제 UseCase |
| WebAlarmCancellerImpl | `features/.../web/bridge/common/user/WebAlarmCancellerImpl.kt` | AlarmManager + DataStore 취소 |
| NotificationRepositoryImpl | `data/.../repository/notification/NotificationRepositoryImpl.kt` | DataStore 읽기/쓰기 |
| NotificationSettingsViewModel | `features/.../notification/NotificationSettingsViewModel.kt` | 광수동 OFF 트리거 |
| KurlyWebViewViewModel | `features/.../web/base/viewmodel/KurlyWebViewViewModel.kt` | 로그아웃/탈퇴 트리거 |
| LogoutToGuestUseCase | `domain/.../usecase/user/LogoutToGuestUseCase.kt` | 로그아웃 시 전체 삭제 |
