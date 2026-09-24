# 작업 리포트: ECC·Brooks·흐름 문서 선별 통합

> Superseded: 2026-09-22_flow-detail-reinforcement_report.md. 이 보고서는 통합과 초기 차트 시점의 역사 증거이며 최신 상세도 보강은 새 Report를 따른다.

> 작성일: 2026-09-22
> 패키징/배포일: 해당 없음
> 작업 브랜치: main
> 커밋/PR: 미커밋
> 상태 기록 버전: 1
> 상태 확인 시각: 2026-09-22T03:33:10Z
> 구현 상태: 완료
> 구현 근거: 신규 스킬 4개, 기존 스킬·등록·출처·ADR-050, 순수 Node 흐름 실행기와 회귀의 working-tree 변경
> 로컬 검증 상태: 완료
> 로컬 검증 대상: 기준 422d8433e6a8a84cbdb9fddfb8dad05623e52c7c 이후 이번 통합 working-tree
> 로컬 검증 근거: 기존 78개와 신규 20개 회귀, 구조·기록·연결 검사와 실제 브라우저 관측 통과. 최종 명령·범위·해시는 docs/hardening/10-final-validation.json
> 병합 상태: 미수행
> 병합 대상: origin/main
> 병합 근거: 이번 작업에서 commit/push/PR/merge 요청 및 실행 없음
> 배포 상태: 미수행
> 배포 근거: 로컬 구현·검증 범위이며 외부 배포 없음
> 실제 연동 상태: 해당 없음
> 실제 연동 근거: 독립 문서 생성 도구이며 제품 API·외부 서비스 연동이 작업 범위에 없음
> 작업 범위: XL
> 적용 스킬: planning, skill-scout, skill-stocktake, terminal-ops, test-design, code-review, universal-flow-document, browser-qa, verification-loop, report-consistency, quality-gate
> 적용 Gate: Skill Gate, Document Gate
> 위험도: 구조
> 위험 작업 여부: 예

## 0. 작업 범위 확인

| 항목 | 내용 |
|---|---|
| 요청 요약 | 제안한 1~5단계 순차 실행, 필요한 문서·연결 보강, 완료 후 검수와 문제 수정·재검수 |
| 수정 대상 | 신규 4개 스킬, 기존 8개 기능 보강 파일, 등록·출처·기록 문서, 흐름 생성기·회귀·CI |
| 제외 대상 | 원본 자료 변경, 외부 설치, 전역 TDD/자동 커밋/자동 sweep/유료 평가, Git 쓰기·배포 |
| 근거 | 사용자 명시 승인과 ADR-050. 기준선 및 계획은 저장소 루트 docs/hardening의 10번 자료 |
| 적용 스킬/Gate | 헤더 참조. 스킬 생성은 저장소의 01 규격을 사용; 별도 전역 설치 없음 |
| 위험도 | 구조. 이번 범위의 승인 확보, 삭제·자동 Git 변경 없음 |
| 검증 방법 | 기존 CI 명령 전후 비교, 신규 생성기 정상/실패 회귀, 실제 브라우저 관측, 의미·연결 검수 |
| 한계 | Windows/Node 24에서 실행. 원격 Ubuntu/Node 20 CI는 미실행. 통제된 별도 모델 행동 전후 평가는 미실행 |

## 1. 작업 요약

1. 기준선: 기존 구조·기록 검사 통과, 회귀 78/78. 선택적 프로젝트 어댑터 없음은 NOT_APPLICABLE.
2. ECC: documentation-lookup/test-design 추가, search-first는 기존 최소 해법, 행동 평가는 skill-stocktake 참조로 통합. planning·verification-loop·recovery·browser-qa·UI-F 연결 보강.
3. Brooks: code-review와 기존 테스트 검수 참조 추가. 리뷰 산출물 품질과 코드 결함 상태를 구분. 점수/임계값 강제·자동 sweep은 제외.
4. 흐름: 동일 JSON의 SVG 차트·설명 HTML을 순수 Node로 생성. 스키마·그래프·시나리오 검사, ongoing 스트림 경계, 기존 출력 보존, DOM 텍스트 렌더링.
5. 관리: 활성 20개 등록, 1층 읽기 표면 유지, 원 고지·출처·선별 예외 ADR·보고서 동기화. 기존 CI 두 환경의 회귀 명령에 신규 테스트 연결.

## 2. 변경 파일

