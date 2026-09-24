# Source Mapping

> 목적: 현재 하네스에 어떤 ECC 선택 참고자료와 감사 피드백이 반영되었는지 추적한다.

---

## 0. 외부 근거 출처 및 보존 상태

이 문서에서 인용하는 외부 자료의 안정 식별자와 보존 여부를 한곳에 모은다(외부 검수 M-14). 개별 반영 표에는 이 정보를 반복하지 않는다.

| 외부 자료 | 취득 경로 | 취득 시점(대화 기준) | 패키지 내 보존 여부 | 재검증 가능 여부 |
|---|---|---|---|---|
| `GENERAL_HARNESS_논리구조_검수_리포트_2026-07-10.md`(첫 번째) | 사용자가 대화에 직접 첨부 | 2026-07-10 | 미보존(패키지 밖 원문) | 재검증 불가 — 사용자가 재첨부해야 원문 재확인 가능 |
| `GENERAL_HARNESS_문서세트_논리구조_검수_리포트_2026-07-10.md`(두 번째, ZIP SHA-256 해시 대조 포함) | 사용자가 대화에 직접 첨부 | 2026-07-10 | 미보존 | 재검증 불가 — 원문에 기록된 원본 ZIP 해시(`EAF71FD9...`)로 당시 대상 ZIP만 식별 가능 |
| `GENERAL_HARNESS_문서세트_논리구조_검수_리포트_2026-07-11.md`(세 번째, ZIP SHA-256 대조 포함) | 사용자가 대화에 직접 첨부 | 2026-07-11 | 미보존 | 재검증 불가 — 원문 기록 해시로 당시 대상 ZIP만 식별 가능(외부 검수 M-10, G-09) |
| `GENERAL_HARNESS_문서세트_논리구조_재검수_리포트_2026-07-11.md`(네 번째, 재검수, .NET 독립 ZIP 검증 포함) | 사용자가 대화에 직접 첨부 | 2026-07-11 | 미보존 | 재검증 불가 — 원문 기록 해시로 당시 대상 ZIP만 식별 가능(외부 검수 M-09, 이 행 자체가 누락돼 있던 것을 이번에 보강) |
| `GENERAL_HARNESS_문서세트_논리구조_검수_리포트_2026-07-12.md`(다섯 번째) | 사용자가 대화에 직접 첨부 | 2026-07-12 | 미보존 | 재검증 불가 — 원문 기록 해시로 당시 대상 ZIP만 식별 가능 |
| `GENERAL_HARNESS_문서세트_논리구조_재검수_리포트_2026-07-12_2001.md`(여섯 번째, 재검수) | 사용자가 대화에 직접 첨부 | 2026-07-12 | 미보존 | 재검증 불가 — 원문 기록 해시로 당시 대상 ZIP만 식별 가능 |
| `GENERAL_HARNESS_REPAIR_AND_SKILL_ROADMAP.md` | 사용자가 대화에 직접 첨부 | 2026-07-10 이전 | 미보존 | 재검증 불가 |
| `harness_import_candidates_20260704.zip` | 사용자가 대화에 직접 첨부 | 2026-07-04 | 미보존(원본 zip) | 재검증 불가 |
| `ecc_selected_reference_pack_v0.1` | 사용자가 대화에 직접 첨부 | 2026-07-04 이전 | 미보존 | 재검증 불가 |
| `Understand-Anything-main.zip` | 사용자가 대화에 직접 첨부(GitHub 저장소 원본) | 2026-07-09 | 미보존(24.8MB, 패키지에 넣기엔 과함) | 재검증 불가 — 필요 시 사용자가 원본 저장소 재확인 |
| `codebase-memory-mcp-main.zip` | 사용자가 대화에 직접 첨부(GitHub 저장소 원본) | 2026-07-09 | 미보존(93MB) | 재검증 불가 |
| `intent-to-implementation.zip`(스킬 패키지, 영어 원문 + YAML frontmatter + 벤더 배포 파일) | 사용자가 로컬 작업 폴더에 직접 제공 | 2026-08-02 | 미보존(사용자 결정으로 저장소에서 제외, 로컬에만 존재) | 재검증 불가 — 필요 시 사용자가 재제공. 원저작 여부(직접 작성 vs 외부 파생)도 미확인 |
| `HARNESS_문제점_종합정리_2026-08-02.md`(실사용 Report 10건 분석 + 반입 검수) | 사용자가 로컬 작업 폴더에 직접 제공 | 2026-08-02 | 미보존(사용자 결정으로 저장소에서 제외, 로컬에만 존재) | 재검증 불가 — 필요 시 사용자가 재제공. 근거가 된 챱챱 프로젝트 Report 10건 원본도 이 저장소 밖에 있음 |
| `vue-ui-polish.zip`(스킬 패키지, 한국어 본문 + YAML frontmatter + 벤더 배포 파일 + MIT LICENSE) | 사용자가 로컬 작업 폴더에 직접 제공 | 2026-08-03(최초), 2026-08-04(개정본 2회 — 참조 11종·감사 스크립트 포함 확장) | 미보존(사용자 결정으로 저장소에서 제외, 로컬에만 존재). 단 `LICENSE`는 MIT 고지 보존 의무에 따라 `skills/vue-ui-polish/LICENSE`로 반입(개정본 기준 저작권자 3인) | 재검증 불가 — 원저작은 Emil Kowalski `Skills for Design Engineers` + Hallmark 구조 다양화·안티패턴 감사 + Taste Skill(Leonxlnx) 브리프 해석·시각 강도 개념의 Vue 재구성 파생본 |

모든 외부 자료는 URL이나 해시를 별도로 기록하지 않는다 — 대화 중 사용자가 직접 첨부한 파일이라 출처가 "이 대화 자체"이며, 별도의 외부 URL·버전 관리가 없는 임시 업로드이기 때문이다. 재현이 필요하면 사용자에게 재첨부를 요청한다.

