---
name: universal-flow-document
description: 코드·업무 규칙에서 상세 흐름, 처리 주체, 상태 변화, 실패 시나리오와 근거를 추출하여 인터랙티브 차트와 설명 문서를 함께 생성·갱신한다.
---

# Universal Flow Document

> 목적: 코드·설정·업무 근거에서 흐름을 추출해 동일 데이터의 차트와 단계별 설명을 생성·갱신한다.
> 출력물: FlowDocument JSON, 자체 포함 HTML, 근거와 검수 기록.
> 출처: 사용자 제공 universal-flow-document의 의미 모델을 참고해 하네스 규격과 순수 Node 실행기로 재작성했다. 반입 범위는 `skills/universal-flow-document/REFERENCE_PROVENANCE.md`에 기록한다.

## 0. Harness Control Rule

- 이 스킬은 `00.HARNESS_RULES.md`의 하위 모듈이다.
- 충돌 시 중단하고 상위 규칙을 따른다. 위험 작업 WARN은 사용자 확인 전 스킬 단독으로 진행하지 않는다.

## 1. Trigger

- 코드·업무·이벤트·배치 흐름의 차트와 단계별 설명을 함께 만들거나 갱신할 때.
- 사용자가 기존 FlowDocument를 최신 근거에 맞추도록 요청할 때.
- 이 스킬의 흐름 탐색·시나리오 선택·HTML 표현 기준 자체를 보강할 때.

## 2. Do Not Trigger

- 한 문장으로 설명되는 동작, 단순 코드 수정, 화면 디자인 자체의 요청.
- 정적인 짧은 다이어그램만으로 충분하고 인터랙티브 문서를 요청하지 않은 경우.
- 코드 저장소가 있다는 이유만으로 모든 기능의 흐름 문서를 자동 생성하지 않는다.

## 3. Required Inputs

- 대상 범위·독자, 근거 코드/설정/사용자 지정 업무 문서와 버전.
- 갱신이면 기존 JSON과 변경 근거. 실행기 사용에는 Node 20 이상.
- 실행기는 `skills/universal-flow-document/scripts/flow-document.mjs`, 브라우저 동작은 scripts/flow-viewer.js, 표현 자산은 styles/flow.css가 담당한다(두 자산 경로는 이 스킬 폴더 기준).
- 데이터 형식은 `skills/universal-flow-document/REFERENCE_FORMAT.md`, 분석·표현은 `skills/universal-flow-document/REFERENCE_AUTHORING.md`를 읽는다. JSON schema는 `skills/universal-flow-document/templates/flow-document.schema.json`, 예시는 `skills/universal-flow-document/references/decision.json`이다.

### HTML 생성·표현 규칙 수정 시 추가 읽기

| 목적 | 문서 |
|---|---|
| 전체·완료·실패 버튼, 하위 경로 선택, 왼쪽 검색·목록 | `skills/universal-flow-document/REFERENCE_INTERACTION.md` |
| 기존 차트 계열 색상, CSS 토큰, 패널·카드·반응형 | `skills/universal-flow-document/REFERENCE_VISUAL.md` |
| 생성기 지원 상태와 0/1/여러 경로·검색·화면 검수 | `skills/universal-flow-document/REFERENCE_UI_REVIEW.md` |

JSON 분석만 할 때는 HTML 전용 문서를 로딩하지 않는다. 각 지침 문서는 200줄 이내로 유지하고 넘기 전에 책임별 보조 문서로 분리해 이 표 또는 해당 소유 문서에서 연결한다. 같은 규칙을 여러 파일에 복제하지 않는다.

## 4. Procedure

