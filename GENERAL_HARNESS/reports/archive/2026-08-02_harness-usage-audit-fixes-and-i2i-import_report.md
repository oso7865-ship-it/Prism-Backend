# 작업 리포트: 실사용 검수 반영 및 intent-to-implementation 반입

> Superseded note:  
> 이 보고서의 다음 작업 판단은 `reports/_LATEST.md`가 가리키는 최신 Report로 대체되었다.  
> 과거 의사결정 근거로는 유효하지만, 현재 Next Work 판단은 최신 Report와 `05.WORKING_CONTEXT.md`를 우선한다.

> 작성일: 2026-08-02  
> 패키징/배포일: 해당 없음  
> 작업 브랜치: `harness-audit-260802`  
> 커밋/PR: `594362c`(본 작업 — 민감 원본 제외를 위해 이력 재작성, 2026-08-03), 헤더 갱신 후속 커밋 1건 / PR #3  
> 작업 범위: L  
> 적용 스킬: `skill-scout`, `skill-stocktake`, `planning`, `git-workflow`, `verification-loop`, `report-consistency`  
> 적용 Gate: `gates/skill-gate.md`, `gates/document-gate.md`  
> 위험도: 구조  
> 위험 작업 여부: 예(스킬 추가·문서 구조 변경 — 사용자의 명시 요청 "수정작업 시작해줘"가 근거)

---

## 0. 작업 범위 확인

| 항목 | 내용 |
|---|---|
| 요청 요약 | `HARNESS_문제점_종합정리_2026-08-02.md`의 문제를 해결하고 `intent-to-implementation`을 하네스에 맞게 반입한다. 해결 방법 설계는 에이전트에게 위임됨 |
| 수정 대상 | `06.REPORT_TEMPLATE.md`, `05.WORKING_CONTEXT.md`, `02.SKILL_INDEX.md`, `01.SKILL_TEMPLATE.md`, `10.ADR.md`, `_SOURCE_MAPPING.md`, `reports/_LATEST.md`, `scripts/validate-report-consistency.mjs`, 루트 `CLAUDE.md`, 신규 `skills/intent-to-implementation/`(5개 파일) |
| 제외 대상 | 챱챱 프로젝트 폴더의 Report 2건 정정 주석(A-3)·프로젝트 상수 기입(C-1) — 이 저장소 밖. "Browser" 정체 확정(Phase B) — 사용자 확인 필요. `vue-ui-polish` 반입(Phase F) — 원본 zip 미제공 |
| 근거 | 근거 문서 P-01~P-19 및 §5 실행 순서. 구조 작업 승인 근거는 사용자의 최신 명시 요청 |
| 적용 스킬/Gate | 헤더와 동일 |
| 위험도 | 구조 |
| 검증 방법 | `scripts/validate-harness.mjs`를 포함한 검증 스크립트 6종(docs, skills, references, report-consistency, no-personal-paths, harness) 전체 실행 + skill-gate 수동 판정 |
| 한계 | 챱챱 실사용 Report 원본은 이 저장소에 없어 재검증 불가(분석 문서 경유). i2i 원저작 여부 미확인 |

## 1. 작업 요약