---

## GENERAL_HARNESS_논리구조_검수_리포트_2026-07-10.md 반영 (1~2라운드)

| 반입 대상 | 근거(피드백 번호) | 반영 방식 |
|---|---|---|
| `08.QUALITY_GATE.md §2`, `00.QUICK_REF.md §3` FAIL 해제조건 명확화 | C-01 | "사용자 확인만으로 FAIL 해제 불가, 수정 후 재검증 PASS만 인정"을 명시 |
| `04.GATEGUARD.md §6-1`(신규) 위험 유형별 해제 조건 SoT | C-02 | "추가 근거"를 위험 유형별로 구체적으로 정의하는 단일 표 신설, §6/§8을 이 표 참조로 정리 |
| `gates/api-gate.md`, `skills/api-design/SKILL.md`, `checklists/api-checklist.md` PASS 판정에 계약 상태 반영 | C-03 | "필수 항목" 표에만 있던 계약 상태 표시를 실제 PASS/FAIL 판정 행에도 반영 |
| `gates/payment-gate.md`, `checklists/payment-red-blue-checklist.md` 웹훅 FAIL/WARN 경계 | C-04 | "웹훅 검증 없음"(FAIL)과 "웹훅 검증 부족"(WARN)을 명확히 구분 |
| `checklists/release-checklist.md` 테스트/롤백/백업복구/배포후검증 추가 | C-05 | 항목 5개 추가, N/A 허용 |
| `07.SECURITY_BASELINE.md`, `gates/security-gate.md` PASS 정의 강화 | M-01 | "검토됨"을 "필수 통제 충족"으로 변경, 외부 응답 검증을 판정에 반영 |
| `gates/db-gate.md`, `checklists/erd-checklist.md` 필수값/유일성 반영 | M-02 | PASS/FAIL 판정에 NOT NULL/UNIQUE 기준 추가 |
| `gates/skill-gate.md` FAIL 기준을 `validate-skills.mjs`와 통일 | M-16 | Do Not Trigger, Required Inputs 누락도 FAIL로 명시 |

## GENERAL_HARNESS_논리구조_검수_리포트_2026-07-10.md 반영 (3~4라운드)

| 반입 대상 | 근거(피드백 번호) | 반영 방식 |
|---|---|---|
| `06.REPORT_TEMPLATE.md §8` superseded 템플릿을 `_LATEST.md` 참조로 변경 | M-04 근본 원인 | 특정 후속 경로 하드코딩을 없애 archive 이동 시 깨지지 않게 함 |
| `06.REPORT_TEMPLATE.md §8-2`(신설) Report 완료 트랜잭션 | M-03, M-05, P1-1 | 9단계 원자적 순서 정의, `09.AGENT_WORKFLOW.md §8`이 참조 |
| `scripts/validate-references.mjs` reports/ 포함 + archive 폴백 | M-04 | 통째 제외 대신 실제 검사, 알려진 예외 3건만 허용목록 등록 |
| `scripts/validate-report-consistency.mjs` 스킬 이름 집합 비교 + digest 부재 FAIL | M-06, P1-3 | 개수만이 아니라 실제 스킬명 집합을 구조적으로 비교 |
| `scripts/validate-package.mjs` ZIP 내부 실제 검사 | M-07 | 단일 루트/경로탈출/대소문자 중복/필수파일을 `unzip -Z1`로 검사 |
| `scripts/validate-harness.mjs` 필수 목록에 스크립트 7개 추가 | M-07 | 기존엔 validate-package.mjs만 있었음 |
| `scripts/validate-no-personal-paths.mjs` 예외 목록에서 실제 이름 제거, Unicode/경로 확장 | M-08 | 검사 목적과 반대로 실제 개인 이름이 예외에 있던 버그 수정 |
| `08.QUALITY_GATE.md §12` 표 복구, `§10-1` 보증범위 표 완성 | m-04, m-05 | 빈 줄로 끊긴 표 복구, 누락 스크립트 3개 추가 |

## GENERAL_HARNESS_논리구조_검수_리포트_2026-07-10.md 반영 (5~6라운드)

| 반입 대상 | 근거(피드백 번호) | 반영 방식 |
|---|---|---|
| `08.QUALITY_GATE.md §7` 사전 Gate 분기 추가 | M-09 | 흐름도가 사전 Gate 없이 시작하던 모순 수정 |
| `skills/quality-gate/SKILL.md` Checklist 조건부 명시, Handoff placeholder 제거 | M-10 | 실제 6개 Gate 결정표로 교체 |
| 스킬 5개 Output Format 실제 증거 필드 추가 | M-11 | api-design/error-handling/security-review/terminal-ops/git-workflow |
| `verification-loop`/`agent-recovery` 발동·종료 조건 자기모순 정리 | M-12 | Do Not Trigger 재정리, PASS/WARN 경계 명확화 |
| Checklist 5개 전체 결과/근거 열 추가, `08.QUALITY_GATE.md §7-1` 집계 규칙 신설 | M-13 | PASS/FAIL/N/A 3단 판정으로 확장 |
| `09.AGENT_WORKFLOW.md §2` Report/WC 갱신 조건부 명시 | M-15 | 무조건 실행처럼 보이던 흐름도 수정 |
| ADR/이력 파일 인용 오류 정정 다수 | m-01, m-02, m-03, m-06, m-07, m-08, m-09 | 수치·소유문서·자기지시어·표 이스케이프·bare 경로 보강 |
| `_SOURCE_MAPPING.md §0`(신설) 외부 근거 보존 상태 표 | M-14 | 외부 자료의 취득 경로·시점·보존 여부 정리(항목 수는 §0 표 참고, 새 검수 리포트가 도착할 때마다 행이 늘어남) |

