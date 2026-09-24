# History Digest

> 목적: `reports/archive/`에 있던 과거 Report의 핵심 결정과 변경 내역을 날짜순으로 압축한 색인이다.
> **2026-07-12부로 원본 삭제 정책으로 전환했다(사용자 결정, ADR-031).** 아래 표에 있는 각 항목 중 "삭제 이벤트"에 파일명이 명시된 것은 **원본이 삭제되어 이 요약이 유일한 기록**이다.
> 새 Report가 archive로 이동하면 그 즉시 이 표에 한 줄 추가한다. 원본 파일을 보관할지 삭제할지는 그때그때 판단하고, 삭제하면 아래 "삭제 이벤트"에 **새 이벤트 블록을 추가**한다 — 기존 이벤트 블록의 숫자·목록은 절대 고치지 않는다(외부 검수 M-06/X-06/G-06).

## 삭제 이벤트

**각 삭제는 독립된 이벤트 블록이다.** 이벤트가 여러 번 있으면 블록을 여러 개 나열한다(기존 블록 수정 금지, 새 블록만 추가). 각 블록은 `event_id`(고유해야 함), `date`, `approval`(실제로 `10.ADR.md`에 있는 ADR 번호여야 함), `count`(그 이벤트에서 지운 파일 개수, 아래 목록 줄 수와 일치해야 함)를 헤더에 명시한다.

`scripts/validate-report-consistency.mjs`는 모든 이벤트 블록을 각각 독립적으로 검증한다: `event_id` 전체 고유, `approval`이 실제 존재하는 ADR인지, `count`가 그 블록 파일 목록 줄 수와 일치하는지, 그 블록의 파일 전부가 digest 표 행에 실제로 있는지, 그 블록의 파일이 현재 archive에 실제로 없는지. 모든 이벤트의 파일을 합친 것과 digest 표·현재 archive를 최종 대조해 설명 안 된 고아가 있는지도 확인한다.

<!-- PURGE_EVENT event_id=PURGE-2026-07-12-01 date=2026-07-12 approval=ADR-031 count=30 -->
```text
2026-06-24_harness-v0.2-audit-fix_report.md
2026-06-25_harness-v0.2.1-stabilization_report.md
2026-06-25_harness-v0.2.2-maintenance_report.md
2026-06-25_harness-stable-package-maintenance_report.md
2026-06-25_harness-stable-package-consistency_report.md
2026-06-25_harness-runtime-slim-patch_report.md
2026-06-25_harness-runtime-slim-minor-fix_report.md
2026-06-25_harness-runtime-slim-final-alignment_report.md
2026-07-04_harness-import-candidate-blend_report.md
2026-07-05_harness-logical-structure-fix_report.md
2026-07-05_0046_harness-minor-followup-fix_report.md
2026-07-05_0100_harness-mixed-agent-alignment_report.md
2026-07-09_harness-rename-and-batch-import-v1_report.md
2026-07-09_harness-planning-skill-naming-fix_report.md
2026-07-09_harness-feedback-full-adoption-v1_report.md
2026-07-09_harness-mistake-pattern-promotion-v1_report.md
2026-07-09_harness-compression-cleanup-v1_report.md
2026-07-09_harness-history-wording-fix_report.md
2026-07-09_harness-history-digest-autocheck-v1_report.md
2026-07-09_harness-working-context-catchup-v1_report.md
2026-07-10_harness-external-review-round1-2_report.md
2026-07-10_harness-external-review-round3-4_report.md
2026-07-10_harness-external-review-round5-6_report.md
2026-07-10_harness-external-review-round7-c01-fix_report.md
2026-07-10_harness-external-review-round8-major-minor_report.md
2026-07-10_harness-external-review-round9-final-decisions_report.md
2026-07-11_harness-external-review-critical-and-decisions_report.md
2026-07-11_harness-external-review-major-minor_report.md
2026-07-11_harness-external-review-reaudit_report.md
2026-07-12_harness-external-review_report.md
```
<!-- PURGE_EVENT_END event_id=PURGE-2026-07-12-01 -->