- **Phase A(기록 신뢰성)**: Report 템플릿 헤더에 작업 브랜치·커밋/PR 칸 추가, §5-1 Git 이력 기록 규칙 신설(P-01/P-02 재발 차단). `02.SKILL_INDEX.md §4`에 "파일 이동·폴더 구조 변경→git-workflow", "XL/L 구조 작업 전→planning" 행 추가(P-05/P-09).
- **Phase C(WARN 피로)**: `05.WORKING_CONTEXT.md §1-1` 프로젝트 상수 표 신설, 템플릿 §5-2(상수 반복 기재 금지)·§5-3(후속 작업 누적 처리)·§5-4(위험도–Gate 불일치 사유) 신설(P-06/P-08/P-09).
- **Phase D(구조 정리)**: `02.SKILL_INDEX.md §6`을 `_PENDING_IMPORT_LIST.md` SoT 참조로 축소(P-10), mermaid RC/API 중복 라벨·PLAN→VL 엣지·GATE042 ID 수정(P-11/P-12/P-14), 루트 `CLAUDE.md`에 언어 혼용 의도 명시(P-13).
- **Phase E(재고조사)**: 0회 스킬 9개 판정 — §5 참조.
- **Phase G(i2i 반입)**: P-16 축소안으로 14번째 스킬 반입. 고유 가치 4종(의도 라우팅/요구사항 재구성/최소 해법 나침반/변경 설명)만 `REFERENCE_*.md` 평면 구조로 반입, 중복 절차는 기존 소유 문서 참조로 치환. frontmatter·벤더 파일 제외, 한국어 7섹션 재작성(P-15/P-18, Q-3=제거 통일, Q-5=4종 반입하되 파이프라인 소유권 제거). `01.SKILL_TEMPLATE.md §2-1` 보조 참조 문서 규칙 공식화. ADR-040.
- **Phase H(환류)**: `_LATEST.md`를 "하네스 유지보수 최신/부착 프로젝트 최신" 2행 구조로 확장(Q-4=2행 선택), `validate-report-consistency.mjs` 포인터 인식 하위 호환 확장. ADR-041.

## 2. 변경 파일

| 파일 | 변경 내용 | 이유 |
|---|---|---|
| `06.REPORT_TEMPLATE.md` | 헤더 2칸 + §5-1~§5-4 신설 | P-01, P-02, P-06, P-08, P-09 |
| `05.WORKING_CONTEXT.md` | §1-1 프로젝트 상수 표, 활성 스킬 14개 | P-06, 스킬 추가 |
| `02.SKILL_INDEX.md` | §2 14번 행, §3 mermaid 수정+I2I 노드, §4 행 4개, §6 축소, §7 반입 이력 | P-05, P-10~P-14, 스킬 등록 |
| `01.SKILL_TEMPLATE.md` | §2-1 보조 참조 문서 규칙 | P-15 구조 공백 |
| `skills/intent-to-implementation/SKILL.md` 외 REFERENCE 4종(신규) | 축소 반입 본체 | P-16 축소안 |
| `10.ADR.md` | ADR-040, ADR-041 | 구조 결정 기록 |
| `_SOURCE_MAPPING.md` | §0 출처 2행, i2i 반영 섹션 | 반입 추적 |
| `reports/_LATEST.md` | 2행 구조 전환 | P-07 |
| `scripts/validate-report-consistency.mjs` | 포인터 정규식 하위 호환 확장 | 2행 구조 대응 |
| 루트 `CLAUDE.md` | 언어 안내 1줄 | P-13 |

## 3. 검증 결과

| 검증 항목 | 결과 | 비고 |
|---|---|---|
| `validate-docs.mjs` | PASS | 64개 문서 |
| `validate-skills.mjs` | PASS | 14개 스킬(신규 i2i 포함, 7섹션+HCR+Handoff 대상 실존) |
| `validate-references.mjs` | PASS | 이 Report 게시 후 재실행 기준 |
| `validate-report-consistency.mjs` | PASS | 스킬 이름 집합 14개 일치, 2행 포인터 인식 |
| `validate-no-personal-paths.mjs` | PASS | |
| `validate-harness.mjs` | PASS | |
| skill-gate 수동 판정(i2i) | PASS | 필수 7섹션 구체 작성, Quality Gate 작업 특화(의도 분류·Unresolved 추측 금지), Handoff 실경로 |

## 4. Checklist 결과

| Checklist | 결과 | Report 반영 |
|---|---|---|
| 해당 없음 | — | 문서·스킬 작업으로 적용 대상 Checklist 없음(`gates/skill-gate.md`, `gates/document-gate.md` 기준으로 판정) |

## 5. 발견된 문제

Phase E — 0회 스킬 9개 재고조사 판정(실사용 근거 P-04 분류표 기준):

