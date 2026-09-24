# Project Adapter Contract

## 1. 책임과 진입

공통 하네스는 작업 절차·위험 판단·검증·기록 형식을 소유한다. 프로젝트 루트의 PROJECT_HARNESS는 제품 요구사항·화면·API·데이터 계약의 기준 문서와 담당자를 연결한다. 제품 규칙을 GENERAL_HARNESS에 복사하지 않는다. 어댑터는 상위 규칙의 우선순위를 바꾸지 않으며, 충돌은 00.HARNESS_RULES.md §3에 따라 해결한다.

어댑터가 있으면 00.PROJECT_CONTEXT.md를 먼저 읽고 현재 작업에 해당하는 manifest.json의 route를 선택한다. 선택된 문서만 선언 순서대로 읽는다. 자동 검사는 전체 경로의 존재만 확인하며 모든 제품 문서를 컨텍스트에 넣으라는 뜻이 아니다. 경로 누락·기준 충돌·정의되지 않은 작업이면 추측하지 말고 해당 작업을 중단하여 범위 또는 기준을 확정한다.

어댑터가 없으면 기존 공통 하네스 절차를 그대로 사용한다. 기존 context만 있는 프로젝트는 수동 검토 대상으로 남기며 자동 변환하지 않는다.

## 2. 선언 형식과 소유자

프로젝트 루트 기준 PROJECT_HARNESS/manifest.json에 다음 정보를 기록한다.

| 필드 | 계약 |
|---|---|
| schemaVersion | 정수 1. 지원하지 않는 계약은 FAIL |
| adapterVersion | 프로젝트가 관리하는 세 자리 버전 문자열. 경로·소유자·읽기 순서 변경 때 갱신 |
| harnessSource | repository: HTTPS 저장소 URL, commit: 반입 기준의 전체 커밋 ID |
| documents | 고유 id, 프로젝트 상대 Markdown path, 책임자 또는 담당 팀 owner |
| routes | 고유 task와 읽기 순서대로 나열한 documents ID 목록 |
| localChanges | 공통 하네스에서 로컬 변경한 파일 path와 reason. 변경이 없으면 빈 배열 |

경로는 슬래시(/)를 사용한다. 절대 경로·상위 이동·심볼릭 링크를 허용하지 않는다. 제품 문서는 GENERAL_HARNESS 밖에 둔다. context에는 모든 등록 문서의 경로와 기준 충돌 시 처리 방식을 기록한다. owner는 문서 내용의 관리 책임자이며 실행 권한 부여가 아니다. Git 기준 브랜치는 별도 harness.config.json이 소유한다.

## 3. 반입과 갱신

1. 원본 저장소와 반입 커밋을 확인하고 기록한다. 미커밋 수정은 원본 커밋에 포함된 것으로 표현하지 않는다.
2. templates/project-adapter의 예시를 프로젝트 루트의 PROJECT_HARNESS로 복사하고 manifest.example.json을 manifest.json으로 이름을 바꾼다. 모든 자리표시자를 실제 값으로 교체한다.
3. 제품 기준 문서와 담당자, 작업별 읽기 순서를 합의한다. 업무별 경로는 프로젝트에서 정한다.
4. 공통 하네스 수정 파일·이유를 localChanges에 적고 버전과 변경 보고서를 갱신한다. 상위 버전 반입 시 이 목록과 Git diff를 비교해 충돌을 검토한다.
5. 명시적 프로젝트 루트로 검사한다. 기존 어댑터는 검토 후에만 manifest를 도입한다.

```sh
node GENERAL_HARNESS/scripts/validate-project-adapter.mjs --project-root . --require-adapter --strict --json
node GENERAL_HARNESS/scripts/validate-project-adapter.mjs --project-root . --task ui --json
```

## 4. 판정과 한계

PASS는 선언 구조·경로·연결의 통과다. 어댑터 없음은 NOT_APPLICABLE(exit 0)이며 PASS로 합산하지 않는다. --require-adapter 또는 --task로 요구했는데 없으면 FAIL(exit 1). context만 있는 기존 어댑터는 WARN(exit 0, --strict는 1); 작업 route를 요구하면 FAIL이다. 잘못된 JSON·버전·누락 문서·알 수 없는 route는 FAIL이다. 실패 시 selectedDocuments는 빈 배열이다.

검사기는 파일을 수정하거나 프로젝트 스크립트를 실행하지 않는다. 원본 커밋의 실재·진위, 누락된 로컬 변경, 문서 내용의 정확성·충돌, 소유자의 적합성은 자동 인증하지 않는다. Git diff와 문서 검토를 함께 수행하고 그 근거를 보고서에 남긴다. CI에서는 선택적 어댑터를 --strict로 검사하며 실행 범위는 `08.QUALITY_GATE.md §9-2`를 따른다.