## GENERAL_HARNESS_논리구조_검수_리포트_2026-07-10.md 반영 (두 번째 검수, C-01 라운드)

두 번째 외부 검수(같은 이름, ZIP 해시 대조 포함)에서 새로 지적된 항목.

| 반입 대상 | 근거(피드백 번호) | 반영 방식 |
|---|---|---|
| `06.REPORT_TEMPLATE.md §8-2` 순서를 "게시 전 검증"으로 재구성, 롤백 규칙 추가 | C-01 | 검증(6단계)보다 게시(`_LATEST.md` 갱신)가 먼저였던 구조적 결함 수정 |
| `06.REPORT_TEMPLATE.md §8-2` WC 갱신 소유문서 참조를 `05.WORKING_CONTEXT.md §8`로 정정 | M-04 | `03.CONTEXT_BUDGET.md §7`(다른 개념)을 잘못 인용하던 것 수정 |
| `_PENDING_IMPORT_LIST.md §8` 1~6라운드 전부 "완료"로 갱신 | M-03, X-05 | 5·6라운드를 완료 후에도 "대기"로 남겨뒀던 것 수정 |
| `_SOURCE_MAPPING.md`에 5~6라운드 반영 섹션 신설(이 섹션) | M-03, X-05 | 반영 근거 기록 자체가 누락되어 있었음 |
| `04.GATEGUARD.md §11-3` "게시가 검증을 앞지름" 패턴 신규 등록, 자기참조 갱신 누락 패턴 재발 횟수 갱신 | C-01 근본원인 | 4번째 재발한 메타 패턴을 구조적으로 반영 |

이 피드백 문서 원문은 패키지에 포함하지 않는다(외부에서 별도로 전달받음). 나머지 항목(3~6라운드)은 `_PENDING_IMPORT_LIST.md §8`을 따른다.

---

## GENERAL_HARNESS_논리구조_검수_리포트_2026-07-10.md 반영 (두 번째 검수, 남은 Major/Minor 라운드)

| 반입 대상 | 근거(피드백 번호) | 반영 방식 |
|---|---|---|
| `08.QUALITY_GATE.md §6` 사전 Gate WARN/FAIL 분리 | M-01 | FAIL은 재검증 PASS만 인정하도록 명시, 흐름도에 WARN/FAIL 분기 추가 |
| `09.AGENT_WORKFLOW.md`/`terminal-ops`/`00.QUICK_REF.md` 삭제·외부실행 승인 문구 통일 | M-02 | "항상 실시간 확인, 과거 근거 대체 불가"로 통일 |
| `skills/security-review/SKILL.md` 외부 응답 검증 절차·판정 동기화 | M-05 | 인증성/무결성/타임아웃/실패정책 확인 단계와 FAIL 기준 추가 |
| `gates/api-gate.md`/`checklists/api-checklist.md` 판정·항목 보강 | M-06 | Method/URL 판정 반영, 필드타입/필수·nullable/제약/오류코드 항목 추가 |
| `gates/payment-gate.md`/`checklists/payment-red-blue-checklist.md` 환불·지연웹훅 보강 | M-07 | 환불 상태전이·멱등성·보상처리, 지연 웹훅 시나리오 추가 |
| `gates/db-gate.md`/`checklists/erd-checklist.md` 수량·상태전이·삭제방식 보강 | M-08 | 판정표와 체크리스트에 1:1 연결 |
| `checklists/srs-checklist.md` 수용기준 등 보강 | M-09 | 수용기준/행위자/입출력/전제/예외/검증방법/비기능요구 추가(N/A 허용) |
| `checklists/release-checklist.md` 운영배포 전용 섹션 신설 | M-10 | 적용범위 필드 + §1-1(모니터링/로그/임계값/책임자/관찰기간) |
| `scripts/validate-package.mjs` 재작성 | M-11 | fail-open 제거(ZIP 미검사 시 WARN), 추출본-ZIP 전체 parity 비교 추가 |
| `scripts/validate-references.mjs` 섹션 참조 검사 추가 | M-12 | `파일.md §N` 존재 검사, 제외 문서 3개는 한계로 문서화 |
| `skills/planning/SKILL.md` 구현단계 생략 오독 문구 수정 | m-01 | 2곳 수정 |
| `gates/document-gate.md` 집계 규칙 참조 추가 | m-02 | `08.QUALITY_GATE.md §7-1` 참조 |
| `skills/quality-gate/SKILL.md` Output Format 보강 | m-03 | 적용 Gate/Checklist, 구조/의미 PASS 구분 필드 추가 |
| `10.ADR.md` ADR-021/022/023 오기 정정 | m-04, m-05, m-06 | 파일·스크립트 개수, Report 섹션 참조 정정 |

---

## GENERAL_HARNESS_문서세트_논리구조_검수_리포트_2026-07-11.md 반영 (세 번째 검수, ZIP SHA-256 대조 포함)

세 번째 외부 검수(Critical 3건 + 사용자 결정 5건 + Major 15건 + Minor 11건, 총 34건)의 상세 반영 매핑은 각 라운드 Report에 그대로 남아 있다 — 여기서는 반입 대상만 요약한다.

| 반입 대상 | 근거(피드백 번호) | 상세 근거 |
|---|---|---|
| ZIP 내용 SHA-256 비교, Report 게시 트랜잭션 재설계(검증 후 게시), 복합 Gate 최악판정 신설, `05.WORKING_CONTEXT.md` 프로젝트 템플릿 전환 | Critical 3건 + 사용자 결정 5건 | "2026-07-11_harness-external-review-critical-and-decisions_report"(원본은 2026-07-12 삭제됨, `reports/archive/HISTORY_DIGEST.md` 참고) |
| API/DB/Security/Payment Gate 필수-판정 재정리, 12개 스킬 HCR "중단" 문구 일괄 반영, `_WORKING_CONTEXT_HISTORY.md` 중복 섹션 제거 | Major 15건 + Minor 11건 | "2026-07-11_harness-external-review-major-minor_report"(원본은 2026-07-12 삭제됨, `reports/archive/HISTORY_DIGEST.md` 참고) |

