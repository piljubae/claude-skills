# /feature-plan 사용 가이드

## 사용법

```
/feature-plan KMA-XXXX
/feature-plan https://kurly0521.atlassian.net/browse/KMA-XXXX
/feature-plan KMA-XXXX --resume
```

## 동작 순서

1. Jira 티켓 + 연결 문서(Confluence PRD, Figma, 이벤트 로그 설계서) 자동 수집 → 4개 변수(DOC_API_SPEC / DOC_SCREEN_SPEC / DOC_EVENT_SPEC / DOC_POLICY)로 분리 저장
2. 4개 변수 교차 검증 → 불일치·모순 발견 시 ❓ 항목 생성 → 확인 (CP1, ❓=0이면 자동 진행)
3. 코드 영향 분석 + 1차 구현 스텝 초안 → 확인 (CP2, ❓=0이면 자동 진행)
4. 기획자 / Android Architect / QA 병렬 검토 + event-snapshot → BI 검토
5. 확인 필요 이슈만 제시 (CP3), 나머지는 자동 반영
6. 단위 테스트 시나리오 + Instrumented Test 플랜 + 구현 스텝 + 검증 플랜 → `docs/plans/` 저장

## 출력

- `docs/plans/YYYY-MM-DD-KMA-XXXX-plan.md`
- Jira description 업데이트 (선택)

## 체크포인트

| CP | 내용 | 자동 진행 조건 |
|----|------|--------------|
| CP1 | 수집 문서 확인 + ❓ 기획서/Figma 불명확 항목 | ❓=0이면 자동 진행 |
| CP2 | 1차 구현 스텝 + ❓ 코드 탐색 발견 항목 | ❓=0이면 자동 진행 |
| CP3 | 🔴 확인 필요 이슈만 제시 (즉시반영은 자동 처리) | 항상 정지 |

## 세션 중단 및 재개 (`--resume`)

CP1/CP2에서 외부 확인이 필요한 경우 `[s]`로 초안 저장 후 세션 종료 가능.

```
/feature-plan KMA-XXXX --resume
```

재개 시 Confluence 재수집 여부 확인 후 저장된 ❓ 항목을 순서대로 질문.
답변에 Slack URL 또는 Confluence URL 입력 시 자동 fetch 후 반영.

## 팁

- Confluence PRD / Figma / 이벤트 로그 설계서 링크가 Jira 티켓 description에 있으면 자동 수집
- 링크가 없어도 티켓 내용만으로 동작
- CP3의 🔴 항목 목록은 Slack에 그대로 복사해 공유 가능
- `docs/plans/` 는 `.gitignore` 에 추가 권장 (로컬 작업 문서)
