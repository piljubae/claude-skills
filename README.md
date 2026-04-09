# claude-skills

Personal Claude Code skills and agents for Android/Compose development.

## Skills

### `/design-validate` — Compose Migration Design Validator

Compose 마이그레이션 후 시각적 차이를 자동으로 찾아 수정하는 스킬.

#### 동작 방식

```
origin/develop 코드 분석 (or Figma/production)
    ↓
design-diff-report.md 생성
    ↓
Compose 코드 자동 수정
    ↓
빌드 검증
```

#### 사용법

```bash
/design-validate <ScreenName> [--before=develop|production|figma:<url>] [--screenshot]
/design-validate <ScreenName> [--package=com.example.app.debug] [--build-cmd="./gradlew :app:compileDebugKotlin"]
```

#### Code Analyzer 체크리스트 (7개)

분석 시 반드시 확인하는 항목:

1. **레이아웃 XML** — padding, margin, textSize, cornerRadius 등
2. **ItemDecoration** — 섹션 간 간격 (Decorator.kt 탐색)
3. **Adapter/ViewHolder** — dynamic visibility, spanCount
4. **Activity/Fragment** — addItemDecoration, programmatic padding
5. **styles.xml** — 참조된 스타일 값
6. **drawable** — gradient, shape, layer-list
7. **Color token** — @color/xxx → Design System 토큰 매핑

---

### `/review-radar` — AI Code Review Quality Analyzer

머지된 PR의 AI·사람 코멘트를 비교 분석해 `/code-review` 스킬의 누락·오탐 패턴을 파악하고, 에이전트 파일별 개선안(rule 초안 포함)을 도출하는 스킬.

#### 동작 방식

```
Phase 1: PR 코멘트 수집 (GitHub GraphQL)
    ↓ 병렬
Phase 2a: 오탐 분석 (거절된 AI 코멘트 → 프롬프트 수정 필요 여부 판정)
Phase 2b: 누락 분석 (사람·growth AI가 잡았지만 우리가 놓친 이슈 → rule 초안 생성)
    ↓
리포트 저장 (rule 초안 포함)
```

#### 사용법

```bash
/review-radar                          # 최근 14일
/review-radar --days 21                # 최근 21일
/review-radar --repo owner/repo        # 레포 지정
/review-radar --help                   # 사용법 출력
```

#### 주요 기능

- **오탐 판정 3분류**: `prompt-issue` (프롬프트 수정 필요) / `communication` (AI 맞음, 작성자 거절) / `context-dependent` (외부 판단 불가)
- **플랫폼 API 리서치**: 플랫폼 동작 관련 거절 시 AndroidManifest + 공식 API 계약 종합 확인 후 판정
- **growth-code-review 비교**: 외부 AI가 잡았지만 우리가 놓친 실질 이슈 분류
- **rule 초안 자동 생성**: 2건 이상 반복 누락 패턴에 대해 에이전트 파일을 읽고 즉시 붙여넣을 수 있는 rule 텍스트 생성
- **이모지 반응 기반 감정 분류**: 답글 없이 👍만 눌러도 `accept`로 포착

---

## 에이전트

| 에이전트 | 역할 |
|---------|------|
| `compose-design-analyzer` | 코드 분석 → `design-diff-report.md` 생성 |
| `compose-design-fixer` | report 보고 Compose 코드 수정 + 빌드 검증 |
| `compose-screenshot-writer` | uiautomator2 스크립트 생성 + 스크린샷 캡처 |
| `review-radar-collector` | PR 코멘트 수집 (GraphQL, source/sentiment/reactions 분류) |
| `review-radar-false-positive` | 오탐 분석 — 코드·플랫폼 리서치 기반 판정 |
| `review-radar-coverage-gap` | 누락 분석 — 반복 패턴 진단 + rule 초안 작성 |

---

## 설치

### 프로젝트별 설치

```bash
# 스킬
mkdir -p .claude/skills
cp -r .claude/skills/design-validate .claude/skills/
cp -r .claude/skills/review-radar .claude/skills/

# 에이전트
mkdir -p .claude/agents
cp .claude/agents/compose-design-*.md .claude/agents/
cp .claude/agents/review-radar-*.md .claude/agents/
```

### 전역 설치 (모든 프로젝트에서 사용)

```bash
# 스킬
mkdir -p ~/.claude/skills
cp -r .claude/skills/design-validate ~/.claude/skills/
cp -r .claude/skills/review-radar ~/.claude/skills/

# 에이전트
mkdir -p ~/.claude/agents
cp .claude/agents/compose-design-*.md ~/.claude/agents/
cp .claude/agents/review-radar-*.md ~/.claude/agents/
```

### 심볼릭 링크로 설치 (이 레포에서 바로 사용)

```bash
# design-validate
ln -sf $(pwd)/.claude/skills/design-validate ~/.claude/skills/design-validate
ln -sf $(pwd)/.claude/agents/compose-design-analyzer.md ~/.claude/agents/compose-design-analyzer.md
ln -sf $(pwd)/.claude/agents/compose-design-fixer.md ~/.claude/agents/compose-design-fixer.md
ln -sf $(pwd)/.claude/agents/compose-screenshot-writer.md ~/.claude/agents/compose-screenshot-writer.md

# review-radar
ln -sf $(pwd)/.claude/skills/review-radar ~/.claude/skills/review-radar
ln -sf $(pwd)/.claude/agents/review-radar-collector.md ~/.claude/agents/review-radar-collector.md
ln -sf $(pwd)/.claude/agents/review-radar-false-positive.md ~/.claude/agents/review-radar-false-positive.md
ln -sf $(pwd)/.claude/agents/review-radar-coverage-gap.md ~/.claude/agents/review-radar-coverage-gap.md
```

---

## 프로젝트 특화 설정

`--package`와 `--build-cmd`를 매번 입력하지 않으려면,
프로젝트의 `.claude/CLAUDE.md`에 기본값을 명시할 수 있습니다:

```markdown
## design-validate 기본값
- 앱 패키지: com.example.app.debug
- 빌드 명령: ./gradlew :app:compileDebugKotlin
```