## GENERAL_HARNESS_문서세트_논리구조_재검수_리포트_2026-07-11.md 반영 (네 번째 검수, 재검수, unzip 의존성 재작성)

네 번째 외부 검수(Critical 5건 + Major 14건 + Minor 8건, 총 27건)의 상세 반영 매핑도 각 라운드 Report에 남아 있다.

| 반입 대상 | 근거(피드백 번호) | 상세 근거 |
|---|---|---|
| `validate-package.mjs`를 순수 Node ZIP 파서로 전면 재작성(unzip 의존 제거), 게시 트랜잭션 원자적 교체(임시zip+백업+rename), 결제 복합Gate 매트릭스 SoT 확정(로그인 Payment Gate 오적용 정정), 대량이동 분류 SoT 통일 | Critical 5건 | "2026-07-11_harness-external-review-reaudit_report"(원본은 2026-07-12 삭제됨, `reports/archive/HISTORY_DIGEST.md` 참고) |
| `_LATEST.md` 포인터 전환 절차, Skill Handoff DAG 통일, 체크리스트 FAIL 강도 통일, 섹션참조 검사범위 확장(gates/skills 경로 포함), 고아행 정규식 일반화 등 | Major 14건 + Minor 8건 | 위와 동일 Report |

다섯 번째 검수(2026-07-12, Critical 4건·Major 8건·Minor 7건, "Major 수정 후 사용 가능" 판정)가 지적한 항목의 반영 매핑은 `reports/2026-07-12_harness-external-review_report.md`(원본은 이후 삭제됨, `reports/archive/HISTORY_DIGEST.md` 참고)에 남겼다. 여섯 번째 검수(재검수, 2026-07-12, Critical 0건·Major 10건·Minor 5건)의 반영 매핑은 `reports/2026-07-12_harness-external-review-round2-major-fixes_report.md`(원본은 이후 archive로 이동, 삭제되지 않음)에 남겼다. 4차부터 6차까지의 원문 provenance는 §0에 기록되어 있다(외부 검수 M-05→M-09→M-08로 이어진 지적 — §0에 4차 행이 실제로 빠져 있던 것과 5·6차 통계가 서로 뒤바뀌어 있던 것을 이번에 보강·정정했다).

## GENERAL_HARNESS_REPAIR_AND_SKILL_ROADMAP.md 반영

| 반입 대상 | 참고한 원본 | 반영 방식 |
|---|---|---|
| `skills/report-consistency/SKILL.md`(신규) | 피드백 문서 §5-1 `report-consistency` 스킬 제안 | 제안된 Trigger/Procedure/Quality Gate 구조를 그대로 채택하되, 이 하네스의 8단계 스킬 템플릿(`01.SKILL_TEMPLATE.md`) 형식에 맞춰 재작성 |
| `scripts/validate-report-consistency.mjs`(신규) | 피드백 문서 §6-1 검사 항목 제안 | 제안된 5개 검사 항목(포인터 존재/일치, 스킬 수 일치, superseded 표기 등)을 이 하네스 스크립트 스타일로 재작성 |
| `scripts/validate-references.mjs`(신규) | 피드백 문서 §5-2 `reference-integrity` 제안 | 스킬이 아니라 스크립트로만 구현하기로 결정(사용자 확인 완료). 오탐 방지를 위해 `_PENDING_IMPORT_LIST.md`/`_SOURCE_MAPPING.md`/`10.ADR.md`/`reports/*`는 검사 대상에서 제외 |
| `03.CONTEXT_BUDGET.md §4-2` 최신성 충돌 Stop Condition(신규) | 피드백 문서 §2-5, §9-5 | 예시 문구를 거의 그대로 채택 |

### 반입하지 않은 것

| 항목 | 반입하지 않은 이유 |
|---|---|
| `project-bootstrap`, `harness-maintenance`, `document-audit` 스킬 | 피드백 문서 스스로도 후순위로 판단했고, 검수 결과도 동의함. `_PENDING_IMPORT_LIST.md` §6-3에 도입 조건과 함께 보류 |
| `validate-zip-internals.mjs`, `validate-adr-unique.mjs` | 배포 패키징 빈도, ADR 누적량이 아직 자동화가 필요한 수준이 아님. `_PENDING_IMPORT_LIST.md` §6-3에 도입 조건과 함께 보류 |

---

## 1. 직접 반영한 핵심 참고

| 하네스 파일 | 참고한 ECC 자료 | 반영 방식 |
|---|---|---|
| `00.HARNESS_RULES.md` | `RULES.md`, `AGENTS.md`, `SECURITY.md` | 상위 규칙만 재작성 |
| `01.SKILL_TEMPLATE.md` | `docs/SKILL-DEVELOPMENT-GUIDE.md`, `skills/*/SKILL.md` | 공통 스킬 구조만 추출 |
| `02.SKILL_INDEX.md` | `agent.yaml`, `scripts/ci/catalog.js` | 목록 관리 개념만 축소 |
| `03.CONTEXT_BUDGET.md` | `skills/context-budget/SKILL.md` | 컨텍스트 예산 개념 반입 |
| `04.GATEGUARD.md` | `skills/gateguard/SKILL.md` | 수정 전 근거 확인 개념 반입 |
| `05.WORKING_CONTEXT.md` | `WORKING-CONTEXT.md` | 상태 관리 개념 축소 |
| `06.REPORT_TEMPLATE.md` | `skills/terminal-ops`, `skills/production-audit` | 증거 기반 리포트 구조 반입 |
| `07.SECURITY_BASELINE.md` | `SECURITY.md`, `skills/security-review` | 최소 보안 기준 반입 |
| `08.QUALITY_GATE.md` | `scripts/ci/validate-skills.js`, `scripts/hooks/quality-gate.js` | PASS/WARN/FAIL 구조 반입 |
| `09.AGENT_WORKFLOW.md` | `AGENTS.md`, `team-agent-orchestration` | 역할 기반 작업 흐름 축소 |
| `10.ADR.md` | 중간 강도 반입 산출물 | 이번 결정사항 기록 |

