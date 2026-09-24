# Pending Import List

> 목적: 지금 바로 만들지 않고 대기 상태로 둔 항목을 기록한다.  
> 기준: “너무 과하지도, 너무 가볍지도 않은” 중간 강도 하네스를 유지한다.

---

> A/B 등급 항목은 현재 하네스 핵심 문서와 활성 스킬로 반영 완료했다. 이 목록은 C/D/X 등급과 이후 최적화 후보를 관리한다.

## 1. C등급 — 조건부 반입 후보

| 후보 | 참고한 ECC 원본 | 지금 만들지 않는 이유 | 도입 조건 |
|---|---|---|---|
| `skills/tdd-workflow/SKILL.md` | `skills/tdd-workflow/SKILL.md` | 2026-09-22 test-design에 시나리오·실패/통과 증거 원칙만 반영; 전체 TDD 강제는 미반입 | 프로젝트가 테스트 우선 정책과 환경을 확정할 때 전체 흐름 재검토 |
| `skills/db-patterns/SKILL.md` | `skills/mysql-patterns/SKILL.md` 등 | 현재는 `db-gate`와 `erd-checklist`로 충분함 | 특정 DBMS 패턴, 인덱스, 트랜잭션, 성능 이슈가 반복될 때 |
| `skills/database-migrations/SKILL.md` | `skills/database-migrations/SKILL.md` | Flyway/Liquibase 같은 마이그레이션 도구 도입 전에는 과함 | DB 변경 이력 관리가 필요해질 때 |
| `skills/codebase-onboarding/SKILL.md` | `skills/codebase-onboarding/SKILL.md` | 새 레포를 자주 분석하는 단계가 아님 | 프로젝트가 여러 개로 늘어날 때 |
| `skills/production-audit/SKILL.md` | `skills/production-audit/SKILL.md` | 매일 쓰기엔 무거움 | 현재 릴리즈/다음 릴리즈 제출 직전 점검 단계 |
| `skills/documentation-lookup/SKILL.md` | `skills/documentation-lookup/SKILL.md` | 2026-09-22 조건부 활성 스킬로 승격(ADR-050) | 완료. 버전 불확실성에만 발동 |
| `skills/research-ops/SKILL.md` | `skills/research-ops/SKILL.md` | 모든 작업에 붙이면 느림 | 기술 선정/레퍼런스 비교 작업이 많아질 때 |

---

## 2. D등급 — 장기 보류