이 이벤트 이후 새 삭제가 생기면, 위 블록은 그대로 두고 새 `PURGE_EVENT` 블록을 이 자리 아래에 추가한다. 어떤 이벤트에도 속하지 않는 archive 참조는 원본이 실제로 존재해야 한다 — 없으면 설명 안 된 고아로 FAIL이다.


| 날짜 | 원본 파일 | 핵심 내용 |
|---|---|---|
| 2026-06-24 | `2026-06-24_harness-v0.2-audit-fix_report.md` | 최초 감사 피드백 반영, v0.2 핵심 보강(충돌 우선순위, 위험 WARN 중단, 재개 규칙) |
| 2026-06-25 | `2026-06-25_harness-v0.2.1-stabilization_report.md` | Harness Control Rule 필수 검증 도입, 사전/사후 Gate 구분 |
| 2026-06-25 | `2026-06-25_harness-v0.2.2-maintenance_report.md` | ADR 번호 고유성 규칙 추가, 최신 Report 우선 원칙 정립 |
| 2026-06-25 | `2026-06-25_harness-stable-package-maintenance_report.md` | 배포 파일명/루트 폴더명 고정, Handoff canonical 표기 정리 |
| 2026-06-25 | `2026-06-25_harness-stable-package-consistency_report.md` | 안정 배포명 정합성 점검 |
| 2026-06-25 | `2026-06-25_harness-runtime-slim-patch_report.md` | 일반 작업 런타임 진입점으로 `00.QUICK_REF.md` 도입 |
| 2026-06-25 | `2026-06-25_harness-runtime-slim-minor-fix_report.md` | Runtime Slim Patch 후속 가시성 문제 보정 |
| 2026-06-25 | `2026-06-25_harness-runtime-slim-final-alignment_report.md` | Quick Ref 우선 로딩, 재개 규칙 소유권 정리로 Runtime Slim 계열 마무리 |
| 2026-07-04 | `2026-07-04_harness-import-candidate-blend_report.md` | `verification-loop`, `agent-recovery` 스킬 신설(8→10개), API Candidate/Confirmed 상태 도입, 스킬 대분류(문서/코드/운영) 도입 |
| 2026-07-05 | `2026-07-05_harness-logical-structure-fix_report.md` | WARN 3분류(일반/구조/위험) 확정, 작업 계약 필드 통일, API 상태 Deprecated까지 확장 |
| 2026-07-05 | `2026-07-05_0046_harness-minor-followup-fix_report.md` | Working Context 자기모순 문장, Report Template 표 깨짐 등 Minor 수정 |
| 2026-07-05 | `2026-07-05_0100_harness-mixed-agent-alignment_report.md` | Claude/Codex 혼합 운영 최소 역할 분기(`03 §2-3`, `09 §1-1`) 도입, SRS 원본/추출본 우선순위 확정 |
| 2026-07-09 | `2026-07-09_harness-rename-and-batch-import-v1_report.md` | `GLOBAL_AI_HARNESS` → `GENERAL_HARNESS` 이름 변경, `planning` 스킬 신설, SKIP=FAIL 원칙, 개인경로 검사 스크립트 도입(10→11개 스킬) |
| 2026-07-09 | `2026-07-09_harness-planning-skill-naming-fix_report.md` | `planning` 스킬명과 "Planning Agent" 역할명 혼동, 연결 다이어그램 부정확성 수정 |
| 2026-07-09 | `2026-07-09_harness-feedback-full-adoption-v1_report.md` | 외부 피드백 전면 수용: `report-consistency` 스킬·검증 스크립트 2종 신설(11→12개 스킬, 5→7개 스크립트), top-level Report 정리 |
| 2026-07-09 | `2026-07-09_harness-mistake-pattern-promotion-v1_report.md` | Report 기록에서 2회 이상 반복 확인된 실수 패턴 5건을 `04.GATEGUARD.md §11` 금지 패턴으로 승격 |
| 2026-07-09 | `2026-07-09_harness-compression-cleanup-v1_report.md` | 우선순위 표/PASS·WARN·FAIL 완전 중복 제거, 이 색인 파일 신설, `_WORKING_CONTEXT_HISTORY.md` 신설, `04.GATEGUARD.md §11` 소분류 |
| 2026-07-09 | `2026-07-09_harness-history-wording-fix_report.md` | `_WORKING_CONTEXT_HISTORY.md`의 "(당시 기준)" 표기 누락, `05.WORKING_CONTEXT.md` 서식(연속 빈 줄) 수정 |
| 2026-07-09 | `2026-07-09_harness-history-digest-autocheck-v1_report.md` | `HISTORY_DIGEST.md` 색인 누락분 수정, `validate-report-consistency.mjs`에 archive 색인 완전성 자동 검사 추가(회귀 테스트로 동작 확인) |
| 2026-07-09 | `2026-07-09_harness-working-context-catchup-v1_report.md` | `05.WORKING_CONTEXT.md` 최신 요약이 3라운드 뒤처진 문제 수정, "자기 참조 색인/요약 갱신 누락" 패턴을 일반화해 `04.GATEGUARD.md §11-3`에 승격(ADR-020) |
| 2026-07-10 | `2026-07-10_harness-external-review-round1-2_report.md` | 외부 검수 리포트 1~2라운드: FAIL 해제조건 단일화, `04.GATEGUARD.md §6-1` 위험유형별 해제조건 SoT 신설, API/DB/보안/결제/릴리즈/스킬 Gate의 필수항목-판정 불일치 수정(ADR-021) |
| 2026-07-10 | `2026-07-10_harness-external-review-round3-4_report.md` | 외부 검수 리포트 3~4라운드: superseded 템플릿을 `_LATEST.md` 참조로 변경(M-04 근본원인), Report 완료 트랜잭션 9단계 신설, 검증 스크립트 3종 로직 강화(ADR-022) |
| 2026-07-10 | `2026-07-10_harness-external-review-round5-6_report.md` | 외부 검수 리포트 5~6라운드: Skill 라우팅/Output Format/Workflow 정합성(M-09~M-15), Minor 전부, Source Mapping provenance 신설 — 55개 항목 전체 완료 주장(이후 두 번째 검수에서 일부 갱신 누락 발견됨, ADR-023) |
| 2026-07-10 | `2026-07-10_harness-external-review-round7-c01-fix_report.md` | 두 번째 외부 검수 C-01(Report 게시 순서 결함) 수정: 검증 전 게시하던 §8-2를 게시 전 검증으로 재구성, 롤백 규칙 추가, Pending/Source Mapping 갱신 누락 수정(ADR-024) |
| 2026-07-10 | `2026-07-10_harness-external-review-round8-major-minor_report.md` | 두 번째 검수 Major 10건+Minor 6건 전체: Gate/Checklist 필수-판정 불일치 다수 수정, validate-package fail-open 제거, validate-references 섹션검사 추가(ADR-025) |
| 2026-07-10 | `2026-07-10_harness-external-review-round9-final-decisions_report.md` | 두 번째 검수 §12 사용자 확인 5건 최종 결정: 환경변경(비파괴적) 범주 분리 적용, 외부근거 provenance·Checklist 엄격도는 현행 유지(ADR-026) |
| 2026-07-11 | `2026-07-11_harness-external-review-critical-and-decisions_report.md` | 세 번째 검수 Critical 3건(ZIP 내용해시 비교, Report 게시-전-검증 재설계, 복합Gate 최악판정) + 사용자 결정 5건(배포SoT=ZIP, 최종검증은 채팅기록, 결제 복합Gate, 외부근거 비보존, WORKING_CONTEXT 신규템플릿 전환) 반영(ADR-027) |
| 2026-07-11 | `2026-07-11_harness-external-review-major-minor_report.md` | 세 번째 검수 Major 15건 + Minor 11건 전체: API/DB/Security/Payment Gate 필수-판정 재정리, 12개 스킬 HCR 중단문구 일괄반영, WORKING_CONTEXT_HISTORY 중복섹션 제거 |
| 2026-07-11 | `2026-07-11_harness-external-review-reaudit_report.md` | 네 번째 검수(재검수) Critical 5건: validate-package.mjs를 순수 Node ZIP 파서로 전면 재작성(unzip 의존 제거), 게시 원자적 교체, 결제 복합Gate 매트릭스 SoT 확정, 대량이동 분류 통일(ADR-028) |
| 2026-07-12 | `2026-07-12_harness-external-review_report.md` | 다섯 번째 검수 Critical 4건: --zip 인자 추가로 후보 실제검증, Report 게시상태 필드 자체 제거(외부신호로 판단), 복합Gate 하드코딩 제거·quality-gate 집계 단일화, 결제 위험WARN을 AND조건으로 통일(ADR-029) |
| 2026-07-12 | `2026-07-12_harness-deployment-model-decision_report.md` | §12 결정: 배포 모델을 템플릿 복제로 확정. GENERAL_HARNESS.zip은 원본 템플릿 전용, 프로젝트 부착 시 각자 사본으로 관리(ADR-030) |
| 2026-07-12 | `2026-07-12_harness-archive-purge-decision_report.md` | §12 마지막 결정: archive Report 30개 원본 삭제, HISTORY_DIGEST만 유지. 삭제 로그 신설, 관련 참조 3건 수정(ADR-031) |
| 2026-07-12 | `2026-07-12_harness-orphan-check-explicit-list-fix_report.md` | 고아 행 검사의 날짜 cutoff 결함을 명시적 파일 목록(PURGED_FILES) 방식으로 근본 수정(ADR-032, 이후 목록 자체의 무결성 검사가 ADR-033에서 추가로 강화됨) |
| 2026-07-12 | `2026-07-12_harness-external-review-round2-major-fixes_report.md` | 여섯 번째 검수(재검수) Major 10건+Minor 5건: 게시 WARN 차단, project §8-3 신설, Gate fan-out, 전역 최종판정 공식, 43/44 정정 기록(ADR-033) |
| 2026-07-13 | `2026-07-13_harness-external-review-purge-event-model_report.md` | 일곱 번째 검수(재검수) Major 9건+Minor 5건: 삭제를 event 기반 모델로 재설계(자기승인 우회 차단, 다중삭제 지원), 나머지 잔여 정합화(ADR-034) |
| 2026-07-13 | `2026-07-13_harness-self-audit-terminology-fix_report.md` | Claude 자체 검수 1회차: §7-1의 "최종 판정" 용어를 "Checklist 판정"으로 통일(m-01) |
| 2026-07-13 | `2026-07-13_harness-self-audit-round2-gateguard-summary-fix_report.md` | Claude 자체 검수 2회차: `04.GATEGUARD.md §8` 요약표에 누락됐던 "외부 설치"·"환경 변경" 행 2개 추가 |
| 2026-07-13 | `2026-07-13_harness-self-audit-round3-terminology-consistency_report.md` | Claude 자체 검수 3회차: ADR-034(삭제 이벤트 모델)를 발표한 문서 자신이 옛 용어("삭제 로그")를 남겨뒀던 것을 "삭제 이벤트"로 통일(단, 이후 4회차에서 이 통일이 불완전했음이 드러남) |
| 2026-07-13 | `2026-07-13_harness-self-audit-round4-terminology-final-sweep_report.md` | Claude 자체 검수 4회차: "삭제 로그"/"PURGED_FILES"(구용어) 전수 grep으로 활성 문서 4곳 추가 발견·정리(3회차 spot-check의 불완전함을 보강) |
| 2026-07-13 | `2026-07-13_harness-self-audit-round5-actual-delivery-step_report.md` | Claude 자체 검수 5회차: 실제 전달 누락 사고를 계기로 `06.REPORT_TEMPLATE.md §8-2`에 7-1번(실제 전달) 단계 신설(ADR-035) |
| 2026-07-13 | `2026-07-13_harness-self-audit-round6-delivery-failure-handling-final_report.md` | Claude 자체 검수 6회차(최종): 7-1 자체가 실패/생략될 경우의 처리(8-1번) 추가. 자체 검수 루프 종료 |
| 2026-07-15 | `2026-07-15_harness-ui-ux-design-skill-addition_report.md` | `ui-ux-design` 스킬(13번째)·ui-ux-gate·ui-ux-checklist 신설, 스킬 본체와 Stack Profile 분리(ADR-036) |
| 2026-07-21 | `2026-07-21_harness-git-first-agents-standardization_report.md` | Git-first 공식 반영 정책 확정, 루트 진입점 `AGENTS.md` 표준화(ADR-039) |
| 2026-07-21 | `2026-07-21_harness-ui-ux-ai-pattern-guard_report.md` | `ui-ux-design`에 기계적·획일적 결과 방지 검토 추가(ADR-037), Stack Profile 구현 경계 보강(ADR-038) |
| 2026-08-02 | `2026-08-02_harness-usage-audit-fixes-and-i2i-import_report.md` | 실사용 검수 15건 반영(Report Git 이력란·프로젝트 상수·구조 정리), `intent-to-implementation` 축소 반입(ADR-040), `browser-qa` 승격(ADR-042), `_LATEST` 2행 환류 구조(ADR-041). 활성 스킬 15개 |
| 2026-08-03 | `2026-08-03_harness-vue-ui-polish-import_report.md` | `vue-ui-polish` 스택 한정 스킬 반입(ADR-043, 스택 한정 범주·MIT LICENSE 첫 반입). 활성 스킬 16개 |
| 2026-08-03 | `2026-08-03_0045_harness-enforcement-layer_report.md` | 집행층 도입(ADR-044): CI harness-ci(검증 7종 강제), validate-no-secrets 신설, main 브랜치 보호, PR 템플릿, 2층 읽기 표면(03.CONTEXT_BUDGET §2-2-1) |
| 2026-08-03 | `2026-08-03_0153_harness-stats-script_report.md` | 성적표 집계 스크립트 harness-stats.mjs 추가(스킬 발동률·미등록 스킬명·Git 기록·반복 미해결 자동 집계), 하네스 동결 선언 |
| 2026-08-04 | `2026-08-04_harness-vue-ui-polish-revision_report.md` | vue-ui-polish 개정 교체·보조 스크립트 도입(ADR-045). 당시 활성 16개, 동결 예외의 역사 근거. 2026-09-22 유지보수 포인터 전환으로 archive 보존 |

