# Working Context History

> 목적: `05.WORKING_CONTEXT.md`가 "현재 상태 요약본"으로 유지되도록, 지나간 라운드의 상세 서술을 여기로 이관해 보관한다.
> `05.WORKING_CONTEXT.md`에는 최신 1개 라운드의 상태 요약만 남기고, 그 이전 것은 여기로 옮긴다(`05.WORKING_CONTEXT.md §7` 장기 요약 규칙).
> 원본 내용은 요약하지 않고 그대로 옮겼다 — 정보 손실 없음.

---

## v0.2.1 상태 요약

- `Harness Control Rule`은 Skill Gate와 `validate-skills.mjs`에서 필수로 검사한다.
- 체크리스트 WARN은 일반 WARN과 위험 WARN으로 구분한다.
- 위험 작업은 수정 전 사전 Gate와 수정 후 사후 Gate를 구분한다.
- 새 스킬이나 무거운 자동화는 추가하지 않았고, v0.2 안전 규칙의 하위 문서/스크립트 정합성을 맞췄다.

---

## v0.2.2 상태 요약

- (당시 기준) 현재 기준은 `GENERAL_HARNESS v0.2.2`였다.
- `10.ADR.md`의 ADR 번호 중복을 정리하고 ADR 번호 고유성 규칙을 추가했다.
- 여러 Report가 있으면 최신 날짜 Report를 먼저 읽고, 오래된 Report는 증거로만 본다.
- v0.2 Report의 다음 작업은 v0.2.1/v0.2.2 이후 상태로 대체되었다.
- `validate-skills.mjs`는 `Harness Control Rule`의 본문 최소 요건과 Handoff 대상 존재를 더 엄격하게 확인한다.

---

## Import Candidate Blend 상태 요약

- `verification-loop`, `agent-recovery` 스킬을 신규 추가했다(활성 스킬 8개 → 10개).
- `02.SKILL_INDEX.md`에 스킬 대분류(문서/코드/운영)를 추가해 향후 스킬 확장 시 나열식 구조가 무너지지 않도록 했다.
- `skills/api-design/SKILL.md`, `gates/api-gate.md`에 API 명세의 `Candidate`/`Confirmed` 상태 구분을 추가했다.
- `09.AGENT_WORKFLOW.md §7-1`에 Handoff Note 최소 형식을 추가했다. Handoff Note는 우선 `05.WORKING_CONTEXT.md`에 남기고, 작업 단위 증거가 필요하면 해당 작업 Report 하단에도 같은 Handoff Note를 남긴다.
- Executor Boot·Claude·단수형 에이전트 문서 같은 별도 실행자 부트 문서, Understand-Anything, codebase-memory-mcp는 이번에 반입하지 않았다. 단, Claude/Codex 혼합 운영의 최소 역할 분기와 First Reading은 기존 문서인 `03.CONTEXT_BUDGET.md §2-3`, `09.AGENT_WORKFLOW.md §1-1`에서 처리한다. 근거는 `10.ADR.md` ADR-015, `_PENDING_IMPORT_LIST.md` §2를 참고.

> 참고: `05.WORKING_CONTEXT.md`의 §1~§3, 그리고 이 이력 파일의 상태 요약들은 하네스 "자체"의 개발 이력이다. 실제 대상 프로젝트에 이 하네스를 부착할 때는 `05.WORKING_CONTEXT.md`를 프로젝트 상태 요약본으로 새로 시작하거나, 하네스 이력과 프로젝트 이력을 구분해서 기록해야 한다. 초기화 절차는 `09.AGENT_WORKFLOW.md §7-2`를 따른다.

---

## Runtime Slim Patch 상태 요약

- 일반 작업의 런타임 진입점으로 `00.QUICK_REF.md`를 추가했다.
- `03.CONTEXT_BUDGET.md`는 S/M 작업에서 Quick Ref 우선 로딩을 권장한다.
- 초기 8개 스킬의 `Harness Control Rule`은 2줄 요약으로 축약했고, 이후 추가된 활성 스킬도 같은 원칙을 따른다.
- Gate의 위험 WARN 반복 설명은 `08.QUALITY_GATE.md §3`, `04.GATEGUARD.md` 참조로 축약했다.
- `05.WORKING_CONTEXT.md` 분리는 현재 보류한다.

---

## 2026-07-05 논리구조 패치 상태 요약

- `DOCUMENT_AUDIT_REPORT.md`의 Critical/Major/Minor 검수 결과를 기준으로 기존 문서 안에서 최소 수정했다.
- 구조 WARN을 삭제하지 않고 정식 3분류(`일반 WARN` / `구조 WARN` / `위험 WARN`)로 유지했다.
- `00.QUICK_REF.md`, `04.GATEGUARD.md`, `08.QUALITY_GATE.md`, 5개 Checklist에 구조 WARN 처리 기준을 동기화했다.
- 작업 계약 필드는 `목표 / 수정 대상 / 제외 대상 / 근거 / 적용 스킬·Gate / 위험도 / 검증 방법` 기준으로 맞췄다.
- API 계약 상태는 `Candidate / Confirmed / Deprecated`로 확장했고, DB 기준에는 실제 스키마·확정 문서·후보 문서 우선순위를 추가했다.
- (당시 기준) 최신 판단 기준 Report는 "2026-07-05_0100_harness-mixed-agent-alignment_report"였다(원본은 2026-07-12 삭제 로그로 정리됨, `reports/archive/HISTORY_DIGEST.md` 참고). 이후 여러 라운드가 지나며 대체되었으므로, 현재 기준은 항상 `reports/_LATEST.md`를 직접 확인한다.

