# 작업 리포트: 플로우차트 전체 높이 규칙

> 작성일: 2026-09-22  
> 패키징/배포일: 해당 없음  
> 작업 브랜치: codex/harness-skill-reinforcement  
> 커밋/PR: 76d28b4 / PR 미생성  
> 상태 기록 버전: 1  
> 상태 확인 시각: 2026-09-22T15:34:33+09:00  
> 구현 상태: 완료  
> 구현 근거: 커밋 76d28b4의 universal-flow-document 진입 규칙·작성·표현·UI 검수 문서 변경  
> 로컬 검증 상태: 완료  
> 로컬 검증 대상: 커밋 76d28b4  
> 로컬 검증 근거: validate-docs, validate-skills, validate-references 종료 코드 0과 문서별 200줄 이하 확인  
> 병합 상태: 미수행  
> 병합 대상: origin/main  
> 병합 근거: 76d28b4를 origin/codex/harness-skill-reinforcement에 push; PR·merge 미수행  
> 배포 상태: 미수행  
> 배포 근거: 스킬 문서 규칙 변경 범위이며 배포 요청 없음  
> 실제 연동 상태: 해당 없음  
> 실제 연동 근거: 생성 HTML·CSS·뷰어를 수정하지 않은 규칙 문서 작업  
> 작업 범위: S  
> 적용 스킬: universal-flow-document  
> 적용 Gate: Skill Gate, Document Gate  
> 위험도: 일반  
> 위험 작업 여부: 아니오

## 0. 작업 범위 확인

| 항목 | 내용 |
|---|---|
| 요청 요약 | 긴 플로우차트를 내부 세로 스크롤 없이 전체 높이로 펼치는 규칙 추가 |
| 수정 대상 | SKILL, REFERENCE_AUTHORING, REFERENCE_VISUAL, REFERENCE_UI_REVIEW |
| 제외 대상 | 기존 JSON·HTML·생성기·뷰어·CSS와 브라우저 구현 검수 |
| 근거 | 사용자가 현재 상다리 차트의 내부 세로 스크롤을 직접 확인한 뒤 규칙 변경 요청 |
| 적용 스킬/Gate | universal-flow-document / Skill Gate, Document Gate |
| 위험도 | 일반 |
| 검증 방법 | 문서 간 소유권·상충 대조, 문서·스킬·참조 검사, 줄 수 확인 |
| 한계 | 기존 산출물은 새 규칙을 아직 구현하지 않음 |

## 1. 작업 요약

- 차트 컨테이너가 SVG 전체 렌더링 높이만큼 늘어나도록 규정했다.
- max-height, 고정 높이, overflow-y:auto/scroll로 차트를 내부 세로 스크롤에 가두는 방식을 금지했다.
- 긴 흐름은 페이지의 자연스러운 세로 스크롤로 읽게 하고, 가로 이동은 좁은 화면에서 가독성 유지에 필요한 경우만 차트 영역에 허용했다.
- 모바일에서도 내부 세로 스크롤을 다시 만들지 않도록 했다.
- 가장 긴 실제 흐름에서 컨테이너와 SVG 높이 및 마지막 노드 노출을 측정하는 검수 항목을 추가했다.

## 2. 변경 파일

| 파일 | 변경 내용 |
|---|---|
| skills/universal-flow-document/SKILL.md | 필수 브라우저 검수·FAIL·금지 패턴에 전체 높이 규칙 추가 |
| skills/universal-flow-document/REFERENCE_AUTHORING.md | 좁은 화면 수동 검수를 페이지 세로 스크롤 기준으로 수정 |
| skills/universal-flow-document/REFERENCE_VISUAL.md | 전체 높이·세로 스크롤 금지·조건부 가로 이동의 CSS 계약 정의 |
| skills/universal-flow-document/REFERENCE_UI_REVIEW.md | 긴 차트 인수 시나리오와 측정·FAIL 기준 추가 |

## 3. 검증 결과

| 검증 항목 | 결과 | 비고 |
|---|---|---|
| 문서 구조 | PASS | Markdown 101개 검사 |
| 스킬 구조 | PASS | 활성 스킬 20개 검사 |
| 내부 참조 | PASS | 검사 대상 Markdown 101개 참조 해결 |
| 문서 크기 | PASS | 변경 문서 54~88줄, 모두 200줄 이하 |
| 규칙 정합성 | PASS | 차트 세로 이동은 페이지, 왼쪽 긴 목록은 패널 내부 스크롤로 역할 분리 |

## 4. Checklist 결과

| Checklist | 결과 | Report 반영 |
|---|---|---|
| Skill Gate | PASS | 핵심 규칙은 SKILL에, 상세 CSS·검수 기준은 연결된 참조 문서에 배치 |
| Document Gate | PASS | 적용 범위·금지 방식·예외·검수 방법을 명시 |

## 5. 발견된 문제

| 심각도 | 문제 | 처리 |
|---|---|---|
| Major | 기존 규칙이 차트 내부 가로·세로 스크롤을 모두 허용 | 세로는 금지하고 가로만 조건부 허용하도록 수정 |
| Major | 기존 상다리 HTML의 max-height와 overflow:auto가 새 요구와 충돌 | 이번에는 구현하지 않았음을 명시하고 후속 HTML 갱신 시 FAIL 조건으로 연결 |

## 6. 미해결 항목

- 공용 CSS와 기존 상다리·하네스 HTML은 아직 새 전체 높이 규칙을 적용하지 않았다.

## 7. Working Context 반영 여부

- 반영 필요: 예
- 반영 내용: UI 지침은 전체 높이 표시로 변경됐으며 현재 생성기 구현은 후속 대상이다.

## 8. 다음 작업

- 다음 HTML 생성·갱신 요청에서 공용 CSS의 차트 max-height·세로 overflow를 제거하고 가장 긴 흐름을 브라우저에서 검수한다.
