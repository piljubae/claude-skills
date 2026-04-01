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

## 에이전트

| 에이전트 | 역할 |
|---------|------|
| `compose-design-analyzer` | 코드 분석 → `design-diff-report.md` 생성 |
| `compose-design-fixer` | report 보고 Compose 코드 수정 + 빌드 검증 |
| `compose-screenshot-writer` | uiautomator2 스크립트 생성 + 스크린샷 캡처 |

---

## 설치

### 프로젝트별 설치

```bash
# 스킬
mkdir -p .claude/skills
cp -r .claude/skills/design-validate .claude/skills/

# 에이전트
mkdir -p .claude/agents
cp .claude/agents/compose-design-*.md .claude/agents/
```

### 전역 설치 (모든 프로젝트에서 사용)

```bash
# 스킬
mkdir -p ~/.claude/skills
cp -r .claude/skills/design-validate ~/.claude/skills/

# 에이전트
mkdir -p ~/.claude/agents
cp .claude/agents/compose-design-*.md ~/.claude/agents/
```

### 심볼릭 링크로 설치 (이 레포에서 바로 사용)

```bash
ln -sf $(pwd)/.claude/skills/design-validate ~/.claude/skills/design-validate
ln -sf $(pwd)/.claude/agents/compose-design-analyzer.md ~/.claude/agents/compose-design-analyzer.md
ln -sf $(pwd)/.claude/agents/compose-design-fixer.md ~/.claude/agents/compose-design-fixer.md
ln -sf $(pwd)/.claude/agents/compose-screenshot-writer.md ~/.claude/agents/compose-screenshot-writer.md
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