| 2026-09-22 | `2026-09-22_harness-skill-integration_report.md` | ECC·Brooks·흐름 스킬 선별 통합과 초기 하네스 차트. 당시 회귀 98개·활성 20개. 상세도 보강으로 superseded, 원본 증거 archive 보존 |
| 2026-09-22 | `2026-09-22_flow-detail-reinforcement_report.md` | 상세 FlowDocument 계약과 하네스 차트 보강, 이어서 결과 버튼·검색 UI 지침 작성. 상다리 차트 작업에서 공용 생성기 구현·브라우저 검수까지 완료되어 superseded, 원본 증거 archive 보존 |
| 2026-09-22 | `2026-09-22_1505_sangdari-backend-flow_report.md` | 상다리 백엔드 23개 흐름·220개 단계·97개 시나리오와 공용 결과 탐색 UI 구현·브라우저 검수. 이후 차트 내부 세로 스크롤 금지 규칙이 추가되어 당시 UI PASS는 과거 기준이 됐고 원본 증거를 archive에 보존 |

## 이후에도 참고할 만한 핵심 결정 (요약)

- **이름**: `GENERAL_HARNESS`(영문 고정, 한국어로는 "일반 하네스")
- **스킬 수 흐름**: 8개(최초) → 10개(Import Candidate Blend) → 11개(Rename+Batch Import) → 12개(외부 피드백 수용) → 13개(`ui-ux-design` 신규 추가)
- **자동화 스크립트 흐름**: 4개(최초) → 5개(Rename+Batch Import) → 7개(외부 피드백 수용)
- **WARN 분류**: 일반/구조/위험 3분류로 확정(`08.QUALITY_GATE.md §3`가 소유)
- **API 상태**: Candidate/Confirmed/Deprecated 3단계(`gates/api-gate.md`가 소유)
- **혼합 운영**: Claude/Codex 역할 분기는 별도 Executor Boot 문서 없이 `03.CONTEXT_BUDGET.md §2-3`, `09.AGENT_WORKFLOW.md §1-1`에서 최소한으로 처리

이 요약은 `05.WORKING_CONTEXT.md`의 현재 상태 표, `_WORKING_CONTEXT_HISTORY.md`의 라운드별 상세 서술과 함께 본다.