---

## 2026-07-05 혼합 운영 정렬 상태 요약

- 혼합 운영(Claude+Codex) 관련 외부 검수 피드백의 Major/Minor 지적사항을 기준으로 기존 문서 안에서 최소 보강했다. 피드백 원본 문서는 현재 보존되어 있지 않다.
- Claude/Codex 혼합 운영은 별도 Executor Boot 문서를 만들지 않고 `03.CONTEXT_BUDGET.md §2-3`, `09.AGENT_WORKFLOW.md §1-1`의 최소 역할 분기로 처리한다.
- SRS 원본/추출본/요약본/색인 우선순위는 `checklists/srs-checklist.md §0-1`이 소유하고, 일반 문서 Gate는 이를 참조한다.
- Memory/Lessons Learned는 현재 일반 하네스의 필수 문서가 아니며 프로젝트별 확장 후보로 둔다.

---

## 2026-07-09 외부 피드백 수용 상태 요약

- `GENERAL_HARNESS_REPAIR_AND_SKILL_ROADMAP.md` 피드백의 사실 관계를 전부 직접 대조 검증했고(검수 리포트 참고), 명백히 틀린 주장은 없었다.
- `05.WORKING_CONTEXT.md`의 낡은 현재형 고정 경로 문장을 "당시 기준"으로 재작성했다.
- `03.CONTEXT_BUDGET.md §4-1`의 깨진 표 행을 복구하고, §4-2 최신성 충돌 Stop Condition을 신설했다.
- top-level `reports/`에 superseded 표시 없이 남아있던 과거 Report 4개에 표시를 추가하고 `reports/archive/`로 이동했다. 이제 top-level에는 최신 Report 1개만 남는다.
- `skills/report-consistency/SKILL.md`, `scripts/validate-report-consistency.mjs`, `scripts/validate-references.mjs`를 신설했다(활성 스킬 11개 → 12개, 자동화 스크립트 5개 → 7개).
- `project-bootstrap`, `harness-maintenance`, `document-audit` 스킬과 `validate-zip-internals.mjs`, `validate-adr-unique.mjs`는 피드백 문서 자신의 판단에 동의해 보류했다. 근거는 `10.ADR.md` ADR-018, `_PENDING_IMPORT_LIST.md` §6-3을 참고.

---

## 2026-07-09 실수 패턴 승격 상태 요약

- `reports/`(및 `reports/archive/`) 전체를 스캔해 반복된 실수 패턴 5건을 확인하고, `04.GATEGUARD.md §11` 금지 패턴으로 승격했다(근거: `10.ADR.md` ADR-019).
- 1회만 확인된 패턴 3건(스킬명 겹침, 섹션 제목 실수 삭제, Handoff 형식 불일치)은 승격 기준(2회 이상)에 미달해 관찰 목록으로만 남겼다.

---

## 2026-07-09 압축·정리·자동검사 상태 요약

- 우선순위 표(`00.HARNESS_RULES.md §3`=`00.QUICK_REF.md §1`), PASS/WARN/FAIL 표(`00.QUICK_REF.md §3`, `06.REPORT_TEMPLATE.md §6`)의 완전 중복을 제거하고 참조 문장으로 축약했다. `scripts/validate-docs.mjs`의 표 추출 버그도 함께 고쳤다.
- `_WORKING_CONTEXT_HISTORY.md`(과거 라운드 상세 이관), `reports/archive/HISTORY_DIGEST.md`(archive 압축 색인)를 신설했다.
- `04.GATEGUARD.md §11`을 위험 작업/문서 편집 위생/자동화·이력 관리 위생 3개 소분류로 재구성했다.
- `_WORKING_CONTEXT_HISTORY.md`의 "(당시 기준)" 표기 누락, `05.WORKING_CONTEXT.md`의 연속 빈 줄 서식을 수정했다.
- `HISTORY_DIGEST.md`가 archive 폴더 실제 내용(17~18개)보다 뒤처져 있던 것을 발견해 누락분을 채우고, `scripts/validate-report-consistency.mjs`에 "archive 파일 수 vs 색인 수 일치" 자동 검사를 추가했다(회귀 테스트로 실제 탐지 확인).
- 이 자동 검사를 추가한 직후, `05.WORKING_CONTEXT.md`의 "최신 1개 라운드만 남긴다"는 §7 규칙 자체가 3라운드째 지켜지지 않고 있던 것을 발견했다(자기 참조 색인/요약이 갱신에서 누락되는 패턴이 두 번째로 재발). `04.GATEGUARD.md §11-3`에 일반화된 패턴으로 승격했다.

---

## 2026-07-10 외부 검수 1~2라운드 상태 요약

- 외부 검수 리포트(`GENERAL_HARNESS_논리구조_검수_리포트_2026-07-10.md`, Critical 5·Major 16·Minor 9, 총 55개 항목)의 Critical 5건 전부와 M-05를 직접 파일 대조로 검증했다. C-02, X-06/M-06은 피드백의 프레이밍이 다소 과장돼 있었음을 확인했다.
- 55개 항목을 6라운드로 나누기로 합의하고 1~2라운드(C-01~C-05, M-01, M-02, M-16)를 완료했다: FAIL 해제조건 단일화(수정+재검증만 인정), `04.GATEGUARD.md §6-1` 위험 유형별 해제조건 SoT 신설, API/DB/보안/결제/릴리즈/스킬 Gate의 "필수 항목 표"와 "실제 PASS/FAIL 판정"을 1:1로 맞춤.
- 새 원칙 D-017을 추가했다: Gate/Checklist/Skill의 필수 항목은 항상 실제 판정 행에 반영되어야 한다.