| 항목 | 참고한 ECC 원본 | 보류 이유 | 나중에 가능해지는 조건 |
|---|---|---|---|
| Agent 전체 구조 | `AGENTS.md` | 대규모 Agent 운영 전제라 현재보다 무거움 | 역할이 3~5개 이상으로 분리될 때 |
| Command Registry 전체 | `docs/COMMAND-REGISTRY.json` | 명령 카탈로그 유지 비용이 큼 | 명령 자동화가 10개 이상 필요할 때 |
| MCP Connector 정책 전체 | `docs/MCP-CONNECTOR-POLICY.md` | 외부 도구 연결 보안 검토가 필요함 | 승인 도구 목록과 사용 정책이 생길 때 |
| hooks 자동 차단 전체 | `scripts/hooks/quality-gate.js` | 오작동 시 작업이 막힐 수 있음 | 수동 스크립트가 안정화된 뒤 |
| Browser QA 전체 | `skills/browser-qa/SKILL.md` | **2026-08-02 정식 스킬로 승격 완료(ADR-042)** — 실사용 Report 10건 중 5회 반복 + 자동화 도구 사용을 사용자가 확인해 도입 조건이 충족됨 | 승격됨. 현재 스킬은 `skills/browser-qa/SKILL.md` 참조 |
| E2E Testing 전체 | `skills/e2e-testing/SKILL.md` | 테스트 계정/데이터/환경 관리 필요 | 핵심 사용자 플로우가 안정화된 뒤 |
| 실행자 분기 구조(`00.EXECUTOR_BOOT.md` 등) | `harness_import_candidates_20260704/executor_routing_documents_draft.md` | 루트 `AGENTS.md`는 최소 진입 지도로 채택했고 `CLAUDE.md`는 보조 안내로 유지한다. 별도 부트 문서 다수·제품별 분기 구조는 여전히 무겁다. | 여러 실행자 역할이 3~5개 이상으로 분리되고, 단일 진입 지도만으로 Handoff가 반복 실패할 때 |
| Understand-Anything 전체(대시보드, 멀티에이전트 파이프라인) | `Understand-Anything-main.zip`(원본 저장소 실사 완료) | React 대시보드+멀티에이전트 파이프라인이 있는 완제품 모노레포. `docs/superpowers/specs`·`plans`의 계획 패턴만 `skills/planning/SKILL.md`로 재작성 반입함(`10.ADR.md` ADR-017) | 실제 프로젝트에 하네스를 부착하고 코드베이스가 커져 시각적 온보딩이 필요해졌을 때 |
| codebase-memory-mcp 전체(C 엔진, MCP 서버) | `codebase-memory-mcp-main.zip`(원본 저장소 실사 완료) | tree-sitter+LSP 기반 네이티브 바이너리, `curl \| bash` 설치. `check-no-test-skips.sh` 원칙만 `verification-loop`에 재작성 반입함(`10.ADR.md` ADR-017) | 코드베이스 규모가 커져 검색/그래프 도구가 실제로 필요해질 때 |
| codebase-memory-mcp의 `detect_changes`(Git diff → 영향받는 심볼 매핑 + 위험도 분류) | `codebase-memory-mcp-main.zip` | 실제 코드 심볼 그래프가 있어야 가능한 기능이라 규칙 문서만으로 흉내 낼 수 없음 | codebase-memory-mcp 자체를 도입하기로 결정하는 시점에 함께 재검토 |
| RAG 파이프라인(벡터 검색 기반 문서 조회) | 대화 중 논의(외부 저장소 없음) | 현재 하네스 문서 규모(약 1만 단어대)에서는 `03.CONTEXT_BUDGET.md`의 규모별 읽기 규칙으로 충분함. 벡터 DB/임베딩 API 도입은 외부 설치·특정 스택 종속 문제와 충돌 | 실제 프로젝트 코드베이스가 커지고, Claude/Codex 내장 검색으로 부족해졌을 때 |
| 세션 내 반복 읽기 압축 도구(예: sqz류, `curl \| sh` 설치형 Rust 바이너리) | 대화 중 논의(외부 저장소 없음) | 검증되지 않은 단일 관리자 배포 바이너리가 전체 입출력(코드/명령 결과/로그)을 가로채는 신뢰 범위 문제, 외부 설치 스크립트 원칙(`00.HARNESS_RULES.md §7`)과 충돌. 대신 "중복 읽기 방지 원칙"만 `03.CONTEXT_BUDGET.md §4-1`에 규칙으로 반영함(설치 없이) | 검토하지 않음(원칙만 문서화, 도구 자체는 대상 아님) |

---

## 3. X등급 — 현재 구조와 충돌 가능

| 항목 | 제외 이유 |
|---|---|
| 특정 ORM 전용 스킬 | 일반 하네스에 바로 넣으면 특정 기술 스택으로 오해될 수 있음 |
| `skills/backend-patterns/SKILL.md` 원본 전체 | 특정 백엔드 스택 기준을 전역 규칙으로 오해할 수 있음 |
| `skills/frontend-patterns/SKILL.md` 원본 전체 | 특정 프론트엔드 스택 기준을 전역 규칙으로 오해할 수 있음. **`ui-ux-design` 스킬(정식 반입됨)과의 차이**: 그 스킬 본체는 기술 중립적 실행 절차만 갖고, PrimeVue/Tailwind 같은 특정 스택 고정 정책은 `skills/ui-ux-design/STACK_PROFILE_PRIMEVUE_TAILWIND.md`라는 별도 파일로 분리해 프로젝트가 선택적으로 활성화하는 구조라 이 제외 사유에 해당하지 않는다. **`vue-ui-polish`(정식 반입됨)와의 차이**: 스택 한정 스킬 범주(`01.SKILL_TEMPLATE.md §2-2`, ADR-043)로, Harness Control Rule에 "Vue 3 외 프로젝트에서는 존재 무시"를 선언해 전역 오해 경로를 스킬이 스스로 차단하므로 이 제외 사유에 해당하지 않는다 |
| 설치 스크립트 전체 | 공급망/환경 리스크 검토 전에는 반입하지 않음 |
| MCP 설정 파일 | 외부 도구 연결 정책이 먼저 필요함 |