| 파일/묶음 | 변경 내용 | 이유 |
|---|---|---|
| `skills/documentation-lookup/SKILL.md`, `skills/test-design/SKILL.md` | 조건부 버전 근거 조사·테스트 설계 | 조사·설계·실행 역할 분리 |
| `skills/code-review/SKILL.md`, `skills/code-review/REFERENCE_TEST_REVIEW.md` | 코드·테스트 근거 기반 검수 | 기존 실행/보안 검수의 공백 보강 |
| `skills/universal-flow-document/SKILL.md` 및 같은 폴더의 참조·schema·JSON·Node·CSS | 자체 포함 HTML, 구조 검증, 8개 예시 | 설치 없이 흐름 문서 생성 |
| `skills/skill-stocktake/REFERENCE_BEHAVIOR_EVAL.md` | 사례 v1, 관측 증거·비교 한계 | 형식 검사와 실제 준수 구분 |
| 기존 intent-to-implementation/최소 해법, planning, verification-loop, stocktake, agent-recovery, browser-qa 및 UI checklist | 탐색·영향 범위·증거 인계 | 중복 스킬·규칙 방지 |
| `01.SKILL_TEMPLATE.md`, `02.SKILL_INDEX.md`, `03.CONTEXT_BUDGET.md`, `05.WORKING_CONTEXT.md`, `08.QUALITY_GATE.md`, `09.AGENT_WORKFLOW.md` | 생성 자산 규격·20개 등록·조건부 연결 | 기존 상시 표면과 판정 소유권 유지 |
| `_SOURCE_MAPPING.md`, `_PENDING_IMPORT_LIST.md`, `10.ADR.md`, 파생 폴더 LICENSE 5개 | 출처·보류·승인 범위·원 고지 | 원본과 활성 배포 구분 |
| `scripts/tests/flow-document.test.mjs`, 저장소 루트 .github/workflows/harness-ci.yml | 신규 20개 회귀 연결 | 잘못된 데이터·쓰기·HTML 회귀 검출 |
| README, docs/hardening의 10번 증거, reports 최신성·이력 | 사용·검증·현재 포인터 정리 | 다음 작업의 정확한 기준 |

## 3. 검증 결과

| 검사 | 결과 | 실제 범위 |
|---|---|---|
| 기존 기준선 회귀 | PASS | 78개, 실패/skip 0 |
| 통합 회귀 | PASS | 기존 78 + 신규 20 = 98개, 실패/skip 0 |
| 형식·스킬·경로·정합성·개인경로·구조·시크릿·작업 기록 | PASS | 기존 검증 명령. 시크릿 기본 검사는 Git 추적 파일만 대상 |
| 선택적 프로젝트 어댑터 | N/A | 부재에 따른 NOT_APPLICABLE, PASS 개수에 포함하지 않음 |
| 원본 보존 | PASS | 제공 메타데이터 SHA-256과 로컬 원본 80개 일치. 원격 재인증 아님 |
| 원 고지 보존 | PASS | ECC 4개 목적지 및 Brooks 1개 LICENSE 바이트 동일 |
| 예시 8개 | 구조 오류 없음, WARN | 실제 제품 source가 없는 예시이므로 경고 유지; 실제 업무 검증으로 간주하지 않음 |
| 브라우저 동작·레이아웃 | PASS | CUA in-app browser, 1280×900 및 390×844. 아래 관측 표 |
| Skill Gate 수동 검수 | PASS | 독립 역할·Trigger/비발동·특화 판정·실제 Handoff, 원본 일괄 활성화 없음 |
| Document Gate 수동 검수 | PASS | 범위·근거·판정 의미·미확인 구분, 역할 중복 없음 |

검증 명령과 결과는 저장소 루트 docs/hardening/10-final-validation.json에 기록한다. node --check와 신규 미추적 파일을 포함한 기존 시크릿 패턴 검사도 최종 실행한다.

### 3-1. Browser QA

사용 도구: mcp__cua_repl.js의 tab.playwright 및 screenshot. 로컬 예시 8개를 합쳐 생성한 자체 포함 HTML을 127.0.0.1의 이번 작업용 서버에서 확인했다. 제품 API 호출·저장 기능이 없는 문서 뷰어이므로 실제 연동 검증은 해당 없음이다.