---

## 2026-07-10 외부 검수 3~4라운드 상태 요약

- 3라운드(M-03~M-06, P1-1, P1-3): `06.REPORT_TEMPLATE.md §8`의 superseded 템플릿을 특정 경로 대신 `reports/_LATEST.md` 참조로 바꿔 M-04의 근본 원인을 고쳤다. `§8-2`(신설)에 Report 완료 트랜잭션 9단계를 정의했다. `validate-references.mjs`가 이제 `reports/`도 archive 폴백과 함께 검사한다. `validate-report-consistency.mjs`가 스킬 이름 집합까지 구조적으로 비교한다.
- 4라운드(M-07, M-08, m-04, m-05): `validate-package.mjs`가 실제 ZIP 내부(단일 루트/경로탈출/중복/필수파일)를 검사한다. `validate-harness.mjs` 필수 목록에 스크립트 7개를 전부 추가했다. `validate-no-personal-paths.mjs`에서 실제 사용자 이름이 예외 목록에 있던 것을 제거하고 Unicode·경로 패턴을 넓혔다. `08.QUALITY_GATE.md`의 깨진 표와 불완전한 보증범위 표를 고쳤다.
- 새 원칙 D-018을 추가했다: superseded note는 `reports/_LATEST.md`를 참조하고, Report는 §8-2의 9단계를 전부 마쳐야 완료다.

---

## 2026-07-10 외부 검수 5~6라운드 상태 요약 (55개 항목 전체 완료 — 당시 기준)

- 5라운드(M-09~M-13, M-15): `08.QUALITY_GATE.md §7` 전체 흐름도에 사전 Gate 분기를 추가했다. `quality-gate` 스킬의 placeholder Handoff를 실제 Gate 결정표로 바꿨다. 5개 스킬(api-design/error-handling/security-review/terminal-ops/git-workflow) Output Format에 실제 증거 필드를 추가했다. `verification-loop`/`agent-recovery`의 발동·종료 조건 모순을 정리했다. 5개 Checklist 전체에 결과/근거 열을 추가하고 집계 규칙(`08.QUALITY_GATE.md §7-1`)을 신설했다. `09.AGENT_WORKFLOW.md §2` 흐름도의 Report/WC 갱신을 조건부로 명시했다.
- 6라운드(m-01~m-03, m-06~m-09, M-14): ADR 수치 정정, `_WORKING_CONTEXT_HISTORY.md`의 잘못된 인용 2건 정정, Memory 최소형식에 근거 링크 추가, Skill Template 예시 오용 방지 문구 추가, archive Report 표 파이프 이스케이프, bare 참조 경로 보강, `_SOURCE_MAPPING.md §0`에 외부 근거 보존 상태 표를 신설했다.
- 새 원칙 D-019를 추가했다: 스킬 발동 조건과 완료 판정은 서로 다른 축으로 나눠 판정한다.
- (당시 기준) 외부 검수 리포트(2026-07-10, 55개 항목) 전체를 6라운드에 걸쳐 검증·반영 완료했다고 판단했으나, 두 번째 검수에서 Report 완료 트랜잭션 자체의 결함(C-01)과 Pending/Source Mapping 갱신 누락(M-03/X-05)이 추가로 발견되어 다음 라운드에서 수정했다.

---

## 2026-07-10 두 번째 외부 검수 — C-01 게시 순서 결함 수정 상태 요약

- 같은 이름의 두 번째 검수 리포트(ZIP SHA-256 해시 대조, Windows 환경 재현 포함)가 도착했다. Critical 1건(C-01)과 Major 3건(M-03, M-04, M-11 등)을 직접 파일 대조로 검증한 뒤 반영했다.
- **C-01**: `06.REPORT_TEMPLATE.md §8-2`(직전 라운드에 만든 Report 완료 트랜잭션) 자체가 검증보다 게시(`_LATEST.md` 갱신)를 먼저 하는 결함이 있었다. "초안 → 검증 → (PASS/WARN만) 게시 → 게시 후 재검증 → 실패 시 롤백" 순서로 재구성했다.
- **M-04**: 같은 섹션이 WC 갱신 소유 문서를 `03.CONTEXT_BUDGET.md §7`(다른 개념)로 잘못 인용하던 것을 `05.WORKING_CONTEXT.md §8`로 정정했다.
- **M-03/X-05**: 5~6라운드를 완료했는데도 `_PENDING_IMPORT_LIST.md`와 `_SOURCE_MAPPING.md`가 계속 "대기"로 남아있던 것을 발견해 "완료"로 갱신하고, 5~6라운드 반영 근거 섹션을 신설했다. 이는 "자기 참조 갱신 누락" 패턴의 3번째 재발이다.
- 새 원칙 D-020을 추가했다: 현재 상태를 가리키는 포인터는 검증 통과 후에만 갱신한다.

---

## 2026-07-10 두 번째 외부 검수 — 남은 Major/Minor 전체 완료 상태 요약