---

## 2. 직접 복사하지 않은 이유

원본은 참고자료이며, 이번 하네스는 사용자의 프로젝트 목적에 맞게 재작성된 버전이다.

직접 복사하지 않은 이유:

- ECC는 더 큰 Agent/Command/Hook 생태계를 전제한다.
- 현재 하네스는 초보 개발자와 팀 프로젝트 문서 검수에 맞춘 전역 공통 구조다.
- 과도한 자동화보다 문서 규칙 + 수동 Gate + 최소 scripts가 현재 단계에 적합하다.

---

## 3. v0.2 감사 피드백 반영

| 반영 대상 | 근거 | 반영 방식 |
|---|---|---|
| `00.HARNESS_RULES.md` | `HARNESS_AUDIT_REPORT.md` Critical C-1 | 충돌 해결 우선순위와 스킬 상하관계 추가 |
| `04.GATEGUARD.md` | `HARNESS_AUDIT_REPORT.md` Critical C-2, Major M-9/M-11 | 위험 작업 WARN 중단, 사용자 확인, 파일 수정 안전 규칙 추가 |
| `01.SKILL_TEMPLATE.md`, `skills/*/SKILL.md` | `HARNESS_AUDIT_REPORT.md` Critical C-3, Major M-1/M-7 | Harness Control Rule과 스킬별 Quality Gate 차별화 |
| `05.WORKING_CONTEXT.md`, `09.AGENT_WORKFLOW.md` | `HARNESS_AUDIT_REPORT.md` Critical C-4 | 실패/중단 후 재개 규칙 추가 |
| `08.QUALITY_GATE.md`, `scripts/*.mjs` | `HARNESS_AUDIT_REPORT.md` Major M-8 | 자동 검증 PASS의 한계 명시 |
| `gates/db-gate.md`, `_PENDING_IMPORT_LIST.md` | `HARNESS_AUDIT_REPORT.md` Major M-2/M-10 | 특정 스택 표현을 전역 중립 표현으로 완화 |
| `06.REPORT_TEMPLATE.md`, `checklists/*.md` | `HARNESS_AUDIT_REPORT.md` Major M-4/M-5/M-6 | Report/Working Context 책임 분리, Checklist 결과 이관 규칙 추가 |


---

## 4. v0.2.1 감사 피드백 반영

| 반영 대상 | 근거 | 반영 방식 |
|---|---|---|
| `gates/skill-gate.md` | `HARNESS_AUDIT_REPORT.md` C-1, M-1 | `Harness Control Rule` 필수 섹션화, 작업별 Quality Gate 확인 추가 |
| `scripts/validate-skills.mjs` | `HARNESS_AUDIT_REPORT.md` C-1 | `Harness Control Rule` 필수 검사와 저비용 상위 규칙 검사 추가 |
| `checklists/*.md` | `HARNESS_AUDIT_REPORT.md` C-2, M-7 | 원본 템플릿 사용 규칙, 일반 WARN/위험 WARN 분기, 고위험 체크리스트 FAIL 기준 강화 |
| `04.GATEGUARD.md`, `08.QUALITY_GATE.md` | `HARNESS_AUDIT_REPORT.md` M-5 | 사전 Gate와 사후 Gate 구분 추가 |
| `02.SKILL_INDEX.md`, `_PENDING_IMPORT_LIST.md` | `HARNESS_AUDIT_REPORT.md` M-2, M-3 | `db-patterns` 후보명 통일, 프로젝트 단계 표현 중립화 |
| `_SOURCE_MAPPING.md` | `HARNESS_AUDIT_REPORT.md` M-4 | v0.1 목적 문구를 현재 하네스 기준으로 수정 |


---

## v0.2.2 감사 피드백 반영

| 피드백 | 반영 위치 | 처리 |
|---|---|---|
| ADR 번호 중복 | `10.ADR.md` | v0.2.1 안정화 패치를 `ADR-007`로 수정하고 `ADR-008` 추가 |
| 현재 상태 표기 혼재 | `05.WORKING_CONTEXT.md` | 현재 구조를 v0.2.2로 갱신 |
| 과거 Report 다음 작업 충돌 | `reports/2026-06-24_harness-v0.2-audit-fix_report.md`, `03.CONTEXT_BUDGET.md`, `06.REPORT_TEMPLATE.md` | superseded 표시와 최신 Report 우선 규칙 추가 |
| HCR 본문 검사 완화 | `scripts/validate-skills.mjs` | HCR 최소 요건 강화 |
| Handoff 대상 존재 검사 | `scripts/validate-skills.mjs`, `_PENDING_IMPORT_LIST.md` | 기본 대상 존재 검사 반영, 복잡한 해석은 v0.3 후보 유지 |


---

## 안정 배포명 감사 피드백 반영

| 피드백 | 반영 위치 | 처리 |
|---|---|---|
| ZIP 루트명과 스크립트 루트 탐색 충돌 | `00.HARNESS_RULES.md`, `scripts/*.mjs` | 배포명은 `GENERAL_HARNESS.zip` / `GENERAL_HARNESS/`로 고정하고, marker 기반 root 탐색 적용 |
| Handoff 표기 규칙과 자동 검증 불일치 | `gates/skill-gate.md`, `skills/*/SKILL.md`, `scripts/validate-skills.mjs` | `skills/{skill-name}/SKILL.md` canonical 표기로 통일 |
| v0.2.1 Report superseded 누락 | `reports/2026-06-25_harness-v0.2.1-stabilization_report.md` | 최신 Report 기준 superseded note 추가 |
| Handoff 검증 상태 혼재 | `08.QUALITY_GATE.md`, `_PENDING_IMPORT_LIST.md` | 기초 구현 완료와 고급 후보를 분리 |