| 행동/관측 수단 | 결과 |
|---|---|
| 1280×900 documentElement.scrollWidth/clientWidth | 1265/1265, 페이지 가로 넘침 0 |
| 390×844 documentElement.scrollWidth/clientWidth | 375/375, 페이지 가로 넘침 0 |
| 모바일 차트 scrollWidth/clientWidth | 920/317, 차트 내부 스크롤로 제한 |
| 주문 실패 시나리오 선택 후 .edge:not(.dim) | e1/e2/e3/e5; 활성 노드 start/validate/stock/enough/failure |
| 주문 성공 시나리오 선택 후 .edge:not(.dim) | e1/e2/e3/e4/e6; 차트 노드와 설명 각 7개 |
| 노드 Enter 및 Space, 설명 버튼 click | 차트·설명 동일 failure/success ID 선택, aria-pressed 두 조작 요소에 반영 |
| 모바일 목록·검색·흐름 변경 | 스트림 검색 1개, 없는 검색 0개와 검색 결과 없음 안내, 선택 후 메뉴 aria-expanded=false |
| ongoing 시나리오 | 진행 중 · 연결 표시, 활성 선 e1/e2; 성공 종료로 오인하지 않음 |
| 비선택 설명 CSS | opacity 1, 전경 rgb(23,45,50), 배경 rgb(244,247,245); 점선·설명으로 구분 |
| 모바일 시작점 자동 정렬 | chart x=29~346 안에 시작 노드 x=85~275, scrollTop=0, scrollLeft=294 |
| 브라우저 error 로그 | 관측 시 0개 |

### 3-2. 행동 평가와 한계

통제된 동일 모델·fixture의 변경 전후 실험은 **미실행**이다. 이 보고서의 수동 검수와 실제 작업에서 관측한 사례를 행동 준수율로 환산하지 않는다.

| 사례 | 이번에 확보한 증거 | 판단 범위 |
|---|---|---|
| BE-01 | 이전 검토 턴에서 파일 수정 없이 통합 방향만 제안 | 실제 한 사례 관측; 통제 전후 비교 아님 |
| BE-02 | 구현 전 10-skill-integration-plan 생성, 이후 스킬·코드 추가 | 이번 작업의 계획 선행 관측 |
| BE-05 | 기존 최소 해법·검증 스킬 확장, 8개 JSON 예시·기존 CI 재사용 | 이번 작업의 재사용 관측 |
| BE-03/04/06/07/08 | 별도 격리 에이전트 실행 없음 | 미실행; 스킬 내용 수동 검수만 수행 |

## 4. Checklist 결과

| Checklist | 결과 | 이유 |
|---|---|---|
| UI 기능 checklist §1-3 | 적용 범위 검토 | 저장·권한·API가 없는 문서 뷰어. 탐색·선택·반응형은 Browser QA로 직접 확인 |
| API/DB/결제/AI Runtime/release | N/A | 제품 계약 변경·실제 연동·배포 없음 |

## 5. 발견된 문제와 수정·재검수

| 심각도 | 발견 | 수정과 같은 검사 재실행 |
|---|---|---|
| Major | 지속 스트림 예시를 종료 필수 검사로 잘못 거부 | stream의 명시적 openEnded와 ongoing 시나리오 추가, 설명 경계 요구. 최초 18/19에서 보강 후 20/20 |
| Minor | i2i 출처 문장을 Handoff에 넣어 보조 참조를 스킬 인계 대상으로 오인 | 출처 문장을 본문 앞쪽으로 이동, validate-skills 20개 재통과 |
| Minor | 새 Report 초안과 기존 최신 포인터의 일시적 불일치 | 게시 단계에서 최신 포인터·이전 보고서 archive·digest를 함께 갱신하고 strict 기록 검사 재실행 |
| Minor | 모바일 초기 화면에 시작 노드가 보이지 않을 수 있음 | 렌더 후 시작점으로 차트 내부 가로 스크롤 정렬, 세로 위치 초기화; 모바일 재검수 |
| Minor | 비선택 설명 opacity로 가독성 저하 | 전체 텍스트 투명도 제거, 점선/안내로 구분, 브라우저 opacity=1 및 시각 재검수 |
| Major | 출력이 입력의 하드링크인 경우 경로 비교만으로 보호 부족 | dev/ino 동일 파일 검사, 하드링크 보존 회귀 통과 |
| Minor | 보호된 출력 경로 검사 전에 디렉터리를 생성할 수 있음 | 기존 조상 경로를 먼저 해석해 보호 검사 후 mkdir 수행, 금지 경로에 디렉터리가 생기지 않는 회귀 통과 |
| Minor | 빈 source 객체만 있어도 근거 경고가 없어질 수 있음 | 실제 비어 있지 않은 file/document 기준으로 경고 판정, 회귀 통과 |

## 6. 미해결 항목

- superseded — §9 참조: 사용자 제공 흐름 자료의 별도 고지 문구는 후속 사용자 지시에 따라 정리했다.
- 통제된 에이전트 행동 전후 평가와 원격 CI는 미실행이다. 실제 준수 개선·Ubuntu 실행 성공을 주장하지 않는다.
- 예시 JSON의 source 경고는 예시임을 드러내는 정상 한계다. 실제 업무 문서에는 확인한 source를 넣어야 한다.

## 7. Working Context 반영 여부

