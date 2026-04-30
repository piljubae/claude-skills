# `/plan-migration` Skill Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Jira 티켓을 입력받아 Compose 마이그레이션 코드 흐름 분석 8개 항목을 생성하고 Jira 코멘트로 등록하는 스킬 구현

**Architecture:** 스킬이 오케스트레이터 역할 — Jira MCP로 티켓 읽고, general-purpose 에이전트에 코드 탐색+분석 위임, 결과 확인 후 Jira MCP로 코멘트 등록.

**Tech Stack:** Claude Skill (SKILL.md), Jira MCP (`mcp__atlassian-jira__jira_get`, `mcp__claude_ai_Atlassian__addCommentToJiraIssue`), Agent tool (general-purpose)

**Design doc:** `docs/plans/2026-03-20-plan-migration-skill-design.md`

---

### Task 1: 스킬 디렉토리 및 SKILL.md 뼈대 생성

**Files:**
- Create: `.claude/skills/plan-migration/SKILL.md`

**Step 1: 디렉토리 생성 확인**

```bash
ls .claude/skills/
```

Expected: `code-review`, `commit`, `create-pr` 등 기존 스킬 목록 확인

**Step 2: SKILL.md 생성**

`.claude/skills/plan-migration/SKILL.md` 를 아래 내용으로 생성:

```markdown
---
name: plan-migration
description: Compose 마이그레이션 코드 흐름 분석 — Jira 티켓 기반으로 8개 항목 분석 후 코멘트 등록
argument-hint: [KMA-XXXX | Jira URL]
---

# Plan Migration Skill

## 0. --help 처리

`$ARGUMENTS`에 `--help` 포함 시 아래 출력 후 종료:

```
/plan-migration KMA-7041
/plan-migration https://kurly0521.atlassian.net/browse/KMA-7041

분석 항목:
1. 파일 분류 (재사용/수정/삭제/신규)
2. ViewModel 상태 전체 목록
3. 데이터 흐름 다이어그램
4. ViewModel에 이미 있는 로직
5. 타겟 Compose 레이아웃 스케치
6. 유사 완성 화면 레퍼런스
7. 커밋 순서
8. 테스트 시나리오 목록
```

## 1. 티켓 번호 파싱

`$ARGUMENTS`에서 티켓 번호 추출:

- URL 형식 (`https://...atlassian.net/browse/KMA-7041`) → `KMA-7041` 추출
- 티켓 키 형식 (`KMA-7041`) → 그대로 사용
- 추출 실패 시: "티켓 번호를 입력해주세요: /plan-migration KMA-XXXX" 출력 후 종료

## 2. Jira 티켓 읽기

Jira MCP `mcp__atlassian-jira__jira_get`으로 티켓 조회:

```
path: /rest/api/3/issue/{TICKET_KEY}
jq: fields.{summary: summary, description: description}
```

description에서 아래를 추출 시도:
- 파일 경로 (`.kt`, `.xml` 확장자)
- 클래스명 (`Activity`, `Fragment`, `ViewModel` 포함 단어)
- 화면 키워드 (summary에서 추출)

## 3. 코드 탐색 + 8개 항목 분석

Agent tool로 `general-purpose` 에이전트 호출:

```
subagent_type: general-purpose
description: Compose 마이그레이션 코드 흐름 분석
prompt: |
  아래 티켓 정보를 바탕으로 kurly-android 코드베이스를 탐색하여
  Compose 마이그레이션 분석 8개 항목을 작성하라.

  ## 티켓 정보
  - 티켓: {TICKET_KEY}
  - 제목: {TICKET_SUMMARY}
  - 파일 힌트: {EXTRACTED_FILES (없으면 "없음")}
  - 키워드: {KEYWORDS}

  ## 탐색 방법
  1. 파일 힌트가 있으면 해당 파일 직접 읽기
  2. 없으면 키워드로 Glob/Grep 탐색 → 대상 Activity/Fragment 파일 찾기
  3. 해당 ViewModel 파일 탐색
  4. 관련 Adapter, ViewHolder, XML 레이아웃 파악
  5. 이미 마이그레이션된 유사 화면 탐색 (features/ 내 Composable 파일)

  ## 출력 형식 (마크다운)

  ### 1. 파일 분류
  | 파일 | 처리 | 비고 |
  |------|------|------|
  | {파일명} | 그대로/수정/삭제/새로 만들기 | {간단한 이유} |

  ### 2. ViewModel 상태 전체 목록
  | 상태명 | 타입 | 이 화면 사용 여부 | 비고 |
  |--------|------|-----------------|------|
  | {name} | StateFlow<...> | ✅/❌ | {이유} |

  ### 3. 데이터 흐름
  텍스트 다이어그램으로 표현:
  진입점 → init → UseCase → StateFlow → UI
  사용자 액션 → ViewModel 메서드 → 상태 업데이트

  ### 4. ViewModel에 이미 있는 로직
  별도 포팅 없이 그대로 쓸 수 있는 로직 목록과 이유

  ### 5. 타겟 Compose 레이아웃 구조
  텍스트 트리로 표현:
  {ScreenName}
  ├── {Composable}
  │   └── {SubComposable}
  └── ...

  ### 6. 참고할 완성 화면
  유사한 패턴의 이미 마이그레이션된 화면 파일 경로 + 참고 포인트

  ### 7. 커밋 순서
  1. {첫 번째 커밋 내용}
  2. {두 번째 커밋 내용}
  ...

  ### 8. 테스트 시나리오
  유저 행동 기반으로 체크해야 할 시나리오 목록:
  - [ ] {시나리오 1}
  - [ ] {시나리오 2}
  ...
```

