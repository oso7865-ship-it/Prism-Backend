# Skill Stocktake

> 목적: 현재 스킬 목록의 중복, 누락, 품질 편차를 점검한다.  
> 사용 위치: `GENERAL_HARNESS` 공통 스킬  
> 출력물: 스킬 재고조사

---

## 0. Harness Control Rule

- 이 스킬은 `00.HARNESS_RULES.md`의 하위 모듈이다.
- 충돌 시 이 스킬의 절차를 중단하고 `00.QUICK_REF.md`와 `00.HARNESS_RULES.md §3` 우선순위에 따라 상위 규칙을 따른다. 위험 작업 WARN은 사용자 확인 전 스킬 단독으로 진행하지 않는다.

---

## 1. Trigger

- 스킬이 5개 이상으로 늘었을 때
- 새 스킬 추가 전후
- Trigger가 겹치는 스킬이 의심될 때
- 스킬별 Quality Gate가 복붙처럼 반복되는지 점검할 때
- 규칙이 실제 행동으로 이어지는지 유지보수 평가가 필요할 때

---

## 2. Do Not Trigger

- 단일 스킬의 사소한 문구 수정
- 스킬 목록 변화가 없는 단순 작업

---

## 3. Required Inputs

| 입력물 | 필요 이유 |
|---|---|
| `02.SKILL_INDEX.md` | 스킬 목록과 연결 구조 확인 |
| `skills/*/SKILL.md` | 실제 스킬 내용 확인 |
| `01.SKILL_TEMPLATE.md` | 표준 구조 기준 확인 |
| `gates/skill-gate.md` | 스킬 Gate 기준 확인 |

---

## 4. Procedure

1. 스킬 목록을 수집한다.
2. Trigger와 Do Not Trigger 중복을 확인한다.
3. Quality Gate가 작업별 기준인지 확인한다.
4. Handoff가 실제 파일명/스킬명과 맞는지 확인한다.
5. 통합/분리/보류 후보를 정리한다.
6. 실제 행동 평가가 필요한 유지보수에서만 `skills/skill-stocktake/REFERENCE_BEHAVIOR_EVAL.md`를 읽고 사례·기준선·관측 증거를 정한다. 형식 검사와 실제 도구 기록을 구분하고, 미실행/관측 불가를 PASS로 집계하지 않는다. ECC 파생 평가 절차의 원 고지는 `skills/skill-stocktake/LICENSE`에 있다.

---

## 5. Quality Gate

| 판정 | 기준 |
|---|---|
| PASS | 중복 Trigger, 누락 섹션, 약한 Gate, 잘못된 Handoff 여부가 확인되고 조치 방향이 정리됨 |
| WARN | 일부 스킬 품질 편차가 있으나 즉시 사고로 이어지지는 않음 |
| FAIL | 중복 스킬이 많거나 필수 섹션/Gate/Handoff가 깨져 스킬 선택 기준이 무너짐 |

---

## 6. Output Format

```md
## Skill Stocktake 결과

- 사용 이유:
- 확인한 입력물:
- 판단 결과:
- 행동 평가(해당 시): 기준선/변경 후 증거, 실행 수, 관측 불가 수, 비교 한계
- 조치: 유지/수정/통합/보류
- PASS/WARN/FAIL:
- 위험 WARN 여부:
- 다음 연결:
```

---

## 7. Handoff

다음 연결: `gates/skill-gate.md` → `02.SKILL_INDEX.md` → `06.REPORT_TEMPLATE.md`

---

## 8. Anti-Patterns

- 섹션 존재만 보고 스킬 품질을 PASS 처리하기
- 스킬별 Gate가 모두 같은데도 문제 없음으로 판단하기
- Handoff에 존재하지 않는 스킬명을 남기기
- 프로젝트 전용 스킬을 전역 스킬로 섞기