---

## 4. 다음에 만들면 좋은 순서

1. 실제 프로젝트에 현재 하네스를 1회 적용한다.
2. WARN/FAIL이 자주 나오는 영역을 기록한다.
3. 반복되는 영역만 새 스킬로 승격한다.
4. `02.SKILL_INDEX.md`와 `05.WORKING_CONTEXT.md`를 갱신한다.
5. 자동화 가능한 항목만 scripts에 추가한다.

---

## 5. 프로젝트 전용 후보 처리 규칙

일반 하네스에는 특정 기술 스택을 기본값으로 고정하지 않는다.

| 구분 | 처리 |
|---|---|
| 특정 DBMS, ORM, 프레임워크 | 전역 문서에서는 예시로만 표기 |
| 프로젝트에서 반복되는 기술 패턴 | 프로젝트별 확장 하네스 또는 별도 스킬 후보로 관리 |
| 전역으로 승격할 기준 | 기술명이 아니라 문제 유형이 여러 프로젝트에서 반복될 때 |


## 6. 저비용 의미 검증 상태

아래 항목은 새 스킬을 만들 정도로 크지는 않지만, 반복 누락을 막기 위해 scripts 확장 대상으로 관리한다.

### 6-1. 반영 완료

| 항목 | 적용 대상 | 상태 |
|---|---|---|
| `Harness Control Rule` 섹션 검사 | `scripts/validate-skills.mjs` | 기초 구현 완료 |
| Handoff 대상 존재 검사 | `scripts/validate-skills.mjs` | canonical code span 대상 존재 검사 기초 구현 완료 |
| H2 번호 중복 검사 | `scripts/validate-docs.mjs` | 기초 구현 완료 |
| 안정 패키지명 검사 | `scripts/validate-package.mjs` | 기초 구현 완료 |
| 런타임 Quick Ref | `00.QUICK_REF.md`, `03.CONTEXT_BUDGET.md` | 토큰 절감용 런타임 요약 레이어 반영 완료 |
| ZIP 내부 구조 검사(단일 루트/경로탈출/중복/필수파일/parity/파일별 SHA-256) | `scripts/validate-package.mjs` | 순수 Node ZIP 리더로 재작성해 `unzip` 외부 의존 없이 완전 구현(ADR-028, 근거 Report는 `reports/archive/` 참고) |
| 시크릿·민감 파일 추적 검사 | `scripts/validate-no-secrets.mjs`, CI(`harness-ci`) | 실제 유출 사고 2건을 근거로 구현 완료, CI 강제 실행(ADR-044) |
| Report 헤더 성적표 집계(스킬 발동률·미등록 스킬명·Git 기록·반복 미해결) | `scripts/harness-stats.mjs` | 챱챱 수동 전수 분석(2026-08-02)을 자동화. 통계 전용, CI 차단 미사용. 사용법은 `reports/README.md §4` |

### 6-2. 부분 반영

| 항목 | 적용 대상 | 남은 범위 |
|---|---|---|
| Handoff 검증 | `skills/*/SKILL.md` | 문맥 적합성, 조건부 Handoff, 별칭 해석은 수동/Gate 검수 유지 |
| Report 최신성 관리 | `reports/*.md`, `05.WORKING_CONTEXT.md` | superseded 표기는 문서 규칙으로 반영, 자동 동기화 검사는 `skills/report-consistency/SKILL.md`, `scripts/validate-report-consistency.mjs`로 반영 완료 |

### 6-3. 후보