| 스킬 | 판정 | 근거 |
|---|---|---|
| `api-design`, `error-handling`, `security-review` | 유지 | 백엔드 계약이 아직 없어 발동 조건 미도래(시점 문제) |
| `git-workflow` | 유지 + 발동 조건 강화 완료 | §4에 "파일 이동·폴더 구조 변경" 우선 행 추가 |
| `planning` | 유지 + 발동 조건 강화 완료 | §4에 "XL/L 구조 작업 전" 우선 행 추가. P-05 재작업이 실증 근거 |
| `quality-gate` | 유지(관찰) | Gate 직접 적용과 역할이 겹치는 경향. 다음 재고조사에서 실사용 재확인 |
| `report-consistency` | 유지(관찰) | 스크립트=자동 검사, 스킬=수동 판단으로 역할 분담. 이중화 아님으로 판정 |
| `skill-scout`, `skill-stocktake` | 유지 | 하네스 유지보수에서만 발동하는 성격 — 이번 작업에서 실제 발동됨 |
| `agent-recovery` | 유지 | 안전망 성격, 반복 FAIL 미발생은 정상 |

| 심각도 | 문제 | 처리 |
|---|---|---|
| Minor | 이전 superseded Report 2건(2026-07-15, 2026-07-21 ui-ux)이 §8-1과 달리 archive 미이동 상태였음 | 이번 게시 트랜잭션에서 함께 이동, digest 갱신 |

## 6. 미해결 항목

- **Q-1 "Browser" 정체**(자동화 도구 vs 수동 확인): 사용자 확인 필요. 판정에 따라 `browser-qa` 승격 또는 `verification-loop` 절차 흡수(P-03)
- 챱챱 폴더 측 작업: Report 2건 Git 서술 정정 주석(A-3), "테스트 미구축" 프로젝트 상수 기입(C-1) — 챱챱 폴더에서 별도 세션으로 수행
- `vue-ui-polish` 반입(Phase F): 원본 zip 제공 시 진행. ADR(스택 한정 스킬 허용)은 그때 작성
- `verification-loop` 보강 후보: i2i 원본의 검증 사다리(validation-rules), `planning` 보강 후보: 계층 책임 매핑(implementation-workflow) — 필요 반복 확인 후 재검토
- i2i 원저작 출처 미확인 — 확인되면 `_SOURCE_MAPPING.md §0` 갱신

## 7. Working Context 반영 여부

- 반영 필요: 예
- 반영 내용: 활성 스킬 14개 갱신 완료. §1-1 프로젝트 상수 표 신설(빈 템플릿 상태 유지 — 실제 상수는 부착 프로젝트에서 기입)

## 8. 다음 작업

1. ~~사용자에게 Q-1("Browser" 정체) 확인 → Phase B 처리~~ → §9에서 처리 완료
2. 챱챱 폴더에서 A-3 정정 주석 + C-1 프로젝트 상수 기입, 과거 Report의 "Browser" 표기 정정 주석(B-4)
3. `vue-ui-polish` zip 제공 시 Phase F 반입
4. `main` 병합으로 공식 반영 확정(병합 전까지 이 작업은 공유 진행 상태)

---

## 9. 후속 작업 — Phase B: `browser-qa` 정식 승격 (2026-08-02, 같은 세션)

§5-3 기준: 이 후속 작업은 앞선 §3 검증 결과를 무효화하지 않는 보완이므로 누적 기록한다.

- 사용자 확인 결과(Q-1): "Browser"의 실체는 **자동화 도구 사용** → 처방대로 `browser-qa`를 D등급에서 15번째 정식 스킬로 승격(ADR-042).
- 변경 파일: `skills/browser-qa/SKILL.md`(신규), `02.SKILL_INDEX.md`(§2 15번 행·§3 BQA 노드·§4 행·§7 이력), `05.WORKING_CONTEXT.md`(활성 스킬 15개), `_PENDING_IMPORT_LIST.md §2`(승격 완료 갱신), `10.ADR.md`(ADR-042).
- 검증: 검증 스크립트 6종 재실행 결과는 아래 표와 같다.

| 검증 항목 | 결과 | 비고 |
|---|---|---|
| `validate-skills.mjs` | PASS | 15개 스킬 |
| `validate-report-consistency.mjs` | PASS | 이름 집합 15개 일치 |
| 나머지 4종(docs, references, no-personal-paths, harness) | PASS | |
| skill-gate 수동 판정(browser-qa) | PASS | 재현 가능성 중심의 작업 특화 Gate, Handoff 실경로 |