---

## Understand-Anything / codebase-memory-mcp 반영

| 반입 대상 | 참고한 원본 | 반영 방식 |
|---|---|---|
| `skills/planning/SKILL.md`(신규) | Understand-Anything `docs/superpowers/specs/*`, `docs/superpowers/plans/*` (Goal/Goals/Non-Goals/Task 분해 패턴, 5개 이상 spec에서 반복 확인) | TypeScript 구현 세부는 전부 제외, "Non-Goals를 필수로 요구한다"는 구조와 "Task마다 확인 방법을 명시한다"는 원칙만 재작성 |
| `skills/verification-loop/SKILL.md` Procedure 5단계, Quality Gate | codebase-memory-mcp `scripts/check-no-test-skips.sh` ("전제 조건을 충족 못한 SKIP은 FAIL이다") | 스크립트 자체는 반입하지 않고, 원칙 문장만 재작성해 기존 스킬에 추가 |
| `scripts/validate-no-personal-paths.mjs`(신규) | ECC `scripts/ci/validate-no-personal-paths.js` | 정규식 검사 아이디어만 가져오고 나머지는 이 하네스 스크립트 스타일(루트 탐색, PASS/FAIL 출력 형식)로 새로 작성 |

### 반입하지 않은 이유

| 항목 | 반입하지 않은 이유 |
|---|---|
| Understand-Anything 전체(대시보드, 멀티에이전트 파이프라인, Claude Code 플러그인) | 완제품 모노레포이며 참고자료가 아니라 설치형 도구. `_PENDING_IMPORT_LIST.md`에서 코드베이스 규모가 커질 때 재검토 조건으로 보류 |
| codebase-memory-mcp 전체(C 엔진, MCP 서버, `curl \| bash` 설치) | 설치형 외부 바이너리로 `00.HARNESS_RULES.md §7` 원칙에 해당. Git diff 영향도 매핑(`detect_changes`) 기능은 실제 코드 그래프가 있어야 가능해 지금 규칙 문서만으로는 흉내 낼 수 없음 |

---



## harness_import_candidates_20260704 반영

| 반입 대상 | 참고한 원본 | 반영 방식 |
|---|---|---|
| `skills/verification-loop/SKILL.md` | ECC `verification-loop/SKILL.md` | npm/tsc/pytest 등 특정 명령을 제거하고 "빌드/타입체크/린트/테스트/명세 일치" 단계만 하네스 문체로 재작성. Hook 설정 없음 |
| `skills/agent-recovery/SKILL.md` | ECC `agent-introspection-debugging/SKILL.md` | 4단계(캡처/분류/최소조치/재시도 제한)만 재작성 반입. 원본의 자동 스크립트/리포트 포맷 세부는 제외 |
| `skills/api-design/SKILL.md §4-1`, `gates/api-gate.md` 계약 상태 항목 | ECC `api-design/SKILL.md` | URL/페이지네이션 세부 패턴은 제외하고, "Candidate/Confirmed" 상태 구분 개념만 반입 |
| `09.AGENT_WORKFLOW.md §7-1` Handoff Note | ECC `strategic-compact/SKILL.md` | 토큰 한계 자동 감지 Hook과 명령어(`/compact`)는 제외하고, 사람/Agent가 직접 남기는 최소 인계 기록 형식만 반입 |
| `02.SKILL_INDEX.md §1-1` 스킬 대분류 | ECC `coding-standards/SKILL.md`의 "공통 바닥/세부 스킬 분리" 관점 | 특정 프레임워크(React 등) 언급 없이 문서/코드/운영 3분류 개념만 반입 |

### 반입하지 않은 이유

| 항목 | 반입하지 않은 이유 |
|---|---|
| `00.EXECUTOR_BOOT.md` 등 다중 실행자 분기 구조 | Source of Truth, Stop Condition 같은 SRS 전용 용어를 전제해 현재 `00.HARNESS_RULES.md §4` 고정 용어 체계와 충돌 검토가 필요함. 루트 `AGENTS.md` 최소 진입 지도는 별도 결정으로 채택했으며, 다중 부트 구조는 보류 |
| Understand-Anything(`understand-knowledge`, `understand-domain`, `understand-diff`) | 대상 프로젝트의 실제 코드베이스 규모가 아직 확인되지 않은 상태에서 자동 분석 도구를 도입하기는 이름 |
| codebase-memory-mcp | 설치형 외부 도구이며 `00.HARNESS_RULES.md §7`의 "외부 설치 스크립트 실행을 기본값으로 두지 않는다" 원칙에 따라 보류 |

반입하지 않은 항목은 `_PENDING_IMPORT_LIST.md`에 등급과 도입 조건을 기록한다.

---

## Runtime Slim Patch 반영