| 후보 | 적용 대상 | 도입 조건 |
|---|---|---|
| 체크리스트 위험 WARN 문구 검사 | `validate-docs.mjs` 또는 별도 script | 결제/DB/릴리즈 체크리스트 수정이 반복될 때 |
| 전역 중립 표현 검사 | 문서 전체 | 특정 스택/프로젝트 단계 표현이 반복될 때 |
| ADR 번호 중복 검사(`validate-adr-unique.mjs`) | `10.ADR.md` | **현재 36개로 재검토 기준선(30개)을 이미 넘었다.** 다음 하네스 자체 수정 라운드에서 이 스크립트 도입 여부를 실제로 판단한다 |
| Handoff 문맥 적합성 검사 | `skills/*/SKILL.md` | 스킬 수가 늘어나고 Handoff 오판이 반복될 때 |
| `project-bootstrap` 스킬 | 신규 스킬 | 실제 프로젝트에 하네스를 처음 부착하는 시점(`09.AGENT_WORKFLOW.md §7-2` 절차를 스킬로 승격하는 형태로 검토) |
| `harness-maintenance` 스킬 | 신규 스킬 | 하네스 유지보수(스킬/Gate/스크립트 추가)가 반복되어 영향 문서 목록을 매번 사람이 챙기기 어려워질 때 |
| `document-audit` 스킬 | 신규 스킬 | 범용 문서 검수를 반복적으로 요청받게 될 때. 단, `quality-gate`/`document-gate`와 중복 여부를 `skill-scout` 기준으로 먼저 확인 |


---

## 7. 토큰 절감 후보 상태

| 후보 | 상태 | 이유 |
|---|---|---|
| `05.WORKING_CONTEXT.md` / `05.WORKING_RULES.md` 분리 | 보류 | 현재는 Working Context가 자주 갱신되는 단계라 파일 분리 시 유지 비용이 증가할 수 있음. 실제 프로젝트 적용 후 상태 기록 형식이 안정되면 재검토 |

---

## 8. 2026-07-10 외부 검수 리포트(1차) — 처리 완료

`GENERAL_HARNESS_논리구조_검수_리포트_2026-07-10.md`(Critical 5·Major 16·Minor 9·충돌 10·중복 6·누락 9, 총 55개 항목)를 6라운드로 나누기로 합의함. **1~6라운드 전부 완료**(`10.ADR.md` ADR-021~ADR-023). 55개 항목 전체 반영 완료.

| 라운드 | 항목 | 상태 |
|---|---|---|
| 1 | C-01, C-02 | 완료 |
| 2 | C-03~C-05, M-01, M-02, M-16 | 완료 |
| 3 | M-03~M-06, P1-1, P1-3 | 완료 |
| 4 | M-07, M-08, m-04, m-05 | 완료 |
| 5 | M-09~M-13, M-15 | 완료 |
| 6 | m-01~m-03, m-06~m-09, M-14 | 완료 |

원본 검수 리포트는 `/mnt/user-data/uploads/GENERAL_HARNESS_논리구조_검수_리포트_2026-07-10.md`로 제공받았으며, 패키지 내부에는 포함하지 않는다(원문 미보존 — 근거는 `_SOURCE_MAPPING.md`).

## 9. 2026-09-22 선별 통합 후 보류

| 후보 | 현재 대안 | 재검토 조건 |
|---|---|---|
| 독립 search-first | 최소 해법 참조에 탐색 근거 흡수 | 별도 독립 작업이 입증될 때 |
| 독립 skill-comply/eval-harness | skill-stocktake 행동 평가 참조 | 평가 운영 규모가 보조 문서 범위를 넘을 때 |
| Brooks audit/debt/health | code-review로 변경 범위 검수 | 전체 아키텍처·부채 진단 수요가 반복될 때 |
| Brooks sweep와 자체 관리 스킬 | 승인된 수정 후 기존 검증/복구 사용 | 일괄 자동 수정 필요성과 제한·검증이 별도로 확정될 때 |
| contract-consistency | planning 영향 범위 + verification-loop 계약 대조 | 여러 제공자·소비자 사이 불일치 조사가 반복될 때 |

documentation-lookup/test-design/code-review/universal-flow-document는 ADR-050으로 반영했다. 사용자 제공 흐름 자료의 별도 라이선스 고지 문구는 2026-09-22 사용자 지시에 따라 추가하지 않는다.
