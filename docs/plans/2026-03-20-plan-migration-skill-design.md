# `/plan-migration` 스킬 설계

## 개요

Jira 티켓을 입력받아 Compose 마이그레이션에 필요한 코드 흐름 분석을 수행하고, 결과를 Jira 코멘트로 등록하는 스킬.

**사용법:**
```
/plan-migration KMA-7041
/plan-migration https://kurly0521.atlassian.net/browse/KMA-7041
```

---

## 실행 흐름

```
1. 티켓 읽기
   Jira MCP → KMA-XXXX summary + description 파싱
   → 파일 경로/클래스명 명시 여부 확인

2. 코드 탐색 (general-purpose 에이전트)
   → 경로 명시 있으면 직접 사용
   → 없으면 티켓 키워드로 코드베이스 검색
   → 대상 Activity/Fragment + ViewModel + 관련 파일 수집

3. 8개 항목 분석 (에이전트 이어서)

4. 마크다운 결과 출력 → 사용자 확인

5. [Enter] Jira 코멘트 등록 / [e] 수정 후 등록
```

---

## 산출물: 8개 분석 항목

### 1. 파일 분류 (재사용 vs 신규 작성)
파일별 처리 방향을 테이블로 정리.

| 처리 | 의미 |
|------|------|
| 그대로 | 변경 없이 재사용 |
| 수정 | 일부 변경 필요 |
| 삭제 | Compose 전환 후 제거 |
| 새로 만들기 | 신규 Composable/파일 생성 |

### 2. ViewModel 상태 전체 목록
기존 ViewModel이 관리하던 StateFlow/MutableStateFlow/Channel 전체 나열.
각 상태가 이 화면에서 사용되는지 여부 명시 (Compose 전환 시 처리 판단 기준).

### 3. 데이터 흐름 다이어그램
```
진입점(Intent/SavedStateHandle) → init() → UseCase → StateFlow → Composable
사용자 인터랙션 → ViewModel 메서드 → 상태 업데이트 → 재렌더링
```

### 4. 기존 로직 중 ViewModel에 이미 있는 것
별도 포팅 불필요한 비즈니스 로직 명시.
(예: SINGLE/MULTI 선택 로직, 저장 로직 등)

### 5. 타겟 Compose 레이아웃 스케치
마이그레이션 후 목표 Composable 계층 구조를 텍스트 트리로 표현.

### 6. 유사 완성 화면 레퍼런스
이미 마이그레이션 완료된 유사 화면 파일 경로 제시.
(패턴 참고용)

### 7. 커밋 순서
작업을 어떻게 쪼갤지 순서 제안.
(예: 1. Activity 스텁 → 2. LazyColumn 본체 → 3. Dialog → 4. 구파일 정리)

### 8. 테스트 시나리오 목록
유저 행동 기반 체크 항목.
(예: 세그먼트 선택, 저장, 뒤로가기, 다이얼로그 등)

---

## 산출물 형태 (Jira 코멘트 예시)

```markdown
## 🔍 Compose 마이그레이션 분석

### 1. 파일 분류
| 파일 | 처리 |
|------|------|
| ListProfileActivity | 수정 (ComponentActivity로) |
| activity_list_profile.xml | 삭제 |
| ProfileCategoryAdapter | 삭제 |
| StepBodyContent.kt | 그대로 |
| ListProfileScreen.kt | 새로 만들기 |

### 2. ViewModel 상태 목록
| 상태 | 타입 | 이 화면 사용 |
|------|------|------------|
| isLoading | StateFlow<Boolean> | ✅ |
| categories | StateFlow<List<...>> | ✅ |
| currentPage | StateFlow<Int> | ❌ (StepProfile 전용) |
| uiEvent | Flow<StepProfileEvent> | ✅ |

### 3. 데이터 흐름
...

### 4. ViewModel에 이미 있는 로직
...

### 5. 타겟 레이아웃 구조
...

### 6. 레퍼런스 화면
...

### 7. 커밋 순서
...

### 8. 테스트 시나리오
...
```

---

## 구현 파일 위치

```
.claude/skills/plan-migration/
└── SKILL.md
```

---

## 제약 사항

- Jira MCP 필수 (티켓 읽기 + 코멘트 등록)
- 코드베이스 탐색은 `general-purpose` 에이전트 위임
- 코멘트 등록 전 사용자 확인 필수 (자동 등록 없음)
