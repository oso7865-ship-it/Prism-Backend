# 작업 리포트: 흐름 스킬 상세도 보강

> Superseded note:  
> 이 보고서의 다음 작업 판단은 reports/_LATEST.md가 가리키는 최신 Report로 대체되었다.  
> 과거 의사결정 근거로는 유효하지만, 현재 Next Work 판단은 최신 Report와 05.WORKING_CONTEXT.md를 우선한다.

> 작성일: 2026-09-22
> 작업 브랜치: main
> 커밋/PR: 미커밋
> 상태 기록 버전: 1
> 상태 확인 시각: 2026-09-22T04:28:38Z
> 구현 상태: 완료
> 구현 근거: 상세 데이터·렌더러·검증·작성 기준 보강 및 하네스 5개 흐름 재작성
> 로컬 검증 상태: 완료
> 로컬 검증 대상: 기준 422d8433e6a8a84cbdb9fddfb8dad05623e52c7c 이후 상세도 보강 working-tree
> 로컬 검증 근거: docs/hardening/11-flow-detail-validation.json 및 docs/flows/harness-workflow-validation.json의 명령·대상·실측
> 병합 상태: 미수행
> 병합 대상: origin/main
> 병합 근거: 커밋·push·PR·merge 요청 및 실행 없음
> 배포 상태: 미수행
> 배포 근거: 로컬 파일 생성·검수 범위
> 실제 연동 상태: 해당 없음
> 실제 연동 근거: 오프라인 문서 뷰어; API 예제는 명시적인 가상 계약
> 작업 범위: L
> 적용 스킬: universal-flow-document, browser-qa, verification-loop, terminal-ops, code-review
> 적용 Gate: Skill Gate, Document Gate
> 위험도: 구조
> 위험 작업 여부: 예

## 0. 작업 범위 확인

사용자의 보강 요청을 근거로 기존 스킬·실행기·하네스 차트와 관련 검사·기록을 수정했다. 계획과 제외 범위는 저장소 루트 docs/hardening/11-flow-detail-plan.md다. 사용자 제공 ZIP·수집본·제품 코드·외부 서비스·Git 쓰기는 제외했다. 일반 skill-creator 지침을 적용하되 저장소의 Skill/Document Gate를 유지했다.

## 1. 작업 요약

- 단계의 주체·번호·판단 조건·상태 변화, 구현/설계/조건부/미확인 상태, 실패 발생 단계·결과·후속 행동·재시도·코드를 연결했다.
- 선택 API 확장에 메서드·경로·접근 조건·요청 시그니처·스키마를 추가했다. 접수·후속 처리·결과 전달은 completion으로 구분한다.
- hold 종료/시나리오를 추가해 보류와 실패를 분리했다. 상세 흐름 연결, 분류·그룹·경로 검색, 확대·맞춤, 주소 상태 복원, 안전한 근거 링크와 인쇄 CSS를 제공한다.
- detailed 모드에서는 핵심 설명 누락이 FAIL이다. 기존/overview 자료도 설명·시나리오가 빠지면 WARN이며 조용히 PASS하지 않는다.
- 하네스 문서는 5개 Flow, 45개 Node, 18개 Scenario다. 기존 전체 흐름 ID는 유지하고 상세 4개를 추가했다. API 상세 예제는 실제 제품과 분리한 가상 계약이다.

## 2. 변경 파일

| 대상 | 변경 |
|---|---|
| skills/universal-flow-document의 SKILL·REFERENCE_AUTHORING·REFERENCE_FORMAT | 상세도·추출 범위·상태 변화·실패 계약·검수 지침 |
| 같은 스킬의 schema·scripts·styles | 필드와 화면 연결, 내용 누락 검사, 탐색과 접근성 보강 |
| 같은 스킬의 references/detailed-api.json | 상세 API·202 접수/후속 결과·오류 코드의 가상 예제 |
| scripts/tests/flow-document.test.mjs | 기존 20개 + 보강 8개 회귀 |
| scripts/validate-docs.mjs | YAML 메타데이터 뒤 Markdown 제목 인식; 제목 누락 거부 유지 |
| 저장소 루트 docs/flows·README | 실제 하네스 상세 문서·진입 안내·검수 근거 |
| reports·_WORKING_CONTEXT_HISTORY 및 docs/hardening | 최신성·작업 계약·검증 증거 |

## 3. 검증 결과

