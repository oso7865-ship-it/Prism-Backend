# 작업 리포트: harness-external-review-2026-07-12-round2-major-fixes

> Superseded note:
> 이 보고서의 다음 작업 판단은 `reports/_LATEST.md`가 가리키는 최신 Report로 대체되었다.
> 과거 의사결정 근거로는 유효하지만, 현재 Next Work 판단은 최신 Report와 `05.WORKING_CONTEXT.md`를 우선한다.

> 작성일: 2026-07-12
> 작업 범위: XL (게시 트랜잭션 재설계, Gate 라우팅·판정 통일, 검증 스크립트 재작성, 정정 사항 포함)
> 적용 스킬: `report-consistency`, `quality-gate`, `verification-loop`(회귀 테스트 실행)
> 적용 Gate: Document Gate, Skill Gate
> 위험 작업 여부: 예 (게시 트랜잭션·검증 스크립트 핵심 로직·Gate 판정 매트릭스 변경. 사용자가 "수정작업 진행해줘"로 명시적 확인함)

이 Report에는 "게시 상태" 필드를 두지 않는다(D-028).

---

## 0. 작업 범위 확인

| 항목 | 내용 |
|---|---|
| 요청 요약 | 여섯 번째 외부 검수(재검수, .gitkeep 포함 52개 파일 독립 대조)의 Critical 0건, Major 10건, Minor 5건 전부 반영. 충돌 10건·중복 4건·누락 9건은 대부분 위 항목과 겹침 |
| 수정 대상 | `scripts/validate-report-consistency.mjs`(고아 행 검사 전면 재작성), `reports/archive/HISTORY_DIGEST.md`(마커 카운트 버그 수정), `08.QUALITY_GATE.md`(흐름도 fan-out 재설계, 매트릭스 확장, 전역 최종판정 공식), `06.REPORT_TEMPLATE.md`(WARN 분류/해제 단계, §8-3 프로젝트 트랜잭션 신설, I/O 실패 롤백 명시), `09.AGENT_WORKFLOW.md`(§8-2/§8-3 참조 정정), `04.GATEGUARD.md`(사전 Gate FAIL/WARN 해제조건 분리), `gates/api-gate.md`, `gates/db-gate.md`, `gates/payment-gate.md`(1:1 재정렬), `skills/quality-gate/SKILL.md`(전역공식 반영), `07.SECURITY_BASELINE.md`(이미 참조형이라 추가 수정 없음), `checklists/*.md`(5개, 로컬판정 명시), `_SOURCE_MAPPING.md`(4~6차 provenance 보강, wildcard 제거), `03.CONTEXT_BUDGET.md`/`reports/README.md`/`reports/_LATEST.md`/`skills/report-consistency/SKILL.md`(삭제 예외 전파), `10.ADR.md`(ADR-028/029 정정, ADR-032 관련 표기 유지) |
| 제외 대상 | `_SOURCE_MAPPING.md`의 부분적 참조 검사(제외 문서에서도 `reports/` 아래 Report 파일명 패턴만 선택 검사) — 이번엔 구현하지 않고 알려진 한계로 명시 |
| 검증 방법 | 게시 전 6개 스크립트 실행. `validate-report-consistency.mjs`의 새 로직을 정상/2027고아/무단PURGED추가/개수불일치 4가지로 직접 재현 테스트 |
| 한계 | 이번 라운드도 매우 넓은 범위를 한 번에 다뤄, 개별 항목의 실사용 검증(실제 프로젝트 적용)까지는 못 했다 |

---

## 1. 정정 사항 — 이전 Report(archived)의 43/44 수치 차이 (M-10/X-10)

`reports/2026-07-12_harness-orphan-check-explicit-list-fix_report.md`(현재 top-level에 있으며 이번 라운드에서 archive로 이동 예정)의 §5는 게시 전 `validate-docs`가 "43 markdown files"를 검사했다고 기록했다. 그 Report 자신이 트리에 이미 쓰여 있었으므로(§8-2 1번: 초안 작성 후 검사) 그 시점 카운트에도 44가 반영됐어야 한다는 지적을 받았다.

**이 Report는 수정하지 않는다(D-028, 이미 게시되어 archive로 이동한 콘텐츠는 불변).** 대신 여기에 차이를 기록한다: 정확한 원인(검사 시점과 파일 저장 시점의 순서 문제인지, 다른 이유인지)은 그 세션의 정확한 명령 실행 순서를 재구성해야 확정할 수 있어 현재는 단정하지 않는다. 다만 그 Report의 §6("다음 작업: 없음")은 부정확했다 — 실제로는 이번 재검수가 찾아낸 Major 10건이 이미 존재했다.

---

## 2. Major 10건 처리