- C-01 라운드에 이어, 같은 검수 리포트의 남은 Major 10건(M-01, M-02, M-05~M-12)과 Minor 6건(m-01~m-06)을 전부 처리했다.
- 대부분 D-017 원칙("필수 항목과 실제 판정은 1:1")의 재발 사례였다: API Gate의 Method/URL, DB Gate의 수량, Payment Gate의 환불 시나리오, SRS/Release Checklist의 여러 항목이 필수 선언만 있고 판정에는 없었다.
- **M-11**: `validate-package.mjs`가 ZIP을 못 열어도 PASS를 반환하던 fail-open을 제거하고, 추출본-ZIP 전체 파일 parity 비교를 추가했다(양성/음성/parity 불일치 3가지 시나리오로 직접 테스트).
- **M-12**: `validate-references.mjs`에 `파일.md §N` 섹션 참조 존재 검사를 추가했다(회귀 테스트로 확인). 3개 제외 문서(`_PENDING_IMPORT_LIST.md` 등)는 여전히 검사 안 됨을 정직하게 문서화했다.
- 새 원칙 D-021을 추가했다: 자동 검증 스크립트는 검사를 못 했을 때 PASS를 반환하지 않는다(fail-open 금지).
- 두 번째 외부 검수 리포트(Critical 1 + Major 12 + Minor 6, 총 19건) 전부 처리 완료.

---

## 2026-07-10 §12 사용자 확인 사항 5건 최종 결정 상태 요약

- 두 번째 외부 검수 리포트 §12의 사용자 확인 사항 5건 중 (2) Report 게시 순서, (3) release-checklist 적용범위는 이미 이전 라운드(ADR-024, ADR-025)에서 반영 완료된 상태였다.
- (1) 환경 변경 분리: **적용함.** `04.GATEGUARD.md §6-1`에 "되돌릴 수 있는 로컬 환경 변경(비파괴적)"을 신설해 삭제·외부 설치(예외 없는 실시간 확인)와 분리하고 구조 작업과 동일하게 완화했다. `00.QUICK_REF.md §2`도 함께 정리했다.
- (4) 외부 근거 provenance 장기 재검증: **지금은 투자하지 않기로 결정.** 대화 중 일회성 첨부라 안정 URL/해시를 유지보수할 방법이 없어, `_SOURCE_MAPPING.md §0`의 기존 한계 기록으로 충분하다고 판단. 실제 프로젝트 저장소 부착 시 재검토.
- (5) Checklist 엄격도 획일화: **하지 않기로 결정.** 현재의 "N/A + 근거" 방식이 프로젝트 규모에 따른 유연성을 유지하면서도 항목 자체는 빠짐없이 보이게 하는 더 나은 절충안이라고 판단.
- 새 원칙 D-022를 추가했다: 삭제·외부 설치는 항상 실시간 승인, 비파괴적 환경 변경은 구조 작업과 동일하게 완화한다.
- 두 번째 외부 검수 리포트(Critical 1 + Major 12 + Minor 6 + §12 확인사항 5건)가 완전히 마무리됐다.

---

## GENERAL_HARNESS 자체 개발 이력 완결편 (05.WORKING_CONTEXT.md를 신규 프로젝트 템플릿으로 전환하며 이관)

`05.WORKING_CONTEXT.md`를 실제 프로젝트에 부착할 수 있는 빈 템플릿으로 바꾸면서, 그 문서에 남아있던 하네스 자체의 상태 이력·결정사항·작업 큐를 전부 여기로 옮겼다(정보 손실 없음, 요약하지 않고 그대로 이관).

### 하네스 자체 상태 이력(구 §1 하단 행)

| 항목 | 상태 |
|---|---|
| Rename v1 | `GLOBAL_AI_HARNESS` → `GENERAL_HARNESS`(폴더/zip/패키지명), "전역 하네스" → "일반 하네스"(문서 전체). 근거는 `10.ADR.md` ADR-016 |
| Batch Import v1 | `planning` 스킬 신설(Understand-Anything의 Spec/Non-Goals/Task 분해 패턴 재작성), `verification-loop`에 SKIP=FAIL 원칙 추가(codebase-memory-mcp 참고), `scripts/validate-no-personal-paths.mjs` 신설(ECC 참고), `03.CONTEXT_BUDGET.md` 중복 읽기 방지 원칙, `00.HARNESS_RULES.md` Memory 승격 경로, `09.AGENT_WORKFLOW.md` 대화 메모리 보조수단 원칙, `reports/archive/` 아카이빙 도입. 근거는 `10.ADR.md` ADR-017 |
| 외부 피드백 수용 v1 | `report-consistency` 스킬, `scripts/validate-report-consistency.mjs`, `scripts/validate-references.mjs` 신설. Report 최신성 오류(낡은 경로 고정 지목, 표 구조 깨짐, superseded 미표시) 전부 수정. 근거는 `10.ADR.md` ADR-018 |
| Import Candidate Blend | `harness_import_candidates_20260704` 중 verification-loop, agent-recovery, 계약 상태(Candidate/Confirmed), Handoff Note, 스킬 대분류를 재작성 반입. Executor Boot·Claude·단수형 에이전트 문서 같은 별도 실행자 부트 문서는 보류하되, Claude/Codex 혼합 운영의 최소 역할 분기와 First Reading은 `03.CONTEXT_BUDGET.md §2-3`, `09.AGENT_WORKFLOW.md §1-1`에 반영 |
| v0.2 핵심 보강 | 충돌 우선순위, 위험 WARN 중단, 하네스>스킬, 재개 규칙, 스킬별 Gate 차별화 |
| v0.2.1 안정화 | Harness Control Rule 필수 검증, 위험 WARN 분기, 사전/사후 Gate 구분 |
| v0.2.2 유지보수 | ADR 번호 고유성, 최신 Report 우선, 과거 Report superseded, HCR 본문 요건 강화 |
| 안정 배포명 유지보수 | `GENERAL_HARNESS.zip` / `GENERAL_HARNESS/` 기준, Handoff canonical 표기 정리 |
| Runtime Slim 보강 | Quick Ref 우선 로딩, Gate WARN 힌트 복원, 재개 규칙 소유권 복원 |