| 피드백 | 반영 위치 | 처리 |
|---|---|---|
| 일반 작업에서 `00.HARNESS_RULES.md` 전체 로딩 비용이 큼 | `00.QUICK_REF.md`, `03.CONTEXT_BUDGET.md`, `09.AGENT_WORKFLOW.md` | 런타임 요약 레이어 추가 및 S/M 작업 우선 로딩 규칙 반영 |
| 스킬별 Harness Control Rule 반복 | `skills/*/SKILL.md`, `01.SKILL_TEMPLATE.md` | 각 스킬의 HCR을 2줄로 축약하고 상세 기준은 템플릿과 Quick Ref에 위임 |
| Gate 위험 WARN 반복 문구 | `gates/api-gate.md`, `gates/db-gate.md`, `gates/payment-gate.md`, `gates/security-gate.md` | 반복 설명을 `08.QUALITY_GATE.md §3`, `04.GATEGUARD.md` 참조 한 줄로 축약 |
| 문서 헤더 보강 이력 주석 | 핵심 문서, Gate, Skill | 런타임 판단에 불필요한 보강 이력 주석 제거. 이력은 ADR/Report/Source Mapping에 보관 |
| `05.WORKING_CONTEXT.md` 분리 제안 | `_PENDING_IMPORT_LIST.md`, `03.CONTEXT_BUDGET.md` | 현재는 보류. 실제 프로젝트 적용 후 상태 기록 형식이 안정되면 재검토 |

---

## intent-to-implementation.zip 반영 (2026-08-02)

반입 판정의 근거 문서는 `HARNESS_문제점_종합정리_2026-08-02.md`(저장소 루트) P-15/P-16/P-18이며, 구조 결정은 `10.ADR.md` ADR-040이다.

| 반입 대상 | 참고한 원본 | 반영 방식 |
|---|---|---|
| `skills/intent-to-implementation/SKILL.md` | `intent-to-implementation/SKILL.md` | 영어 원문·YAML frontmatter를 제거하고 한국어 하네스 7섹션 표준으로 재작성. 기존 문서가 소유한 절차(작업 계약·사전 조사·계획·검증)는 본문에서 제거하고 참조로 치환 |
| `skills/intent-to-implementation/REFERENCE_INTENT_ROUTING.md` | `references/intent-routing.md` | 한국어 재작성. 위험 유형별 해제 조건의 소유권을 `04.GATEGUARD.md §6-1`로 명시 |
| `skills/intent-to-implementation/REFERENCE_REQUIREMENT_RECONSTRUCTION.md` | `references/requirement-reconstruction.md` | 한국어 재작성. 증거 우선순위가 `00.HARNESS_RULES.md §3`과 충돌하지 않도록 소유권 문장 추가 |
| `skills/intent-to-implementation/REFERENCE_MINIMAL_SOLUTION_COMPASS.md` | `references/minimal-solution-compass.md` | 한국어 재작성. `CLAUDE.md §2·§3`의 실행 절차라는 소유권 명시, GateGuard 승인 조항, Report 기록 단서 유지 |
| `skills/intent-to-implementation/REFERENCE_EXPLAIN_DIFF_FORMAT.md` | `references/explain-diff-format.md` | 한국어 재작성. 검증 기준 소유권을 `skills/verification-loop/SKILL.md`로 명시 |

### 반입하지 않은 이유

| 항목 | 반입하지 않은 이유 |
|---|---|
| Establish a Working Contract 섹션 | `AGENTS.md` 시작 순서 3이 이미 소유. 참조로 치환 |
| Inspect Before Designing 섹션 | `CLAUDE.md §1`과 `AGENTS.md` 시작 순서 1이 이미 소유. 참조로 치환 |
| Plan and Execute + `references/implementation-workflow.md` | `skills/planning/SKILL.md`와 `CLAUDE.md §2·§3`이 대부분 소유. 계층 책임 매핑은 필요해지면 `planning` 보강 후보로 재검토 |
| Validate the Result + `references/validation-rules.md` | `skills/verification-loop/SKILL.md`가 소유. 검증 사다리(좁은 검사→넓은 검사)는 verification-loop 보강 후보로 보류 |
| Response Contract 섹션 | `06.REPORT_TEMPLATE.md`가 소유. 스킬의 Output Format으로 축약 |
| `agents/openai.yaml`, `assets/icon.svg` | 특정 벤더 배포 규격. `_PENDING_IMPORT_LIST.md` X등급의 "MCP 설정 파일" 제외 사유와 같은 계열(반입 검수 P-18) |
| YAML frontmatter | `.claude/skills/` 자동 발견용 규격이라 하네스 스킬 템플릿과 불일치. 제거로 통일(반입 검수 Q-3 판정) |

---

## vue-ui-polish.zip 반영 (2026-08-03)

반입 판정의 근거는 `HARNESS_문제점_종합정리_2026-08-02.md` P-17/P-18/P-19와 Phase F이며, 구조 결정은 `10.ADR.md` ADR-043(스택 한정 스킬 범주 신설)이다.

| 반입 대상 | 참고한 원본 | 반영 방식 |
|---|---|---|
| `skills/vue-ui-polish/SKILL.md` | `vue-ui-polish/SKILL.md` | 하네스 7섹션 표준으로 재구성(본문은 원본이 이미 한국어). frontmatter 제거, HCR에 Vue 3 스택 한정 선언 추가, Handoff를 `browser-qa`→`verification-loop`→`ui-ux-gate`로 연결 |
| `skills/vue-ui-polish/REFERENCE_VUE_PATTERNS.md` | `references/vue-patterns.md` | 내용 그대로, 상단에 보조 문서 종속 명시만 추가 |
| `skills/vue-ui-polish/REFERENCE_MOTION_RULES.md` | `references/motion-rules.md` | 내용 그대로, 종속 명시 추가. §7 즉시 경고 패턴은 SKILL.md Anti-Patterns에도 요약 반영 |
| `skills/vue-ui-polish/REFERENCE_ANIMATION_VOCABULARY.md` | `references/animation-vocabulary.md` | 내용 그대로, 종속 명시 추가 |
| `skills/vue-ui-polish/LICENSE` | `LICENSE`(MIT, Emil Kowalski) | 원문 그대로 보존 — 하네스 첫 외부 LICENSE 반입 사례(P-19) |

### 반입하지 않은 이유