| 번호 | 문제 | 수정 내용 |
|---|---|---|
| M-01 | Report 트랜잭션이 validator FAIL만 롤백 대상으로 다룸 | `06.REPORT_TEMPLATE.md §8-2`에 9번 단계 추가 — 4/5/7번의 명령 자체 실패(권한 오류, 디스크 부족 등)도 validator FAIL과 동일하게 롤백 |
| M-02 | project Report의 비-ZIP 완료 경로가 §8-2와 직접 충돌 | `06.REPORT_TEMPLATE.md`에 §8-3(프로젝트 Report 완료 트랜잭션, ZIP 생성 없음) 신설. `09.AGENT_WORKFLOW.md`의 §8-2 오참조 2곳을 §8-3으로 정정 |
| M-03 | 복합 Gate 흐름도가 여전히 단일 분기(switch) | `08.QUALITY_GATE.md §7` 흐름도를 "해당하는 Gate 전부 표시 → 전부 판정 → 최악" fan-out 구조로 재설계 |
| M-04 | Gate 필수 항목-판정 1:1 재발(API Method/Auth, DB Index, Payment 로그) | api-gate PASS에 Method 선택이유·인증·권한 전부 명시, db-gate에서 Index를 "권장이지 PASS 필수 아님"으로 명확화, payment-gate PASS/FAIL에 로그 기록 명시 |
| M-05 | Verification·Gate·Checklist 전역 최종판정 공식 없음 | `08.QUALITY_GATE.md §7-2`에 `최종 판정 = maxSeverity(Verification, 적용 Gate 전부, 적용 Checklist 전부)` 공식 신설. 5개 Checklist의 "결과 요약"을 "이 Checklist 자체의 판정"으로 재정의 |
| M-06 | PURGED_FILES 명시 목록도 연도 하드코딩·부분문자열 검사·자기승인으로 우회 가능 | `scripts/validate-report-consistency.mjs` 전면 재작성 — digest 표 행 구조적 파싱, marker 정확히 한 쌍, purged⊆digest, purged∩archive=∅, 삭제 로그 count 일치, 연도 4자리 일반화. 정상/2027고아/무단추가/개수불일치 4가지 재현 테스트 완료 |
| M-07 | 구조 WARN이 게시를 막지 못함 | `06.REPORT_TEMPLATE.md §8-2`에 3-1번 단계 추가 — WARN을 일반/구조/위험으로 분류하고 구조·위험 WARN은 해제 증거 확보 전 게시 금지 |
| M-08 | archive 삭제 예외가 다른 문서에 전파 안 됨 | `03.CONTEXT_BUDGET.md`, `reports/README.md`, `reports/_LATEST.md`, `skills/report-consistency/SKILL.md`에 PURGED_FILES/삭제 예외 인지 문구 추가 |
| M-09 | Source Mapping의 4차 이후 provenance 누락, 5차 wildcard | `_SOURCE_MAPPING.md §0`에 4~6차 검수 provenance 행 추가, wildcard 참조를 실제 파일명으로 정정 |
| M-10 | 이전 Report의 43/44 수치 차이, "다음 작업 없음" 오류 | 위 §1에 정정 기록(원본은 수정하지 않음) |

---

## 3. Minor 5건 처리

| 번호 | 문제 | 수정 내용 |
|---|---|---|
| m-01 | 검증기 개수 6 하드코딩 | 이전 라운드에서 이미 구조적 서술로 교체 완료(이번 검수도 이 부분은 수정됨으로 확인) |
| m-02 | ADR-028 부분대체가 상태 셀에 없음 | 상태 셀에 `Partially superseded by ADR-029` 이동 |
| m-03 | 사전 Gate FAIL이 사용자 확인만으로 풀리는 것처럼 읽힘 | `04.GATEGUARD.md §7` 표에서 WARN/FAIL 해제조건 분리, FAIL은 재검증 PASS만 인정 명시 |
| m-04 | MJS 로직 수정 Report가 Document Gate만 기록 | 이 Report는 적용 스킬에 `verification-loop`(회귀 테스트 실행)를 명시 |
| m-05 | ADR-029의 파일 수/Minor 건수 오류 | "70개 파일"→"70개 Markdown, 전체 78개", "Minor 6·총18"→"Minor 7·총19"로 정정(결정 자체는 유지) |

---

## 4. validate-report-consistency.mjs 재현 테스트 결과

| 시나리오 | 수정 전 | 수정 후 |
|---|---|---|
| 정상 상태 | PASS | PASS |
| 2027년 고아 행(digest 표에만 추가) | PASS(놓침) | **FAIL** |
| PURGED_FILES에 digest 표 행 없는 파일명 무단 추가 | PASS(놓침) | **FAIL**(2개 사유로 동시 검출) |
| 삭제 로그 개수만 조작(30→29, 목록은 그대로) | PASS(놓침) | **FAIL** |

새 로직 구현 중 자체 버그(마커를 세는 정규식이 설명 문구 속 마커 이름 언급까지 세어 정상 상태도 FAIL로 오판)를 발견해 즉시 수정(마커는 그 줄에 단독으로 있을 때만 인정하도록 정규식 보강).

---

## 5. 게시 전 검증 (6개, validate-package 제외)

```txt
PASS validate-harness
PASS validate-docs (44 markdown files checked)
PASS validate-skills (12 skills checked)
PASS validate-no-personal-paths
PASS validate-references (path + section references resolve)
PASS validate-report-consistency (PURGED_FILES 구조적 검증 통과)
```

전부 PASS이므로 게시를 진행한다(WARN 없음, 3-1 단계의 해제 절차 불필요).

---

## 6. 알려진 한계 (정직하게 남김)

- `_SOURCE_MAPPING.md`의 부분 참조 검사(제외 문서에서도 `reports/` 아래 Report 파일명 패턴만 선택 검사)는 이번에 구현하지 않았다.
- `01.SKILL_TEMPLATE.md`와 실제 12개 스킬이 같은 규칙으로 자동 검사되는 장치는 여전히 없다(수동 동기화).
- PURGED_FILES 목록 자체가 향후 갱신을 빠뜨리면(또 다른 자기 참조 누락) 여전히 놓칠 수 있다 — 다만 최소한 날짜 추정보다는 훨씬 명확한 신호를 남긴다.

---

## 7. 다음 작업

없음(위 한계 3건은 "다음에 필요하면 검토할 후보"이지 확정된 작업 큐 항목은 아니다).