1. 범위와 기준을 정한다. 실제 구현 설명은 코드를, 요구된 업무 규칙은 지정 명세를 근거로 삼는다. 둘이 다르면 실제 동작·요구 동작·개선 제안을 구분하고 임의로 일치시키지 않는다.
2. Entry Point 목록과 포함·제외 범위를 먼저 남긴다. 호출 경로에서 검증·권한·상태 조회/변경·트랜잭션·외부 호출·비동기·종료를 추적한다. 사용자 결과를 바꾸는 상태 변화와 실패 경계는 별도 단계로 남긴다. 클래스마다 노드를 만들지 않는다.
3. 상세 설명을 요청했거나 기존 상세 차트를 재현·보강할 때 meta.detailLevel을 detailed로 둔다. 주요 단계의 owner·description·outputs·source, 판단 노드의 condition을 작성한다. 상태 변경은 stateChange, 실제 실패는 failureCases로 발생 단계·결과·다음 행동·시나리오를 연결한다. 주의사항을 실행 실패로 대신하지 않는다. API 계약이 있으면 선택 확장을 사용한다. 세부 기준은 `skills/universal-flow-document/REFERENCE_AUTHORING.md`와 `skills/universal-flow-document/REFERENCE_FORMAT.md`를 따른다.
4. 갱신에서는 Flow/Node ID를 유지하며 근거가 달라진 부분만 수정한다. 제거 근거와 변경 수를 기록하고 사용자 변경을 보존한다.
5. 저장소 루트에서 `node GENERAL_HARNESS/skills/universal-flow-document/scripts/flow-document.mjs validate <flow.json>`을 실행한다. 구조와 내용 누락을 검사하되 추출한 실제 분기·Entry 목록과 FlowDocument를 별도로 대조한다. detailed에서는 핵심 설명 누락을 오류로 취급한다. overview에서도 설명·시나리오 누락을 경고한다. 구조 PASS는 범위 누락이나 사실 정확성을 인증하지 않는다.
6. HTML 작업이면 추가 읽기 표의 UI 계약과 생성기 지원 상태를 확인한 뒤 `node GENERAL_HARNESS/skills/universal-flow-document/scripts/flow-document.mjs build <flow.json> <output.html>`로 생성한다. 내장 뷰어가 새 계약을 충족하지 않으면 재현 가능한 생성 경로부터 맞춘다. 단일 시나리오 select 초안을 최종본으로 전달하지 않는다. 기존 출력 덮어쓰기는 승인된 출력물에만 `--overwrite`를 명시한다. 입력 파일과 출력 파일은 같을 수 없다. 스킬 자산·원본 자료를 출력 경로로 쓰지 않는다.
7. HTML 생성 시 `skills/browser-qa/SKILL.md`와 UI 검수 문서로 결과 버튼·세부 경로, 왼쪽 검색·분류·선택 유지, 차트 전체 높이 펼침, 확대·맞춤, 주소 복원, 주체·근거·계약 표시, 노드와 설명 연결, 키보드·반응형·색상 상태를 확인한다. 차트 컨테이너에 세로 스크롤을 만들지 않고 페이지 스크롤로 처음부터 끝까지 읽게 한다. 코드 변경 때는 잘못된 URL·누락 상세·실패 연결 회귀를 포함한다. 브라우저 도구가 없거나 정책상 열 수 없는 원본은 우회하지 않고 정적 분석/미검증 범위를 기록한다.
8. 생성/변경/삭제 Flow 수, 실제 근거와 미확인, 구조 검사와 시각·의미 검수 결과를 분리해 보고한다. 구조 PASS만으로 의미 검수 완료를 주장하지 않는다.

스킬 문서만 수정하라는 요청에서는 지침·연결·검수 기준을 수정하고 필요한 문서 검사를 수행한다. 데이터 추출·HTML 재생성·생성기/CSS 변경·브라우저 UI 검수는 자동으로 수행하지 않는다. 실제 생성기 지원과 앞으로 적용할 지침을 구분해 보고한다.

## 5. Quality Gate

| 판정 | 기준 |
|---|---|
| PASS | 구조 검사 통과, 주요 단계·분기의 근거 확인, 차트와 설명 일치, HTML이면 실제 상호작용·반응형 검수 증거 확보 |
| WARN | 구조는 유효하지만 일부 근거·브라우저 검수가 미확인이며 범위와 한계를 표시함 |
| FAIL | 빈 흐름·깨진 연결·불가능한 시나리오, 허위 근거/성공 분기, 차트와 설명 불일치, 상세 요청에서 핵심 정보 누락, HTML 납품에서 결과 버튼·왼쪽 검색·차트 전체 높이 펼침 계약 미충족 |

## 6. Output Format

- 기준 소스·버전·범위:
- Flow 수와 추가/변경/삭제 수(갱신 시):
- JSON·HTML 경로:
- 실행 명령·종료 코드·구조 오류/경고:
- 브라우저·의미 검수 증거:
- 확인 필요 및 PASS/WARN/FAIL:

## 7. Handoff

흐름 설명은 `gates/document-gate.md`, API·보안·결제 등 내용이 함께 해당하면 `skills/quality-gate/SKILL.md`에서 기존 누적 Gate를 선택한다. 생성기 코드를 바꿨으면 `skills/verification-loop/SKILL.md`, 기록은 `06.REPORT_TEMPLATE.md`를 따른다.

## 8. Anti-Patterns

- 설명 문서 생성 과정에서 제품 코드를 고치기.
- 구현을 실제 업무 계약으로 간주해 명세 불일치를 숨기기.
- 성공 경로만 검증하거나 연결되지 않은 노드를 무시하기.
- 차트용 데이터와 설명용 데이터를 따로 작성하기.
- 모든 경로를 첫 화면의 단일 select로 합치거나 검색을 숨겨 목록 탐색을 어렵게 만들기.
- 차트에 max-height와 overflow-y를 적용해 긴 흐름을 내부 세로 스크롤에 가두기.
- 문서 규칙을 추가한 것을 기존 HTML·생성기의 구현 완료로 보고하기.
