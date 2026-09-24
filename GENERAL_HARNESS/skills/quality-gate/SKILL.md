# Quality Gate

> 목적: 산출물이 다음 단계로 넘어가도 되는지 PASS/WARN/FAIL로 판정한다.  
> 사용 위치: `GENERAL_HARNESS` 공통 스킬  
> 출력물: 품질 판정

---

## 0. Harness Control Rule

- 이 스킬은 `00.HARNESS_RULES.md`의 하위 모듈이다.
- 충돌 시 이 스킬의 절차를 중단하고 `00.QUICK_REF.md`와 `00.HARNESS_RULES.md §3` 우선순위에 따라 상위 규칙을 따른다. 위험 작업 WARN은 사용자 확인 전 스킬 단독으로 진행하지 않는다.

---

## 1. Trigger

- 문서/스킬/API/DB/결제/보안 산출물 검수
- 작업 완료 전 최종 확인
- 자동 검증 PASS 이후 의미 품질을 따로 확인해야 하는 경우

---

## 2. Do Not Trigger

- 단순 아이디어 브레인스토밍
- 검수 대상 산출물이 아직 없는 경우
- 사용자가 명시적으로 초안만 원하고 판정을 원하지 않는 경우

---

## 3. Required Inputs

| 입력물 | 필요 이유 |
|---|---|
| `08.QUALITY_GATE.md` | 공통 판정 기준 확인 |
| `gates/*.md` | 산출물별 Gate 기준 확인 |
| 관련 Checklist(SRS/ERD/API/결제/릴리즈 대상일 때만) | 세부 항목 확인. Gate 판정만으로 충분한 산출물은 생략 가능 |
| 작업 산출물 | 실제 판정 대상 |

---

## 4. Procedure

1. 산출물 유형을 판단한다.
2. `08.QUALITY_GATE.md §7-2` 매트릭스로 관련 Gate를 전부 선택한다(하나만 고르지 않는다).
3. 필요하면 Checklist를 추가 적용한다.
4. `skills/verification-loop/SKILL.md` 결과가 있으면(빌드/테스트를 실행한 경우) 반드시 포함한다.
5. `08.QUALITY_GATE.md §7-2`의 전역 공식(`maxSeverity(Verification, 적용 Gate 전부, 적용 Checklist 전부)`)으로 최종 판정하고 위험 WARN인지 구분한다.
6. 자동 검증 결과가 구조 PASS인지 의미 PASS인지 구분한다.
7. Report에 근거를 남긴다.

---

## 5. Quality Gate

| 판정 | 기준 |
|---|---|
| PASS | 산출물 유형에 맞는 Gate를 적용했고 필수 기준과 검증 근거가 충족됨 |
| WARN | 일반 보완 사항은 있으나 위험 작업이 아니거나, 위험 WARN은 중단/확인 상태로 기록됨 |
| FAIL | 필수 Gate 기준을 충족하지 못하거나 위험 WARN을 진행 가능으로 오해하고 다음 단계로 넘기려 함 |

---

## 6. Output Format

```md
## Quality Gate 결과

- 사용 이유:
- 확인한 입력물:
- 적용한 Gate:
- 적용한 Checklist(해당 시, 없으면 N/A):
- 구조 PASS(자동 검증 통과) 여부:
- 의미 PASS(내용 품질, 사람/AI 판단) 여부:
- 판단 결과:
- PASS/WARN/FAIL:
- 위험 WARN 여부:
- 다음 연결:
```

---

## 7. Handoff

산출물 유형에 따라 연결한다. **산출물이 여러 유형에 동시에 해당하면 해당하는 Gate를 전부 적용한다** — 하나만 고르지 않는다. **어떤 산출물이 어떤 Gate 조합에 해당하는지는 `08.QUALITY_GATE.md`의 §7-2 표가 유일한 SoT다 — 이 스킬은 그 표를 다시 옮겨 적지 않는다.** 이 스킬의 역할은 산출물 유형을 판단해 §7-2 표에서 해당 행을 찾고, 그 Gate들을 전부 적용한 뒤 최악 판정으로 집계하는 것이다(외부 검수 D-01).

Gate 판정 이후, 대상이 SRS/ERD/API/결제/릴리즈 중 하나면 해당 checklists 폴더의 체크리스트를 추가로 적용한다. Checklist PASS는 위 Gate들의 WARN/FAIL을 낮추지 못한다. 최종적으로 `06.REPORT_TEMPLATE.md`에 결과를 남긴다.

---

## 8. Anti-Patterns

- 자동 검증 PASS를 내용 품질 PASS로 해석하기
- 모든 WARN을 기록 후 진행으로 처리하기
- 산출물 유형과 무관한 Gate를 적용하기
- FAIL을 미해결 항목으로만 남기고 진행하기