에이전트 결과를 `ANALYSIS_RESULT` 에 저장.

## 4. 결과 출력 + 사용자 확인

터미널에 아래 출력:

```
## /plan-migration {TICKET_KEY} 분석 완료

{ANALYSIS_RESULT}

---
Jira {TICKET_KEY}에 코멘트로 등록하시겠습니까?
[Enter] 등록  [e] 수정 후 등록  [s] 건너뛰기
```

## 5. Jira 코멘트 등록

사용자가 [Enter] 또는 [e] 선택 시:

Jira MCP `mcp__claude_ai_Atlassian__addCommentToJiraIssue`로 코멘트 등록:

```
cloudId: kurly0521.atlassian.net
issueIdOrKey: {TICKET_KEY}
body: {ANALYSIS_RESULT (ADF 또는 markdown 형식)}
```

등록 완료 후:
```
✅ KMA-XXXX에 코멘트가 등록되었습니다.
{Jira 티켓 URL}
```

[s] 선택 시: "등록을 건너뛰었습니다." 출력 후 종료.
```

**Step 3: 커밋**

```bash
git add .claude/skills/plan-migration/SKILL.md
git commit -m "feat: add /plan-migration skill skeleton"
```

---

### Task 2: 티켓 파싱 + Jira 읽기 검증

**Files:**
- Modify: `.claude/skills/plan-migration/SKILL.md` (섹션 1~2 정교화)

**Step 1: KMA-7041로 수동 테스트**

Claude 세션에서 실행:
```
/plan-migration KMA-7041
```

확인 항목:
- [ ] 티켓 번호 파싱 정상 (`KMA-7041` 추출)
- [ ] Jira MCP 호출 성공 (summary, description 읽힘)
- [ ] 파일 힌트 추출 (description에서 `.kt` 경로 또는 클래스명 감지)

**Step 2: URL 형식도 테스트**

```
/plan-migration https://kurly0521.atlassian.net/browse/KMA-7041
```

확인:
- [ ] URL에서 `KMA-7041` 정상 추출

**Step 3: 오류 케이스 확인**

```
/plan-migration
```

Expected: "티켓 번호를 입력해주세요" 출력 후 종료

**Step 4: 커밋**

```bash
git add .claude/skills/plan-migration/SKILL.md
git commit -m "fix: refine ticket parsing and Jira read in plan-migration"
```

---

### Task 3: 에이전트 분석 품질 검증

**Files:**
- Modify: `.claude/skills/plan-migration/SKILL.md` (섹션 3 프롬프트 조정)

**Step 1: KMA-7041 전체 실행**

```
/plan-migration KMA-7041
```

에이전트 분석 결과 확인:
- [ ] **항목 1** — 파일 테이블에 `ListProfileActivity`, `activity_list_profile.xml`, `StepBodyContent` 등 포함
- [ ] **항목 2** — `currentPage` 같은 미사용 상태가 ❌로 표시됨
- [ ] **항목 3** — 데이터 흐름이 `SavedStateHandle → UseCase → StateFlow → UI` 형태로 표현됨
- [ ] **항목 4** — `onSegmentClick()` SINGLE/MULTI 로직 언급됨
- [ ] **항목 5** — `LazyColumn`, `ProfileCategorySection` 등 Composable 계층 표현됨
- [ ] **항목 6** — 유사 완성 화면 경로 1개 이상 제시됨
- [ ] **항목 7** — 커밋 3개 이상 제시됨
- [ ] **항목 8** — 테스트 시나리오 5개 이상

**Step 2: 품질 미달 항목 프롬프트 조정**

빠진 항목이 있으면 에이전트 프롬프트에 해당 항목 탐색 지침 보강.

**Step 3: 커밋**

```bash
git add .claude/skills/plan-migration/SKILL.md
git commit -m "fix: improve agent prompt quality for plan-migration"
```

---

### Task 4: Jira 코멘트 등록 검증

**Files:**
- Modify: `.claude/skills/plan-migration/SKILL.md` (섹션 5 ADF 포맷 확인)

**Step 1: 코멘트 등록 테스트**

분석 결과 확인 후 [Enter] 입력 → Jira KMA-7041에 코멘트 등록 확인:
- [ ] Jira 티켓에 코멘트 생성됨
- [ ] 마크다운 테이블이 Jira에서 정상 렌더링됨
- [ ] 코멘트 URL 출력됨

**Step 2: 렌더링 문제 시 ADF 변환 적용**

마크다운이 Jira에서 깨질 경우, 섹션 5를 `addCommentToJiraIssue`의 ADF body 형식으로 변환하도록 프롬프트 수정.

**Step 3: 최종 커밋**

```bash
git add .claude/skills/plan-migration/SKILL.md
git commit -m "feat: complete plan-migration skill with Jira comment posting"
```

---

### Task 5: guide.md 작성

**Files:**
- Create: `.claude/skills/plan-migration/guide.md`

**Step 1: guide.md 생성**

`/commit`의 guide.md 포맷과 동일하게 작성:

```markdown
# /plan-migration 스킬 가이드