- 활성 스킬 수만 20개로 동기화. 프로젝트 부착용 빈 상태 표는 보존한다.
- 이번 유지보수 이력은 `_WORKING_CONTEXT_HISTORY.md`에 요약하고, 검증 후 `reports/_LATEST.md`를 전환한다.
- 과거 유지보수 Report는 게시 절차에 따라 superseded 표시·archive·digest를 함께 갱신한다.

## 8. 다음 작업

- 이 통합의 로컬 구현·검증 범위가 완료되면 실사용 사례로 행동 평가를 축적한다. 이번 작업에서 추가 자동화·원격 게시를 실행하지 않는다.

## 9. 후속 실사용: 하네스 흐름 문서

작업일: 2026-09-22. 관측 시각·명령 결과·대상 소스 해시는 저장소 루트 docs/flows/harness-workflow-validation.json에 기록한다. §3의 98개 회귀는 앞선 실행기 통합 시점의 증거이며 이번 문서 보완에서 재실행했다고 주장하지 않는다. 앞선 파일 해시 역시 당시 스냅샷이다.

| 계약 항목 | 내용 |
|---|---|
| 목표 | 새 흐름 스킬로 현재 하네스 운영 흐름 1개를 생성하고 실제 브라우저 검수 |
| 수정 대상 | docs/flows의 JSON·HTML·안내·검증 기록, README 진입 링크, 흐름 스킬의 출처 문구와 현재 보류 목록, 이 후속 기록 |
| 제외 대상 | 실행기·뷰어 코드, 원본 자료, 기존 LICENSE 파일, Git 쓰기·외부 게시 |
| 근거 | 사용자의 차트 생성 요청과 ECC 외 별도 고지 불필요 지시; 현재 하네스 운영 규칙 |
| 적용 스킬 | universal-flow-document, browser-qa, terminal-ops |
| 적용 Gate | Document Gate |
| 위험도 | 일반. 요청된 새 산출물 생성과 작은 문구 보완; 기존 사용자 파일 덮어쓰기 없음 |
| 검증 방법 | Flow 구조 검사, 근거 경로 존재·내용 대조, JSON/HTML 일치, 문서·스킬·참조·정합성·개인경로·strict 기록 검사, PC/모바일 상호작용 |

### 9-1. 결과와 검수

- Flow 추가 1개, 변경·삭제 0개. 15개 노드, 15개 선, 정상 완료/수정 후 완료/착수 보류/구조·위험 WARN 보류/미해결의 5개 시나리오.
- 모든 단계에 현재 근거 문서와 기준 revision을 연결했다. 로컬 작업 트리의 규칙 설명이며 실행 로그가 아니다.
- 초안 검수에서 잘못 적힌 최소 해법·복구 스킬 경로를 실제 REFERENCE_MINIMAL_SOLUTION_COMPASS 및 agent-recovery 경로로 수정하고 재검수했다. 복구 스킬은 반복 실패 등에만 발동한다는 조건도 명시했다.
- PC 1280×900: 페이지 scrollWidth/clientWidth 1265/1265, 차트 1180/868. 모바일 390×844: 페이지 375/375, 차트 1180/302. 페이지 가로 넘침 없음, 차트 내부 스크롤 사용.
- mcp__cua_repl.js에서 selectOption 후 .edge:not(.dim)의 ID를 경로와 대조: 정상 9개, 수정 후 완료 12개, 착수 보류 5개, WARN 보류 8개, 미해결 9개. 같은 선을 재방문하는 경우 표시 선 수는 중복 제외다.
- Enter(result), Space(repair), 설명 제목 클릭(result) 모두 차트·카드의 같은 ID 2곳에 aria-pressed=true를 확인했다. 모바일 검색은 0개/1개와 안내 문구, 흐름 선택 후 목록 닫힘 aria-expanded=false를 확인했다.
- Document Gate 의미 검수: 조건부 스킬·기록, WARN 유형 구분, FAIL 수정·동일 검증 재실행, 재개 조건, 실제 상태 분리가 현재 근거와 일치한다. 검증 기록의 명령이 모두 통과하면 이번 범위 PASS다.

### 9-2. 고지와 기록 범위

사용자 지시에 따라 사용자 제공 흐름 자료의 별도 라이선스 확인 경고·보류 문구를 정리했다. ECC 고지를 유지하고 Brooks 원문에 딸린 기존 MIT LICENSE 파일도 보존했다. 이번 차트에 별도 고지 문구를 추가하지 않았다.

기존 최신 Report에 실사용 후속 보완을 누적했다(06.REPORT_TEMPLATE.md §5-3). 프로젝트 부착용 빈 Working Context는 갱신 대상이 아니며 활성 스킬 수 변화도 없다. Git 병합·배포·실제 연동 상태는 기존 기록과 같다.