### 하네스 자체 핵심 결정사항(구 §2, D-001~D-022 전체)

| 번호 | 결정 | 이유 |
|---:|---|---|
| D-001 | ECC 전체를 복제하지 않는다 | 현재 목적은 일반 하네스이며, 과도한 Agent/Command 구조는 무거움 |
| D-002 | 핵심 문서 + 핵심 스킬 + Gate + Checklist 구조로 간다 | 문서만 있는 하네스와 자동화만 많은 하네스 사이의 중간 강도 유지 |
| D-003 | 초기에는 스킬 8개만 우선 활성화했고, 이후 `verification-loop`, `agent-recovery` 반영으로 10개 활성 스킬을 사용했다(당시 기준) | 초반 선택 비용을 낮추되, 반복 필요성이 확인된 검증/복구 스킬은 확장함 |
| D-004 | scripts는 최소 검증만 수행한다 | 초기부터 자동 차단 hook을 강제하지 않음 |
| D-005 | 결제/보안은 별도 Gate와 Red/Blue Checklist를 둔다 | 일반 기능보다 실패 비용이 큼 |
| D-006 | 하네스는 모든 스킬보다 상위 규칙이다 | 스킬 절차가 안전 규칙을 덮어쓰지 않게 함 |
| D-007 | 위험 작업의 WARN은 기본 중단/확인으로 처리한다 | 삭제, DB, 결제, 보안 작업 사고를 막기 위함 |
| D-008 | 자동 검증 PASS는 구조 PASS로만 해석한다 | 의미 품질과 운영 안전성을 과신하지 않기 위함 |
| D-009 | 여러 Report가 있으면 최신 Report와 Working Context를 우선한다 | 오래된 Report의 다음 작업이 현재 상태를 덮어쓰지 않게 함 |
| D-010 | ADR 번호는 고유해야 한다 | 결정 추적성과 인용 안정성을 유지하기 위함 |
| D-011 | 배포 파일명과 루트 폴더명은 버전 suffix 없이 고정한다 | 스크립트 실행 위치 혼동과 패키지명 충돌을 줄이기 위함 |
| D-012 | Handoff 스킬 표기는 `skills/{skill-name}/SKILL.md`로 고정한다 | 문서 규칙과 자동 검증의 해석 차이를 없애기 위함 |
| D-013 | 외부 반입 후보(`harness_import_candidates_20260704`)는 원본 그대로 반입하지 않고, 필요한 것만 골라 하네스 문체로 재작성한다 | 원본이 특정 스택(npm/TypeScript 등)·Hook 자동화 전제이며, 실행자 분기(Executor Boot) 같은 대형 구조 변경은 현재 단계에 과함 |
| D-014 | 하네스의 "현재 상태" 서술은 항상 `reports/_LATEST.md`를 가리키게 하고, 특정 Report 경로를 문장에 직접 고정하지 않는다 | 외부 검수에서 낡은 경로 고정 지목 문제가 실제로 발견됨(ADR-018) |
| D-015 | Report 기록에서 2회 이상 반복 확인된 실수 패턴은 `04.GATEGUARD.md §11` 금지 패턴으로 승격한다 | 반복되는 실수를 기록만 하고 방치하지 않기 위함(ADR-019) |
| D-016 | 자기 참조용 색인·요약 문서(HISTORY_DIGEST, Working Context 최신 상태 요약 등)는 라운드가 끝나는 즉시 그 자리에서 갱신한다 | 같은 유형의 갱신 누락이 서로 다른 문서에서 2회 재발함(ADR-020) |
| D-017 | Gate/Checklist/Skill의 "필수 항목" 표와 실제 PASS/WARN/FAIL 판정 행은 항상 1:1로 맞춘다. 필수라고 선언한 항목이 판정에 반영되지 않는 것을 금지한다 | 외부 검수에서 API/DB/보안/스킬 Gate 다수에 이 유형의 불일치가 발견됨(ADR-021) |
| D-018 | Report의 superseded note는 특정 후속 Report 파일명을 직접 쓰지 않고 `reports/_LATEST.md`를 참조한다. Report 작성은 `06.REPORT_TEMPLATE.md §8-2`의 9단계를 전부 마쳐야 완료로 본다 | 하드코딩된 후속 경로가 archive 이동으로 반복 깨짐(ADR-022) |
| D-019 | 스킬의 Trigger/Do Not Trigger와 Quality Gate PASS/WARN 경계는 서로 다른 축(작업 규모 vs 완료 상태)으로 판정하고, 한 조건이 두 판정에 동시에 걸치지 않게 한다 | 외부 검수에서 verification-loop/agent-recovery의 발동·종료 조건이 자기모순으로 읽히는 문제가 발견됨(ADR-023) |
| D-020 | "현재 상태를 가리키는 포인터"(`reports/_LATEST.md` 등)는 검증을 통과한 뒤에만 갱신한다. 검증 전에 게시부터 하지 않는다 | Report 완료 트랜잭션 자체에 이 순서가 뒤바뀐 결함이 있었음(ADR-024) |
| D-021 | 자동 검증 스크립트는 검사를 실제로 수행하지 못했을 때 PASS를 반환하지 않는다(fail-open 금지). 검사 못 한 상태는 WARN으로 명확히 표시한다 | `validate-package.mjs`가 ZIP을 못 열어도 PASS를 반환하던 결함이 발견됨(ADR-025) |
| D-022 | 삭제·외부 설치는 항상 실시간 승인이 필요하지만, 되돌릴 수 있는 로컬 환경 변경(비파괴적)은 구조 작업과 동일하게 승인 또는 유효한 근거로 완화한다 | 두 위험도가 지금까지 같은 급으로 묶여 있었음(ADR-026) |