- 기존 78개와 흐름 관련 28개, 합계 106개 회귀를 로컬 Windows/Node 24에서 실행해 모두 통과했다(실패·skip 0). 최종 실행 결과·종료 상태는 11-flow-detail-validation.json이 소유한다.
- 스키마/ID/연결/시나리오·상세 누락/실패 연결/unsafe URL/HTML escaping/출력 보호·frontmatter 제목 회귀를 검수했다.
- 원본 ZIP은 정적 데이터·HTML·렌더러 분석으로 비교했다. 원본 file URL 열기는 브라우저 정책상 차단되었으며 우회하지 않았다. 실제 브라우저 검수는 이번에 생성한 자체 문서를 loopback 미리보기에서 수행했다.
- skill-creator의 Python quick_validate는 환경에 PyYAML이 없어 실행할 수 없었다. 별도 패키지를 설치하지 않고 현재 2개 단순 scalar 메타데이터(name/description)를 수동 대조하고 저장소 Skill/Document 검사로 검증했다. 그 Python 검사가 통과했다고 주장하지 않는다.

### 3-1. Browser QA

사용 도구: mcp__cua_repl.js의 Playwright DOM 관측·화면 캡처. 테스트 준비: 새로 생성한 하네스 HTML과 가상 API 예제; 실제 API 호출 없음.

- 하네스 모든 18개 시나리오의 활성 edge ID·노드 수·terminal 타입을 원본 JSON 경로와 대조했다. 마지막 추가 실행 실패 시나리오는 commands에서 fail로 바로 이동해 후속 검수를 통과로 표시하지 않는다.
- 기존 전체 시나리오의 pre-hold/warn-hold는 화면과 종료 타입 모두 보류다. 정상 완료/수정 후 완료/미해결과 구분한다.
- 시나리오 선택 후 새로고침은 hash의 flow/scenario를 복원했다. 확대 120%, 맞춤은 차트 scrollWidth/clientWidth가 동일해졌다.
- 노드 Enter와 Space, 설명 제목 클릭으로 같은 ID의 차트·카드 선택 및 실제 포커스를 확인했다. 상세 흐름 버튼은 대상 Flow로 전환했다.
- API 예제에서 /example/jobs 검색, 요청 스키마 펼침, HTTP 400/NAME_REQUIRED와 다음 행동, 접수/후속 처리 각각의 경로, 근거 링크 href/rel을 확인했다. 예제 외부 링크는 방문하지 않았다.
- 320/390/760/1280px 경계에서 페이지 가로 넘침을 확인했다. 측정 대상별 값은 docs/flows/harness-workflow-validation.json에 기록한다. 차트 내부 스크롤은 의도한 동작이다.

## 4. Checklist 결과

Skill Gate·Document Gate: 작성 목적·발동 범위·연결·상세 데이터·화면 대응을 대조했다. 실제 제품 API/DB/결제 계약 변경과 배포는 없으므로 해당 Gate/릴리즈 Checklist는 N/A다. 뷰어 검색·선택·주소·키보드·반응형은 Browser QA에서 직접 관측했다.

## 5. 발견된 문제와 수정·재검수

| 문제 | 수정·재확인 |
|---|---|
| 상세 설명·시나리오를 제거해도 기존 검사 PASS | overview WARN, detailed FAIL; 누락·조건·source·결과 회귀 |
| owner를 저장해도 화면 미표시 | 차트/설명에 번호·주체 출력, 실제 DOM 확인 |
| 보류가 failure로 표시됨 | hold 타입·종료/시나리오 일치 검사 및 실제 표시 확인 |
| 검증 실패 후 후속 검수로 넘어가는 듯한 상세 경로 | 필수 실행 실패 즉시 수정으로 가는 별도 경로 및 시나리오 추가 |
| frontmatter 있는 SKILL을 제목 누락으로 오인 | 기존 제목과 frontmatter 제목 모두 허용, 제목 없음/닫히지 않은 frontmatter 거부 회귀 |
| 확대 버튼의 가로 터치 영역 부족 | 최소 너비 44px 추가 후 측정 |
| 모바일 맞춤 후 축소가 오히려 확대될 수 있는 배율 하한 | 축소가 현재 배율보다 커지지 않도록 수정, 실제 맞춤 20% → 축소 10% 확인 |

## 6. 미해결 항목

- 원격 CI·실제 프린터/PDF 인쇄·외부 근거 URL 접근은 미실행이다. 인쇄 CSS의 실제 인쇄 품질은 미검증이다.
- 자동 검사는 상세 텍스트의 존재·연결을 보증하며 내용의 사실성이나 모든 Entry/분기 추출의 완전성은 원본 대조가 필요하다.
- 파일 형식의 범용성을 유지하며 모든 API/업무 문서에 같은 필드를 억지로 요구하지 않는다. overview의 의도적 생략은 경고와 범위를 남긴다.

## 7. Working Context 반영 여부

하네스 유지보수 이력과 최신 Report를 갱신한다. 부착용 빈 Working Context와 활성 스킬 20개는 유지한다. 이전 통합/초기 차트 검수는 과거 증거로 archive에 보존한다.

## 8. 다음 작업