Jira 티켓 기반으로 Compose 마이그레이션 코드 흐름을 분석하고
결과를 Jira 코멘트로 등록하는 Claude Code 스킬입니다.

---

## 사용법

/plan-migration [KMA-XXXX | Jira URL] [--help]

| 옵션 | 설명 |
|------|------|
| KMA-XXXX | 티켓 번호 직접 입력 |
| Jira URL | 전체 URL 입력 (티켓 번호 자동 추출) |
| --help | 이 가이드 요약 출력 후 종료 |

---

## 분석 항목

| # | 항목 | 설명 |
|---|------|------|
| 1 | 파일 분류 | 재사용/수정/삭제/신규 구분 |
| 2 | ViewModel 상태 목록 | 기존 관리 상태 전체 인벤토리 |
| 3 | 데이터 흐름 | 진입점 → UseCase → StateFlow → UI |
| 4 | ViewModel 기존 로직 | 별도 포팅 불필요한 로직 |
| 5 | 타겟 레이아웃 구조 | Composable 계층 스케치 |
| 6 | 레퍼런스 화면 | 참고할 완성 화면 경로 |
| 7 | 커밋 순서 | 작업 분할 제안 |
| 8 | 테스트 시나리오 | 유저 행동 기반 체크리스트 |

---

## 실행 예시

/plan-migration KMA-7041

🔍 KMA-7041 티켓 읽는 중...
📂 코드베이스 탐색 중...

## 🔍 Compose 마이그레이션 분석

### 1. 파일 분류
| 파일 | 처리 | 비고 |
...

### 8. 테스트 시나리오
- [ ] 프로필 재진입 시 기존 선택값 유지
...

---
Jira KMA-7041에 코멘트로 등록하시겠습니까?
[Enter] 등록  [e] 수정 후 등록  [s] 건너뛰기

✅ KMA-7041에 코멘트가 등록되었습니다.

---

## 에러 상황

### 티켓을 찾을 수 없는 경우
KMA-XXXX 티켓을 찾을 수 없습니다. 티켓 번호를 확인해주세요.

### Jira MCP 미연결
Jira MCP가 설정되지 않았습니다.
kurly-android/.mcp.json 설정을 확인해주세요.

### 코드베이스에서 파일을 찾지 못한 경우
티켓 키워드로 관련 파일을 찾지 못했습니다.
티켓 description에 파일 경로나 클래스명을 추가하면 더 정확한 분석이 가능합니다.

---

## 관련 문서

- **[SKILL.md](./SKILL.md)** — 스킬 기술 명세
- **[CLAUDE.md](../../../CLAUDE.md)** — 프로젝트 가이드라인
```

**Step 2: 커밋**

```bash
git add .claude/skills/plan-migration/guide.md
git commit -m "docs: add guide.md for plan-migration skill"
```

---

### Task 6: CLAUDE.md 스킬 등록

**Files:**
- Modify: `CLAUDE.md`

**Step 1: CLAUDE.md의 스킬 목록 섹션에 추가**

기존 `### /code-review` 섹션 패턴과 동일하게:

```markdown
### /plan-migration

Jira 티켓 기반 Compose 마이그레이션 코드 흐름 분석.
분석 8개 항목 생성 후 Jira 코멘트로 등록.

**사용법:**
/plan-migration KMA-XXXX
/plan-migration https://kurly0521.atlassian.net/browse/KMA-XXXX
```

**Step 2: 커밋**

```bash
git add CLAUDE.md
git commit -m "docs: register plan-migration skill in CLAUDE.md"
```