이 결정들이 만든 실제 규칙은 각 소유 문서(`04.GATEGUARD.md`, `08.QUALITY_GATE.md`, `06.REPORT_TEMPLATE.md` 등)에 그대로 살아있다 — 이 표를 이관한다고 규칙 자체가 사라지는 것이 아니라, "왜 그 규칙이 생겼는지"에 대한 이력만 옮기는 것이다.

> `05.WORKING_CONTEXT.md`가 신규 프로젝트 템플릿으로 전환된 이후(ADR-027), 하네스 자체의 새 구조적 결정은 여기에 D-023부터 이어서 기록한다. 상세 배경·근거는 항상 `10.ADR.md`의 해당 ADR을 함께 참고한다.

| 번호 | 결정 | 이유 |
|---:|---|---|
| D-023 | 배포 SoT는 `GENERAL_HARNESS.zip`이다. Report 완료 트랜잭션은 게시(zip 생성 포함) 이후 Report 파일을 더 수정하지 않고, 최종 검증 결과는 Report가 아니라 전달 메시지(채팅)에 기록한다 | Report 파일 자기수정이 순환을 만드는 문제가 반복됨(ADR-027) |
| D-024 | 산출물이 여러 Gate에 동시에 해당하면 전부 적용하고 최악 판정을 최종 판정으로 쓴다. 결제·환불은 API+Security+Payment Gate를 항상 함께 적용한다 | 복합 산출물에 Gate를 하나만 매핑하던 결함이 발견됨(ADR-027) |
| D-025 | 배포 zip은 기존 파일을 직접 덮어쓰지 않는다. 임시 이름으로 먼저 만들고 전체 검증을 통과해야만 원자적으로 교체(rename)한다. 자동 검증 스크립트는 외부 CLI 명령에 의존하지 않고, 가능하면 언어 표준 라이브러리만으로 직접 검사한다 | ZIP 게시 트랜잭션에 백업·원자적 교체가 없었고, `unzip` CLI 의존으로 인해 그 명령이 없는 환경에서 검사 자체가 조용히 새는 결함이 발견됨(ADR-028) |
| D-026 | 복합 산출물의 Gate 적용 매트릭스는 한 문서(`08.QUALITY_GATE.md §7-2`)에만 정의하고, 다른 모든 문서는 그 표를 참조만 한다. Report 상단의 "게시 상태" 필드와 "최종 검증 수치"는 서로 다른 규칙을 따른다 — 상태 필드는 게시 완료 시 그 자리에서 갱신하고, 수치는 채팅에만 남긴다 | 결제 복합 Gate가 문서마다 다르게 정의돼 있었고, Report 자신이 "게시 전"이라 자칭하는데 `_LATEST.md`는 "완료"라고 하는 모순이 발견됨(ADR-028). **`Partially superseded by D-028`** |
| D-027 | 자동 검증 스크립트가 검사 대상 경로를 하드코딩하지 않는다 — 게시 트랜잭션이 후보 파일을 지정해 검사해야 하면 스크립트는 그 경로를 인자로 받아야 한다 | 게시 절차가 후보 zip을 검증하라고 문서에 적어놓고 정작 스크립트는 고정 경로만 봐서 후보를 실제로 검증한 적이 없던 결함이 발견됨(ADR-029) |
| D-028 | Report 파일 안에 "게시 상태"(게시 전/완료) 같은 자기 참조 필드를 두지 않는다. 게시 여부는 파일 내부 선언이 아니라 `reports/_LATEST.md` 포인터와 archive 위치라는 외부 신호로 판단한다 | 상태 필드를 게시 후 갱신하는 것 자체가 이미 검증을 마친 ZIP과 디스크 트리를 다시 어긋나게 하는 파일 수정이었음이 발견됨(ADR-029, D-026을 대체) |
| D-029 | 배포 모델은 템플릿 복제다. `GENERAL_HARNESS.zip`은 원본 템플릿 전용이고, 각 프로젝트는 부착 시점에 각자 복제해서 그 프로젝트만의 사본으로 관리한다. 하네스 자체 개선은 이미 부착된 사본에 자동 반영되지 않는다 | 사용자에게 "보통 하네스는 프로젝트별로 어떻게 쓰나" 확인한 결과 템플릿 복제 모델로 확정됨(ADR-030) |
| D-030 | 오래된 Report 원본은 기본적으로 삭제하지 않지만, 사용자가 명시적으로 요청하면 "요약(HISTORY_DIGEST) 선행 보존 + 삭제 로그 기록" 조건으로 삭제할 수 있다. 삭제는 항상 실시간 사용자 확인이 필요하다(예외 없음) | archive Report가 너무 많아져 사용자가 원본 삭제를 요청함. 삭제 전 실제 영향을 테스트해 먼저 알린 뒤 진행함(ADR-031) |
| D-031 | 자기 참조 검증 로직에서 "날짜"처럼 하루 단위로 뭉뚱그려지는 정보로 대상을 추정하지 않는다. 특정 항목이 "이미 확인된 예외인지"를 판단해야 하면 명시적 식별자(파일명 전체 목록 등)를 그대로 나열해 대조한다 | 삭제 로그의 날짜 cutoff 방식이 같은 날 추가된 새 고아 항목을 못 잡는 것이 실제로 재현됨(ADR-032) |
| D-032 | 명시적 예외 목록(PURGED_FILES류) 자체도 구조적으로 검증한다 — marker 유일성, 목록이 다른 소스(digest)의 부분집합인지, 실제 상태(archive)와 모순되지 않는지, 개수가 일치하는지를 전부 확인한다. 목록에 이름만 추가하면 스스로 예외를 승인할 수 있게 두지 않는다 | 지난 라운드의 명시적 목록 방식도 무단 추가·개수 조작·연도 하드코딩으로 우회 가능함이 재현됨(ADR-033) |
| D-033 | 하네스 패키지 자체의 게시 트랜잭션(ZIP 생성 포함)과 개별 프로젝트의 Report 완료 트랜잭션(ZIP 없음)은 서로 다른 절차이며 같은 절에서 섞어 쓰지 않는다 | project Report가 §8-2(하네스 전용)를 따르는지 아닌지 문서마다 다르게 서술되어 충돌했음(ADR-033) |
| D-034 | 여러 판정 소스(Verification, Gate, Checklist)가 있는 산출물의 최종 판정은 전역 공식(최악 판정)으로 통일한다. 각 Checklist의 "결과 요약"은 그 Checklist 자체의 판정이지 산출물 전체의 최종 판정이 아니다 | 비릴리즈 구현에서 Verification FAIL이 최종 판정에 반영된다는 보장이 없었음(ADR-033) |
| D-035 | 게시 트랜잭션에서 WARN은 FAIL 없다고 곧바로 통과시키지 않는다. 구조·위험 WARN은 해제 증거를 확보해야 다음 단계로 진행한다 | report-consistency의 고아 검출이 성공해도 게시를 막지 못했던 결함이 발견됨(ADR-033) |
| D-036 | 삭제 같은 되돌릴 수 없는 변경의 승인 기록은 "누계 숫자 하나"로 관리하지 않는다. 각 승인을 독립된 불변 이벤트(고유 ID, 날짜, 실재하는 근거 인용, 자기 몫의 파일 목록과 개수)로 남기고, 기존 이벤트는 절대 수정하지 않고 새 이벤트만 추가한다 | 단일 누계 count 방식이 "일관되게 조작하면 자기승인 우회 가능 + 정상적인 2차 삭제는 오히려 실패"라는 양쪽 문제를 동시에 갖고 있음이 재현됨(ADR-034) |
| D-037 | 실제 실행 코드가 있는 산출물은 어떤 Gate가 적용되든 상관없이 `skills/verification-loop/SKILL.md`(빌드·테스트)를 항상 함께 적용한다. 계약 문서만 다루는 경우에만 N/A다 | 결제 API처럼 이미 Gate가 있는 구현이 Verification 없이 Gate만으로 통과할 수 있었던 gap이 발견됨(ADR-034) |
| D-038 | Security 판정에서 "민감 기능인가"와 "외부 연동이 있는가"는 서로 다른 독립된 축이다. 하나가 아니라고 해서 다른 하나의 확인을 건너뛰지 않는다 | 비민감 기능이 외부 연동 확인 자체를 건너뛰는 흐름도 결함이 발견됨(ADR-034) |
| D-039 | 게시 트랜잭션은 "패키지를 안전하게 완성했는가"에서 끝나지 않는다. "그 완성물을 실제로 사용자에게 전달했는가"까지가 게시의 일부다 | 패키지를 완벽하게 만들어놓고 실제 전달 자체를 빠뜨린 실패가 실제로 발생함(ADR-035) |
| D-040 | 신규 스킬에 특정 기술 스택 정책이 필요하면, 스킬 본체(기술 중립적 실행 절차)와 Stack Profile(특정 스택 고정 정책, 프로젝트가 선택적으로 활성화)을 분리한다. 스킬 본체에 특정 라이브러리를 전역 규칙으로 하드코딩하지 않는다 | `ui-ux-design` 스킬 추가 시 PrimeVue/Tailwind 고정 요구가 있었는데, 이를 스킬 본체에 직접 넣으면 "프로젝트 전용 규칙을 전역 스킬로 고정하지 않는다"는 기존 원칙과 충돌함이 확인됨(ADR-036) |
| D-041 | 공통 UI/UX 스킬의 기계적·획일적 결과 방지 검토는 특정 미감·기술 스택을 강제하지 않고, 토큰·계층·반복·장식·문구와 그 선택 근거를 사람이 판정하게 한다 | "AI 티"를 줄이는 목적은 자동 스타일 판정이나 비대칭 강제가 아니라, 사용자 목표와 연결되지 않은 획일성·장식·추상 문구를 검토하는 데 있음(ADR-037) |
| D-042 | 특정 UI 스택의 디자인 구현 규칙은 공통 UI/UX 스킬이 아니라 선택적 Stack Profile에 둔다. Profile은 토큰 연결, 표준 컴포넌트 경계, 스타일 예외와 구현 QA를 소유한다 | 공통 스킬의 기술 중립성을 유지하면서 PrimeVue + Tailwind 프로젝트에서는 토큰 이탈·중복 구현·근거 없는 예외를 막기 위해 필요함(ADR-038) |
| D-043 | Git 저장소를 배포·이력 Source of Truth로 하고, 작업 브랜치 push는 공유 진행 상태, `main` 병합만 공식 반영으로 본다. 루트 에이전트 진입점은 `AGENTS.md` 하나로 표준화하며 기존 단수형 문서는 제거한다. `CLAUDE.md`와 `AGENTS.md`는 자동 검증에서 제외하고 변경 시 수동 검수한다 | ZIP 중심 규칙이 Git-only 운영과 충돌했고, 단수형 파일명은 표준 자동 인식과 맞지 않았다(ADR-039) |

