# KMA-7041 ListProfileActivity Compose 마이그레이션 디자인 검증

날짜: 2026-03-31
브랜치: `feature/KMA-7041-compose-list-profile`

## 목표

Production(View 기반) vs Beta(Compose 전환) ListProfileActivity 화면을 비교해
시각적 차이를 발견하고 수정한다.

## 팀 구성

| 에이전트 | 역할 |
|---------|------|
| **Code Analyzer** | git 히스토리에서 원본 XML/View 코드 추출 → Compose 코드와 비교 → 차이점 리포트 생성 |
| **Script Writer** | uiautomator2 Python 탐색 스크립트 작성 (두 앱 공통 경로 자동화 + screencap) |
| **Fix Applier** | 차이점 리포트 기반 Compose 코드 수정 |

## 실행 단계

### Phase 1 — 병렬 분석 (Code Analyzer + Script Writer)

**Code Analyzer 산출물** (`docs/plans/design-diff-report.md`):
- 색상/토큰 차이 (XML hardcoded → KPDS 토큰 미적용 여부)
- Typography 차이
- Spacing/padding 수치 차이
- 레이아웃 구조 차이 (존재하지 않거나 추가된 뷰)
- KPDS 값으로 대체 불가한 경우 근사치 목록 별도 기재

**Script Writer 산출물** (`scripts/capture_list_profile.py`):
- `uiautomator2` 기반 Python 스크립트
- 대상 기기: `R3CT10A3JCE` (실기기)
- 패키지: `com.dbs.kurly.m2` (production), `com.dbs.kurly.m2.beta` (beta)
- 탐색 경로 (두 앱 동일): 마이컬리 탭 → 커뮤니티&스타일 → 프로필 클릭 → ListProfileActivity
- screencap 후 로컬로 pull

### Phase 2 — Before 스크린샷

스크립트 실행 조건: 두 앱 모두 로그인 완료 상태

저장 경로:
- `docs/screenshot/before_production.png`
- `docs/screenshot/before_beta.png`

### Phase 3 — Fix Applier

입력: Code Analyzer 리포트 + before 스크린샷 비교 결과
수정 대상: `features/src/main/java/.../siteprofile/list/ListProfileScreen.kt` 및 관련 Composable
우선순위: KPDS 토큰 우선 적용, 근사치 불가피한 경우 코멘트 + 별도 목록

### Phase 4 — After 스크린샷

Beta 앱 재빌드 (`./gradlew :features:installBetaDebug`) 후 스크립트 재실행

저장 경로:
- `docs/screenshot/after_beta.png`

## 성공 기준

- `after_beta.png`가 `before_production.png`와 시각적으로 일치
- KPDS 비적용 값 목록이 문서화됨

## 기기/패키지 정보

| 항목 | 값 |
|------|-----|
| 기기 serial | `R3CT10A3JCE` |
| Production 패키지 | `com.dbs.kurly.m2` |
| Beta 패키지 | `com.dbs.kurly.m2.beta` |
| 스크린샷 저장 경로 | `docs/screenshot/` |