| 항목 | 반입하지 않은 이유 |
|---|---|
| `agents/openai.yaml`, `assets/icon.svg` | 특정 벤더 배포 규격 — ADR-040과 동일 사유(반입 검수 P-18) |
| YAML frontmatter | 하네스 스킬 템플릿과 불일치 — ADR-040과 동일 사유 |

---

## vue-ui-polish.zip 개정본 반영 (2026-08-04)

최초 반입(2026-08-03, ADR-043) 직후 사용자가 대폭 확장된 개정본을 제공해 교체 반입했다. 구조 결정은 `10.ADR.md` ADR-045(하네스 동결의 마지막 예외)다.

| 반입 대상 | 참고한 원본 | 반영 방식 |
|---|---|---|
| `skills/vue-ui-polish/SKILL.md` | 개정본 `SKILL.md` | 하네스 7섹션으로 재구성. 실행 모드 5종·판단 우선순위·필수 규칙을 Procedure/Quality Gate/Anti-Patterns로 배치. frontmatter 제거, 스택 한정 HCR과 `ui-ux-design` 소유권 경계 문장 추가 |
| `REFERENCE_MODES.md` 외 참조 10종 | `references/*.md` 11종 | 평면 `REFERENCE_*.md`로 개명, 종속 명시 추가, 내부 마크다운 링크를 코드 span으로 변환. 내용은 원문 유지(이미 한국어) |
| `skills/vue-ui-polish/scripts/ui-pattern-audit.mjs` | `scripts/ui-pattern-audit.mjs` | 원문 그대로 반입(순수 Node, 의존성 0). 스킬 보조 스크립트 첫 사례 — 규칙은 `01.SKILL_TEMPLATE.md §2-1` |
| `skills/vue-ui-polish/LICENSE` | 개정본 `LICENSE` | 저작권자 3인(Emil Kowalski, Hallmark 계열, Leonxlnx) 버전으로 교체 |

### 반입하지 않은 이유

| 항목 | 반입하지 않은 이유 |
|---|---|
| `agents/openai.yaml`, `assets/icon.svg` | 특정 벤더 배포 규격 — ADR-040/043과 동일 사유 |
| YAML frontmatter | 하네스 스킬 템플릿과 불일치 — 동일 사유 |
| 세 다이얼 수치의 전역 승격 | `REFERENCE_TASTE_STRATEGY.md` 내부의 제한 장치로만 유지. 스택 한정 스킬 밖으로 꺼내면 기술 중립 원칙과 충돌 |

## ECC·Brooks·Universal Flow 선별 통합 (2026-09-22)

기준: HARNESS 422d8433e6a8a84cbdb9fddfb8dad05623e52c7c. ADR-050 및 `reports/2026-09-22_harness-skill-integration_report.md` 참조. 원본은 사용자 제공 '추가 보강파일/sources'에 보존하고 Git에서 제외한다. 이번에 원격을 다시 조회한 것은 아니며 제공된 고정 커밋 메타데이터와 로컬 SHA-256을 대조했다. 파일별 출처·해시는 저장소 루트 docs/hardening/10-source-provenance.json에 있다.

| 원본 저장소·고정 커밋 | 차용 파일·부분 | 목적지 | 제외·라이선스 |
|---|---|---|---|
| [ECC](https://github.com/affaan-m/ECC/tree/bf70150eb2df8070024e5bdf08e4aa08959e2735) | skills/search-first/SKILL.md의 탐색·재사용 선택 근거 | intent-to-implementation의 최소 해법 참조 | 기존 스킬 전체를 ECC 원작으로 표시하지 않음. 해당 폴더 LICENSE에 ECC MIT 고지 |
| 같은 ECC 커밋 | skills/documentation-lookup/SKILL.md의 공식 근거·버전 조회 | documentation-lookup | Context7 강제·이름만으로 발동 제외. 폴더 LICENSE |
| 같은 ECC 커밋 | skills/tdd-workflow/SKILL.md의 기대 행동·실패/통과 증거 | test-design 및 verification-loop 연결 | 80%·자동 커밋·전체 TDD 강제 제외. test-design/LICENSE |
| 같은 ECC 커밋 | skills/skill-comply/SKILL.md, skills/eval-harness/SKILL.md의 기대 행동·기준선·관측 | skill-stocktake/REFERENCE_BEHAVIOR_EVAL.md | 자동 실행기·유료 채점 제외. skill-stocktake/LICENSE |
| [brooks-lint](https://github.com/hyhmrright/brooks-lint/tree/220fe716c01950966e961e020eda9c457f4dd0a7) | skills/brooks-review, skills/brooks-test의 SKILL/guide 및 _shared/common, source-coverage, decay-risks, test-decay-risks의 근거·영향·예외 원칙 | code-review 및 REFERENCE_TEST_REVIEW | 점수·줄 수 강제·sweep·자체 관리 제외. code-review/LICENSE에 원 MIT 고지 |
| 사용자 제공 universal-flow-document (원본 ZIP SHA-256 ec0241d100bd127b7264730bdbe4e47e6b92a0d81c580d416837383048a558a0; 제공 메타데이터 값) | SKILL·규칙의 의미 모델; templates/flow-document.schema.json; references JSON 8개 | universal-flow-document | SKILL/규칙 재작성, Node 검증기·뷰어 신규 구현. schema 제약·ongoing 경계 보강; stream 예시만 ongoing으로 수정. Python·캐시·벤더 파일·원 HTML/CSS 제외. 원본 LICENSE 없음; REFERENCE_PROVENANCE 참조 |

ECC/Brooks 원 고지는 바이트 동일하게 보존했다. 흐름 JSON 예시 7개는 원본 그대로이고 stream은 지속 연결을 성공 종료로 오인하지 않도록 명시적으로 보강했다. 단순 출력/복사 검증을 동작·보안·권리 보증으로 해석하지 않는다.