### 하네스 자체 개발 당시 작업 큐(구 §3)

| 우선순위 | 작업 | 상태(당시 기준) |
|---|---|---|
| P1 | 핵심 문서 00~09 작성 | 완료 |
| P1 | 초기 8개 스킬 작성 및 활성 스킬 확장 | 완료 |
| P1 | Gates/Checklists 작성 | 완료 |
| P1 | 최소 검증 스크립트 작성 | 완료 |
| P1 | 감사 리포트 Critical/Major 피드백 반영 | 완료 |
| P2 | 실제 프로젝트에 적용 후 피드백 반영 | 이 시점 기준 대기 — `05.WORKING_CONTEXT.md`를 신규 프로젝트 템플릿으로 전환한 것이 이 작업의 첫걸음 |
| P2 | 체크리스트 사용 결과 누적 | 이 시점 기준 대기 |
| P3 | C등급 후보 스킬 도입 검토 | 이 시점 기준 대기 |

## 2026-09-22 선별 스킬 통합 상태 요약

- 사용자 승인 범위에서 ECC·Brooks·흐름 문서 통합을 로컬 구현했다(ADR-050). 활성 스킬은 이 라운드에서 16→20개다.
- 기존 1층 읽기 표면은 유지하고 별도 설치·자동 Agent/API 평가·Git 쓰기를 추가하지 않았다.
- 프로젝트 부착용 Working Context의 빈 상태는 보존하고 활성 수만 동기화했다.
- 현재 판단 기준은 `reports/_LATEST.md`를 따른다. 상세 검증·미실행 범위는 `reports/2026-09-22_harness-skill-integration_report.md`에 있다.
- 흐름 원본의 라이선스 미고지와 통제된 모델 행동 전후 평가 미실행을 구분해 기록했다. 이번 통합을 실전 준수 개선의 증거로 해석하지 않는다.

