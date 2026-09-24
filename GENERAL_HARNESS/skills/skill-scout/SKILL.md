# Skill Scout

> 목적: 새 스킬을 만들기 전 기존 스킬로 해결 가능한지 탐색한다.  
> 사용 위치: `GENERAL_HARNESS` 공통 스킬  
> 출력물: 스킬 중복 방지 판정

---

## 0. Harness Control Rule

- 이 스킬은 `00.HARNESS_RULES.md`의 하위 모듈이다.
- 충돌 시 이 스킬의 절차를 중단하고 `00.QUICK_REF.md`와 `00.HARNESS_RULES.md §3` 우선순위에 따라 상위 규칙을 따른다. 위험 작업 WARN은 사용자 확인 전 스킬 단독으로 진행하지 않는다.

---

## 1. Trigger

- 새 스킬 생성 요청
- 기존 스킬로 처리 가능한지 불명확한 경우
- 스킬 목록이 늘어나기 전 정리 필요
- 대기 목록의 후보를 실제 스킬로 승격할지 판단할 때

---

## 2. Do Not Trigger

- 단순 문서 수정
- 이미 명확한 기존 스킬이 있는 경우
- 일회성 작업이라 독립 스킬로 유지할 가치가 없는 경우

---

## 3. Required Inputs

| 입력물 | 필요 이유 |
|---|---|
| `02.SKILL_INDEX.md` | 기존 스킬 목록 확인 |
| `01.SKILL_TEMPLATE.md` | 스킬 품질 기준 확인 |
| `_PENDING_IMPORT_LIST.md` | 보류 후보 여부 확인 |
| 새 스킬 후보 목적 | 독립 작업 단위인지 판단 |

---

## 4. Procedure

1. 기존 스킬 목록을 확인한다.
2. 후보 스킬의 Trigger와 기존 스킬 Trigger를 비교한다.
3. 기존 스킬 확장, 새 스킬 생성, 보류 중 하나로 판정한다.
4. 상위 하네스 규칙과 충돌 여부를 확인한다.
5. 필요하면 Skill Index 반영 항목을 작성한다.

---

## 5. Quality Gate

| 판정 | 기준 |
|---|---|
| PASS | 기존 스킬과의 중복 여부, 새 스킬 필요성, 등록 위치, 보류 여부가 명확함 |
| WARN | 새 스킬 필요성은 있으나 Trigger가 좁거나 기존 스킬 확장으로도 가능함 |
| FAIL | 기존 스킬과 중복되거나, 하네스 상위 규칙과 충돌하거나, 독립 작업 단위가 아님 |

---

## 6. Output Format

```md
## Skill Scout 결과

- 사용 이유:
- 확인한 입력물:
- 판단 결과:
- PASS/WARN/FAIL:
- 위험 WARN 여부:
- 다음 연결:
```

---

## 7. Handoff

다음 연결(새 스킬 생성으로 판정된 경우): `04.GATEGUARD.md`(§6-1 구조 작업 — 사용자 승인 또는 유효한 근거 확보) → `01.SKILL_TEMPLATE.md`(작성) → `gates/skill-gate.md`(판정) → `02.SKILL_INDEX.md`(등록) → `skills/report-consistency/SKILL.md`(Active 스킬 수·이름 동기화 확인, 필수) → `06.REPORT_TEMPLATE.md`

기존 스킬 확장으로 판정된 경우: `skills/skill-stocktake/SKILL.md` 또는 `02.SKILL_INDEX.md` → `06.REPORT_TEMPLATE.md`

---

## 8. Anti-Patterns

- 새 이름이 떠올랐다는 이유만으로 스킬 만들기
- 기존 스킬의 Trigger와 겹치는지 확인하지 않기
- 프로젝트 전용 규칙을 전역 스킬로 고정하기
- 보류 후보를 도입 조건 없이 바로 생성하기