요청한 로컬 보강·재작성·검수 범위는 PASS다. 새 제품 흐름을 만들 때 detailed 예제와 추출 범위 대조를 활용한다. 보조 Python validator의 환경 제약과 인쇄·원격 실행 미검증은 §3·§6에 명시했다.

## 9. 후속 보완: 결과 버튼·탐색·표현 지침

> 작업 시각: 2026-09-22T05:06:59Z
> 작업 규모: M
> 적용 스킬: universal-flow-document, terminal-ops
> 적용 Gate: Skill Gate, Document Gate
> 근거: 사용자가 첨부 화면을 기준으로 전체·완료·실패 버튼과 조건부 세부 선택, 왼쪽 검색·CSS 지침, 200줄 이내 문서 분리를 명시했다. 스킬 문서의 추가·연결은 이 요청의 승인 범위다.

### 9-1. 작업 계약과 변경

목표는 재사용할 스킬의 UI 생성 기준 수정이다. SKILL·AUTHORING·FORMAT과 새 INTERACTION·VISUAL·UI_REVIEW 문서, 필요한 작업 기록을 변경했다. 기존 HTML·JSON·뷰어·생성기·CSS 자산·schema·Git 쓰기는 제외했다. skill-creator를 적용해 필수 진입 지침과 조건부 상세 읽기를 분리했다.

- 전체·완료·실패를 기본 버튼으로 유지하고 시나리오 0/1/여러 개의 비활성/즉시 선택/하위 선택을 정했다. 보류·진행 중은 실제 데이터가 있을 때만 추가한다.
- 결과별 선택 기억·다른 Flow 이동·주소 복원·키보드·복구 후 완료·실패 사례 연결을 구분했다.
- 왼쪽 검색 노출, 검색/분류 교집합, 결과 수와 0건, 선택 후 검색 유지, 모바일 검색·목록 진입과 포커스를 정했다.
- 첨부 원본의 정적 CSS에서 확인한 따뜻한 배경·녹색/붉은색·카드/패널 위계를 토큰과 역할별 스타일 기준으로 구체화했다. 원본 제품 데이터·고정 헤더 높이·작은 터치 영역은 복제하지 않았다.
- 각 지침은 200줄 이내다. SKILL 87줄, 새 보조 문서는 INTERACTION 63줄·VISUAL 62줄·UI_REVIEW 53줄이다.

### 9-2. 검수 결과와 범위

저장소 루트에서 다음 명령을 실행했고 모두 종료 코드 0이었다.

- node GENERAL_HARNESS/scripts/validate-docs.mjs — Markdown 100개 구조 PASS.
- node GENERAL_HARNESS/scripts/validate-skills.mjs — 활성 스킬 20개 PASS.
- node GENERAL_HARNESS/scripts/validate-references.mjs — 검사 범위 100개 문서 참조 PASS, 기존 제외 범위 유지.
- node GENERAL_HARNESS/scripts/validate-no-personal-paths.mjs — 지원 패턴 내 개인 경로 없음.
- node GENERAL_HARNESS/scripts/validate-report-consistency.mjs — 최신 포인터·활성 수·이력 일관성 PASS.
- node GENERAL_HARNESS/scripts/validate-work-records.mjs --project-root . --plans docs/hardening --reports GENERAL_HARNESS/reports --strict --json — 기록 10개 PASS, findings 0.

HTML·JSON·생성기·뷰어·CSS 5개 파일의 작업 전후 SHA-256이 모두 동일함을 확인했다. 문서의 참조 검사도 기록 반영 후 다시 통과했다.

수동 대조에서는 사용자 요구·입력 모델(kind/path/edgePath)·문서 간 연결·0/1/여러 경로·검색 상태 전이를 확인했다. 필수 누락이나 상충 지침은 발견하지 않았다. 기존 두 scalar frontmatter는 유지했다. Python quick_validate의 PyYAML 부재는 §3의 환경 제한과 동일하며 해당 검사의 통과를 주장하지 않는다.

이번 판정은 **스킬 문서 보완 PASS**다. 이전 §3의 106개 회귀와 브라우저 관측은 이전 생성기에 대한 과거 증거이며 이번 새 UI 기준의 구현 검증이 아니다. 이번에는 실행 코드가 바뀌지 않아 회귀와 브라우저 검수를 다시 수행하지 않았다.

### 9-3. 생성기 지원 상태와 다음 적용

현재 내장 build는 여전히 단일 시나리오 select를 출력한다. 새 문서에서 이를 명시하고 이후 HTML 생성·갱신 시 재현 가능한 생성 경로를 새 기준에 맞춘 뒤 검수하도록 연결했다. 현재 HTML이 새 버튼·CSS 기준을 충족한다고 보고하지 않는다. 최신 포인터와 유지보수 이력에는 문서 보완 상태를 기록하고 부착용 Working Context는 유지한다.
