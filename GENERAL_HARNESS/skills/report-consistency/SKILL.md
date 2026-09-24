# Report Consistency

> 목적: Report, Working Context, Skill Index 사이의 "현재 기준"이 서로 다른 것을 가리키지 않는지 점검한다.
> 사용 위치: `GENERAL_HARNESS` 공통 스킬
> 출력물: 최신성 일치 여부 판정과 필요한 동기화 방향

---

## 0. Harness Control Rule

- 이 스킬은 `00.HARNESS_RULES.md`의 하위 모듈이다.
- 충돌 시 이 스킬의 절차를 중단하고 `00.QUICK_REF.md`와 `00.HARNESS_RULES.md §3` 우선순위에 따라 상위 규칙을 따른다. 위험 작업 WARN은 사용자 확인 전 스킬 단독으로 진행하지 않는다.

---

## 1. Trigger

- Report를 새로 추가했을 때
- Report를 `reports/archive/`로 이동했을 때
- `05.WORKING_CONTEXT.md`를 갱신했을 때
- `02.SKILL_INDEX.md`의 Active 스킬 수가 바뀌었을 때
- `03.CONTEXT_BUDGET.md §4-2`의 최신성 충돌 Stop Condition에 해당하는 정황이 의심될 때

---

## 2. Do Not Trigger

- 단순 오탈자 수정만 한 경우
- Report나 Working Context와 무관한 단일 코드 변경인 경우
- 직전 작업에서 이미 이 스킬로 검증한 뒤 아무것도 바뀌지 않은 경우

---

## 3. Required Inputs

| 입력물 | 필요 이유 |
|---|---|
| `reports/_LATEST.md` | 현재 최신 Report 포인터 확인 |
| `_LATEST.md`가 가리키는 실제 Report 파일 | 포인터가 가리키는 파일이 실제 존재하는지 확인 |
| `05.WORKING_CONTEXT.md` | 현재 상태 표와 각 상태 요약 섹션의 Report 경로 확인 |
| `02.SKILL_INDEX.md` | 활성 스킬 목록과 개수 확인 |
| `reports/README.md` | Report 보관·아카이브 기준 확인 |
| `reports/archive/HISTORY_DIGEST.md`, `reports/archive/` 실제 파일 목록 | archive 색인이 실제 보관 파일과 빠짐없이 일치하는지 확인 |

---

## 4. Procedure

1. `reports/_LATEST.md`가 가리키는 파일 경로가 실제로 존재하는지 확인한다.
2. 그 Report가 top-level `reports/`에 있는지, `archive/`에 잘못 남아있지는 않은지 확인한다.
3. `05.WORKING_CONTEXT.md`의 "현재 하네스 상태" 표에 있는 값(활성 스킬 수 등)이 `02.SKILL_INDEX.md`와 일치하는지 확인한다.
4. `05.WORKING_CONTEXT.md`의 각 "상태 요약" 섹션에서 "현재 기준은 ~이다"처럼 현재형으로 특정 Report 경로를 고정 지목하는 문장이 있는지 찾는다. 있다면 그 경로가 실제로 아직 유효한 최신 경로인지, 혹은 이미 archive로 이동해 깨졌는지 확인한다.
5. top-level `reports/`에 superseded 표시 없이 남아있는 과거 Report가 있는지 확인한다.
6. `reports/archive/`의 실제 파일 목록이 `reports/archive/HISTORY_DIGEST.md`의 색인에 빠짐없이 반영되어 있는지 확인한다. **digest에 있지만 archive에 실물이 없는 파일은, `HISTORY_DIGEST.md`의 `PURGE_EVENT` 블록(각 이벤트가 event_id/date/approval/count를 갖는 독립 블록) 중 어딘가에 명시적으로 포함되어야만 정상이다 — 어떤 이벤트에도 없으면 진짜 고아 행이다(외부 검수 M-06/X-06/G-06, ADR-034). 삭제가 여러 번 있었으면 이벤트가 여러 개다 — 기존 이벤트를 고쳐서 새 삭제를 흡수하지 않는다.** `scripts/validate-report-consistency.mjs`가 각 이벤트를 독립적으로 검사한다: event_id 유일성, count와 실제 목록 길이 일치, approval이 실제 존재하는 ADR인지, 그 이벤트 파일들이 digest 표에 실제로 있는지, archive에 실제로 없는지.
7. 위 항목 중 하나라도 불일치하면 PASS가 아니라 WARN 또는 FAIL로 판정한다. **PURGE_EVENT 관련 불일치(event_id 중복, count 불일치, 존재하지 않는 ADR 인용, 목록에 없는 고아 등)는 전부 FAIL이다 — WARN으로 완화하지 않는다(D-021 fail-open 금지 원칙).**
8. 불일치를 발견하면 새 작업을 시작하기 전에 먼저 동기화 방향을 제시한다(`03.CONTEXT_BUDGET.md §4-2`의 최신성 충돌 Stop Condition을 따름).

---

## 5. Quality Gate

| 판정 | 기준 |
|---|---|
| PASS | `_LATEST.md` 포인터가 실제 존재하고, Working Context·Skill Index가 같은 현재 상태를 가리키며, top-level에 superseded 미표시 과거 Report가 없고, `reports/archive/HISTORY_DIGEST.md`가 archive 폴더 전체를 반영하며 모든 PURGE_EVENT가 구조적으로 무결함 |
| WARN | 과거 Report 경로가 남아있지만 "당시 기준"으로 명확히 구분되어 있거나, 사소한 표현 차이만 있음 |
| FAIL | `_LATEST.md` 포인터가 존재하지 않는 파일을 가리키거나, Working Context가 다른 Report/스킬 수를 현재 상태처럼 제시하거나, `reports/archive/HISTORY_DIGEST.md`에 archive 파일이 누락되거나, PURGE_EVENT의 event_id·count·approval·집합 관계 중 하나라도 어긋남 |

---

## 6. Output Format

```md
## Report Consistency 결과

- 확인한 최신 포인터: `reports/_LATEST.md` → ...
- 실제 최신 Report 존재 여부:
- Working Context 현재 상태 표와 Skill Index 일치 여부:
- Working Context 상태 요약 섹션의 낡은 경로 지목 여부:
- top-level 과거 Report의 superseded 표시 여부:
- PASS/WARN/FAIL:
- 필요한 동기화 방향:
```

---

## 7. Handoff

다음 연결: `03.CONTEXT_BUDGET.md`(§4-2 불일치 시 Stop Condition 적용) → `06.REPORT_TEMPLATE.md`(스크립트 재확인은 scripts/validate-report-consistency.mjs 사용)

---

## 8. Anti-Patterns

- `_LATEST.md`만 보고 Working Context는 확인하지 않기
- 파일명 날짜가 가장 최신이라는 이유만으로 그 Report를 현재 기준으로 판단하기(archive로 이동된 파일일 수 있음)
- archive에 있는 Report를 현재 Next Work 기준으로 사용하기
- 과거 상태 요약 문장을 현재형("현재 기준은 ~이다")으로 새로 쓰기 — 항상 `reports/_LATEST.md`를 가리키게 하거나 "당시 기준"으로 명시한다
