# Reference: FlowDocument 형식과 실행

> `skills/universal-flow-document/SKILL.md`의 보조 문서다. JSON 작성 및 실행기 사용 때 읽는다.

## 계약

`skills/universal-flow-document/templates/flow-document.schema.json`이 입력 형식을 소유한다. 실행기는 이 스키마에서 사용하는 type, required, properties, additionalProperties, items, enum, minLength, minItems, minimum, maximum, pattern 키워드를 검사한다. 범용 JSON Schema 엔진이 아니며 지원하지 않는 스키마 키워드는 오류로 거부한다.

- meta.title과 하나 이상의 flows가 필요하다.
- meta.detailLevel은 overview/detailed다. 생략한 기존 자료는 overview와 같이 취급하며 설명·시나리오 누락을 WARN으로 표시한다. detailed는 실행 노드의 description/owner/outputs/source, decision의 condition, 흐름 coverage와 시나리오를 요구한다. 왜 필요한지가 자명하면 why는 생략할 수 있다.
- 각 흐름은 고유 id, title, summary, 비어 있지 않은 nodes와 edges를 가진다.
- 노드에는 id/type/title/row/column이 필요하다. id는 영문·숫자·하이픈·밑줄로 구성하고 row는 0~1000, column은 -100~100 정수다. 같은 위치에 둘 수 없다.
- 노드 ID와 선 ID는 흐름 안에서 고유하다. note는 실행 경로와 시나리오에 연결하지 않는다.
- 시작점과 종료점 또는 명시된 지속 스트림 경계가 있어야 한다. 모든 실행 노드는 시작점에서 도달 가능하며 종료/경계로 이어져야 한다. success/failure 종료점에는 나가는 선이 없다. stream에만 openEnded: true를 쓸 수 있고 description에 연결이 계속 유지되는 관측 범위를 설명해야 한다.
- decision에는 서로 다른 비어 있지 않은 라벨의 두 분기 이상이 필요하다.
- 시나리오 path는 시작점부터 kind와 같은 success/failure 종료까지 실제 연결된 순서다. 지속 스트림 경계에서 끝나는 경우 kind는 ongoing이며 성공 종료로 표시하지 않는다. ID가 고유해야 한다. 같은 두 노드 사이에 여러 선이 있으면 edgePath에 정확한 선 ID 순서를 넣는다.
- source가 없는 주요 단계와 긴 제목은 경고다. 경고를 검토하지 않고 의미 검수 PASS로 보고하지 않는다.

## 명령과 결과

Node 20 이상, 추가 패키지 없음. 저장소 루트에서 실행한다.

```sh
node GENERAL_HARNESS/skills/universal-flow-document/scripts/flow-document.mjs validate path/to/flow.json
node GENERAL_HARNESS/skills/universal-flow-document/scripts/flow-document.mjs build path/to/flow.json path/to/output.html
```

결과 JSON의 status는 구조 검사 PASS/WARN/FAIL이며 의미 품질 Gate를 대체하지 않는다. 오류 또는 IO 실패는 비정상 종료한다. 경고만 있으면 종료 0이고 결과에 WARN을 남긴다. build는 유효성 오류가 있으면 출력하지 않는다. 기존 파일은 기본 보존하고 승인된 출력 갱신에만 --overwrite를 사용한다. 생성 HTML에는 외부 CDN·네트워크 요청이 없다.

build의 성공은 새 결과 버튼·왼쪽 탐색 계약의 적용을 보증하지 않는다. 현재 생성기 지원 상태와 최종 HTML 적용 절차는 `skills/universal-flow-document/REFERENCE_UI_REVIEW.md`를 따른다. 결과 버튼은 기존 scenario.kind에서 도출하므로 UI 규칙만을 위해 JSON 필드를 추가하지 않는다.

`skills/universal-flow-document/references/decision.json`은 형식 예시이며 실제 업무 근거가 아니다. 나머지 JSON 예시는 async/callback/stream 등 해당 의미가 필요할 때만 읽는다.

## 상세 확장

| 위치 | 필드 | 의미 |
|---|---|---|
| Flow | group, category, access | 탐색 그룹·분류·접근 조건 |
| Flow / Node | status: {kind, detail} | kind는 implemented/designed/conditional/unknown. 근거와 한계를 detail로 설명 |
| Flow | coverage: {scope, basis, excluded?} | 포함 범위·대조 기준·제외 문자열 배열 |
| Node | owner, condition, stateChange: {before, after} | 처리 주체·판단 조건·중요 상태 변화 |
| Node | flowRef | 같은 문서의 상세 Flow ID. 부모 개요를 생략하는 자동 호출은 아님 |
| Source | file/document, symbol/method, line, revision, url | url은 자격정보 없는 http/https만 허용. 실제 접근 권한은 별도 |
| Flow | api: {method, path, request, response, signature?, schemas?} | 선택 API 계약. schemas는 name/body와 선택 source 배열. body는 코드·JSON 원문을 텍스트로 표시 |
| Flow | completion: {acceptance, processing, resultDelivery} | 비동기 접수·처리·결과 전달 설명 |
| Flow | failureCases[] | id/nodeId/scenarioId/condition/effect/nextAction 필수, status/code/retry/source 선택 |

failureCases의 연결 시나리오는 발생 노드를 포함하고 그 노드에서 failure 또는 compensation 선으로 나가야 한다. detailed의 failure 종료 시나리오는 최소 하나의 failureCases와 연결한다. status와 code는 문자열이다. 실제 API가 없으면 HTTP 필드를 만들지 않는다.

노드와 시나리오에 hold 타입을 추가했다. 보류 종료에는 나가는 실행 선을 두지 않고 다음 재개 조건을 설명한다. 재시도 후 성공은 실제 루프 경로를 시나리오에 순서대로 기록한다.

기존 데이터는 읽을 수 있지만 이전에 누락된 설명은 WARN이 될 수 있다. 경고를 없애기 위해 가짜 설명·근거를 만들지 않는다. Source URL은 자동으로 열거나 API 호출하지 않는다. 주소 hash는 flow와 scenario만 보관하며 원본 데이터에 쓰지 않는다.

상세 API 작성은 `skills/universal-flow-document/references/detailed-api.json`을 참고한다. 가상 계약의 입력 스키마·실패 코드·202 접수와 비동기 결과 구분을 보여주는 예제이며 실제 제품 근거로 사용하지 않는다.
