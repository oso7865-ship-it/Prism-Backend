# Planning

> 목적: 코드를 작성하기 전에 무엇을 만들지, 무엇을 만들지 않을지, 어떤 파일을 건드릴지 먼저 정리한다.
> 이 스킬은 `09.AGENT_WORKFLOW.md §1`의 Planning Agent 역할 중 계획 산출물을 실제로 작성하는 부분을 담당한다. Planning Agent 역할 자체(작업 범위·읽을 문서·적용 스킬 결정)를 대체하지 않는다.
> 사용 위치: `GENERAL_HARNESS` 공통 스킬
> 출력물: 계획 문서(Spec + Task 목록)

---

## 0. Harness Control Rule

- 이 스킬은 `00.HARNESS_RULES.md`의 하위 모듈이다.
- 충돌 시 이 스킬의 절차를 중단하고 `00.QUICK_REF.md`와 `00.HARNESS_RULES.md §3` 우선순위에 따라 상위 규칙을 따른다. 위험 작업 WARN은 사용자 확인 전 스킬 단독으로 진행하지 않는다.

---

## 1. Trigger

- 여러 파일에 걸친 기능 구현을 시작하기 전
- 한 세션에 끝나지 않을 가능성이 있는 작업을 시작할 때
- 요구사항이 있지만 "무엇을 안 할지"가 아직 불명확할 때
- 구현 방향이 여러 개라 하나를 먼저 정해야 할 때

---

## 2. Do Not Trigger

- 한 파일, 한 함수 수준의 단순 수정
- 사용자가 "계획 없이 바로 진행"을 명시적으로 요청한 경우
- 이미 `Confirmed` 상태의 API/DB 명세를 **단일 파일 또는 소규모 변경**으로 그대로 구현만 하면 되는 경우(이때는 별도 계획 없이 구현 작업을 진행하고, 구현이 끝나면 `skills/verification-loop/SKILL.md`로 넘어감). **Confirmed 명세라도 여러 파일에 걸치거나 한 세션에 끝나지 않을 가능성이 있으면 위 Trigger가 우선하며 계획을 생략하지 않는다.**

---

## 3. Required Inputs

| 입력물 | 필요 이유 |
|---|---|
| 목표 한 줄 | 계획의 출발점 |
| 관련 요구사항 또는 API/DB 명세 | 범위 판단 근거 |
| 현재 코드/문서 구조 | 어떤 파일을 새로 만들지, 어떤 파일을 고칠지 판단 |
| 제약 조건(기한, 기술 스택, 이미 확정된 부분) | Non-Goals와 우선순위 판단 |

---

## 4. Procedure

1. **목표(Goal)**: 한 줄로 무엇을 만드는지 적는다.
2. **Goals**: 이번 작업이 실제로 해결하는 것을 나열한다.
3. **Non-Goals**: 이번 작업이 의도적으로 하지 않는 것을 나열한다. 이 항목이 없으면 계획으로 인정하지 않는다 — 범위가 스스로 불어나는 것을 막는 핵심 장치다.
4. **영향 범위**: 신규/수정 파일을 직접 변경, 호출자·소비자·설정·테스트·계약의 연결 영향, 미확인 범위, 검증 방법으로 나눠 기록한다. 검색하지 못한 범위를 영향 없음으로 단정하지 않는다. 기존 해법 선택이 필요하면 `skills/intent-to-implementation/REFERENCE_MINIMAL_SOLUTION_COMPASS.md`, 버전·API 근거가 불확실하면 `skills/documentation-lookup/SKILL.md`를 조건부로 사용한다.
5. **Task 분해**: 실행 가능한 단위로 나누고, 각 Task마다 "무엇을 하는지"와 "어떻게 확인하는지"를 함께 적는다. 체크박스(`- [ ]`)로 남겨 진행 상태를 추적한다.
6. **위험 판단**: Task 중 구조/DB/보안/결제 관련이 있으면 `04.GATEGUARD.md` 기준으로 표시하고, 계획 단계에서 사용자 확인이 필요한 항목을 미리 표시한다.
7. 검증 시나리오가 부족하면 `skills/test-design/SKILL.md`로 요구사항과 기대 결과를 연결한다. 계획이 끝나면 승인된 범위에서 계획대로 구현 작업을 진행한다. 구현이 끝나면 `skills/verification-loop/SKILL.md`(구현 완료 검증)로 이어진다.

---

## 5. Quality Gate

| 판정 | 기준 |
|---|---|
| PASS | Goals, Non-Goals, 영향 범위(신규/수정 파일), Task 분해가 모두 있고 위험 Task가 표시됨 |
| WARN | Goals와 Task는 있으나 Non-Goals가 약하거나 영향 범위가 불명확함 |
| FAIL | Non-Goals가 아예 없거나, 위험 작업(구조/DB/보안/결제) Task를 표시 없이 바로 실행하려 함 |

---

## 6. Output Format

```md
## Planning 결과

- 목표(Goal):
- Goals:
- Non-Goals:
- 영향 범위(신규 파일 / 수정 파일):
- Task 목록:
  - [ ] Task 1: ... (확인 방법: ...)
  - [ ] Task 2: ... (확인 방법: ...)
- 위험 Task 및 사용자 확인 필요 여부:
- PASS/WARN/FAIL:
- 다음 연결:
```

---

## 7. Handoff

다음 연결: `skills/api-design/SKILL.md` 또는 해당 구현 작업 → `skills/verification-loop/SKILL.md`(구현 완료 후 검증) → `06.REPORT_TEMPLATE.md`

---

## 8. Anti-Patterns

- Non-Goals 없이 Goals만 적고 계획을 끝냈다고 하기
- Task를 너무 크게 쪼개서 "구현하기" 한 줄로 끝내기(확인 방법이 없으면 Task가 아니다)
- 계획 단계에서 위험 작업을 발견하고도 표시 없이 바로 실행 단계로 넘어가기
- 계획을 세운 뒤 실제 구현 중 계획과 달라졌는데 계획 문서를 갱신하지 않기