## 2026-09-22 흐름 스킬 상세도 보강 상태

- 사용자 피드백에 따라 상세 추출 기준·주체·조건·상태 변화·실패 후 행동·선택 API 계약과 화면 표시를 보강했다.
- overview의 내용 누락은 WARN, detailed의 핵심 누락은 FAIL이다. 보류 hold는 실패와 별도다.
- 하네스 차트는 5개 흐름·45개 단계·18개 시나리오이며 상세 절차 간 연결을 포함한다. 활성 스킬 수는 20개로 유지한다.
- 현재 유지보수 기준은 `reports/2026-09-22_flow-detail-reinforcement_report.md`다. 이전 통합 증거는 archive에 보존했다.
- 로컬 회귀·실제 브라우저 검수 범위만 완료로 보고하며 원격 CI·인쇄·배포는 별도다.

## 2026-09-22 흐름 스킬 UI 생성 기준 후속 보완

- 사용자 요청에 따라 전체·완료·실패 버튼, 결과별 세부 선택, 왼쪽 검색·선택 유지·모바일 진입, 기존 차트 계열 CSS 토큰·레이아웃 기준을 문서화했다.
- SKILL에서 INTERACTION·VISUAL·UI_REVIEW 세 보조 문서로 연결했다. 각 지침은 200줄 이내이며 활성 스킬 수는 20개다.
- 이번에는 문서만 수정했다. 기존 HTML·생성기·CSS의 새 UI 적용은 완료 상태가 아니며 이후 HTML 생성·갱신 작업에서 확인한다.
- 근거와 검수 범위는 `reports/2026-09-22_flow-detail-reinforcement_report.md §9`, 현재 판단 기준은 `reports/_LATEST.md`를 따른다.

## 2026-09-22 상다리 백엔드 차트와 공용 UI 구현

- 공개 저장소 sangdari-backend의 dev 커밋 b7234911136e를 기준으로 API 21개, JWT 필터, 예약 자동 취소를 23개 흐름으로 작성했다.
- 산출물은 220개 단계와 97개 시나리오이며 337개 코드 근거 참조의 파일 누락은 0이다.
- 전체·완료·실패 버튼, 0/1/여러 결과 처리, 왼쪽 검색·분류, 주소 복원, 모바일 탐색을 공용 생성기에 구현했다.
- Node 회귀 107개와 FlowDocument 구조 검증, 320·390·760·1280px 실제 브라우저 검수를 통과했다.
- 이전 UI 지침만 작성된 상태는 구현·검수 PASS로 대체됐다. 현재 판단 기준은 `reports/_LATEST.md`다.

## 2026-09-22 플로우차트 전체 높이 규칙

- 사용자 피드백에 따라 차트 내부 세로 스크롤을 금지하고 SVG 전체 렌더링 높이만큼 펼치는 것을 기본 계약으로 정했다.
- 긴 흐름은 페이지 자체의 세로 스크롤로 읽는다. 차트 영역의 가로 이동은 좁은 화면에서 가독성을 유지할 때만 허용한다.
- 모바일에서도 max-height·고정 높이·overflow-y로 내부 세로 스크롤을 다시 만들지 않는다.
- 이번 작업은 스킬 지침만 변경했다. 공용 CSS와 기존 HTML은 새 규칙 적용 전이며 현재 판단 기준은 `reports/_LATEST.md`다.
