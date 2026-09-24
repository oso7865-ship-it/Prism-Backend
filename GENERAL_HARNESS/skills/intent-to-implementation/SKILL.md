# Intent to Implementation

> 목적: 짧거나 불완전하거나 대화체인 요청("어떻게 할까?", "구현해줘", "고쳐줘", "알아서 완성해줘")을 받았을 때, 의도 분류 → 요구사항 재구성 → 최소 충분 해법 판단을 거쳐 기존 하네스 흐름(계획 → 구현 → 검증 → Report)으로 안전하게 넘긴다.
> 사용 위치: `GENERAL_HARNESS` 공통 스킬 (문서 스킬)
> 출력물: 의도 분류 결과, 요구사항 맵(Confirmed/Inferred/Unresolved), 관찰 가능한 완료 기준, 필요 시 변경 설명 문서
>
> 소유 범위: 이 스킬은 **의도 라우팅, 요구사항 재구성, 최소 해법 나침반, 변경 설명** 4가지만 소유한다. 사전 조사 원칙은 `CLAUDE.md §1`, 작업 계약은 `AGENTS.md` 시작 순서 3, 계획은 `skills/planning/SKILL.md`, 검증은 `skills/verification-loop/SKILL.md`가 소유하며 이 스킬은 그 규칙을 재정의하지 않고 참조만 한다(반입 검수 P-16 축소안).

---

탐색·재사용 선택은 `skills/intent-to-implementation/REFERENCE_MINIMAL_SOLUTION_COMPASS.md`가 소유한다. 그 문서의 탐색 근거 보강 부분만 ECC search-first 파생이며 `skills/intent-to-implementation/LICENSE`에 원 고지를 보존한다. 계획·문서 조사·실행 검증 기준을 이 스킬에 중복 정의하지 않는다.

## 0. Harness Control Rule

- 이 스킬은 `00.HARNESS_RULES.md`의 하위 모듈이다.
- 충돌 시 이 스킬의 절차를 중단하고 `00.QUICK_REF.md`와 `00.HARNESS_RULES.md §3` 우선순위에 따라 상위 규칙을 따른다. 위험 작업 WARN은 사용자 확인 전 스킬 단독으로 진행하지 않는다.

---

## 1. Trigger

- 요청이 짧거나 대화체라 "설명 요청인지 수정 요청인지"부터 판단해야 할 때
- 요청이 요구사항 문서를 가리키거나, 동작의 상당 부분이 암묵적으로 남아 있을 때
- "알아서 해줘", "완성해줘"처럼 세부 결정을 에이전트가 추론해야 하는 요청일 때
- 완료된 변경에 대해 사용자가 diff/기능/수정 내용의 설명을 요청할 때(변경 설명 절차만 단독 발동 가능)

---

## 2. Do Not Trigger

- 요청의 의도·범위·완료 기준이 이미 명확하고 단일 파일 소규모 수정인 경우
- 이미 Confirmed 상태의 명세를 그대로 구현만 하면 되는 경우(`skills/planning/SKILL.md`의 Trigger 판단을 따름)
- 하네스 자체 유지보수 작업(진입 흐름은 `09.AGENT_WORKFLOW.md`가 소유)
- 상위 하네스 규칙과 충돌하는 작업인 경우

---

## 3. Required Inputs

| 입력물 | 필요 이유 |
|---|---|
| 사용자의 원문 요청(요약이 아닌 실제 표현) | 의도 분류의 근거는 사용자가 실제로 쓴 동사다 |
| 대상 프로젝트의 구조·관례(확인 가능한 범위) | Inferred 판단의 근거. 조사 원칙 자체는 `CLAUDE.md §1`을 따른다 |
| 관련 명세·요구사항 문서·이전 Report(있으면) | Confirmed 판단의 근거 |

---

## 4. Procedure

1. **의도 분류**: `skills/intent-to-implementation/REFERENCE_INTENT_ROUTING.md`의 표로 요청을 설명/계획/설계/진단/구현/수정/리팩터링/검증 중 하나 이상으로 분류한다. 호기심 표현을 수정 권한으로 해석하지 않는다.
2. **사전 조사**: `CLAUDE.md §1`과 `AGENTS.md` 시작 순서에 따라 프로젝트 상태를 확인한다. 이 스킬은 조사 규칙을 추가하지 않는다.
3. **요구사항 재구성**: `skills/intent-to-implementation/REFERENCE_REQUIREMENT_RECONSTRUCTION.md`로 요구사항 맵을 만들고 각 항목을 Confirmed / Inferred / Unresolved로 표시한다. **Unresolved 중 공개 계약·DB 스키마·인증/권한·결제·비가역 작업에 해당하는 결정은 추측하지 않고 질문한다.**
4. **작업 계약**: `AGENTS.md` 시작 순서 3의 작업 계약 형식을 그대로 사용한다. 재구성한 요구사항 맵의 결론(목표·완료 기준·제외 범위)을 계약에 채워 넣는 것이 이 스킬의 기여다.
5. **최소 충분 해법 판단**: 설계·의존성 추가·추상화·리팩터링 전에 `skills/intent-to-implementation/REFERENCE_MINIMAL_SOLUTION_COMPASS.md`의 하강 순서를 적용한다. 판단이 결과를 바꾼 경우(의존성을 안 넣기로 함, 기존 코드 재사용 등) Report에 근거를 기록한다.
6. **계획·구현**: 여러 파일에 걸치면 `skills/planning/SKILL.md`로 넘긴다. 이 스킬은 계획 형식을 소유하지 않는다.
7. **검증**: 구현 완료 보고 전 `skills/verification-loop/SKILL.md`를 따른다. 이 스킬은 검증 기준을 소유하지 않는다.
8. **변경 설명**: 의미 있는 구현 후 또는 사용자가 설명을 요청하면 `skills/intent-to-implementation/REFERENCE_EXPLAIN_DIFF_FORMAT.md` 순서로 설명한다. 사소한 변경에는 설명 분량을 비례해서 줄인다.

---

## 5. Quality Gate

| 판정 | 기준 |
|---|---|
| PASS | 의도 분류 결과가 기록됨 + Unresolved 항목이 추측 없이 질문 또는 근거 확보로 해소됨 + 완료 기준이 관찰 가능한 결과(예: "중복 요청이 행을 추가로 만들지 않는다")로 작성됨 |
| WARN | Inferred 항목이 많은데 근거(기존 코드·관례) 표기가 약함, 또는 완료 기준이 "정상 동작"처럼 모호함 — 위험 작업과 겹치면 사용자 확인 전 진행하지 않음 |
| FAIL | 공개 계약·DB·보안·결제·비가역 작업에 해당하는 Unresolved 결정을 추측으로 진행함, 또는 설명/진단으로 분류된 요청에서 파일을 수정함 |

---

## 6. Output Format

```md
## Intent to Implementation 결과

- 의도 분류: 설명 / 계획 / 설계 / 진단 / 구현 / 수정 / 리팩터링 / 검증
- 요구사항 맵 요약:
  - Confirmed: ...
  - Inferred(근거 포함): ...
  - Unresolved(질문했거나 질문 예정): ...
- 완료 기준(관찰 가능한 결과):
- 최소 해법 판단이 결과를 바꾼 항목:
- PASS/WARN/FAIL:
- 다음 연결:
```

---

## 7. Handoff

다음 연결: `skills/planning/SKILL.md`(여러 파일 구현 시) → `skills/verification-loop/SKILL.md`(구현 완료 검증) → `06.REPORT_TEMPLATE.md`

수정 요청이 아닌 것으로 분류되면: 설명/진단 결과만 전달하고 `06.REPORT_TEMPLATE.md` 기준으로 Report 필요 여부를 판단한다.

---

## 8. Anti-Patterns

- "이게 왜 이래?"(진단 요청)를 수정 권한으로 해석해 파일을 고치기
- Inferred 항목을 사용자 요구사항인 것처럼 보고하기(근거 표기 없이)
- Unresolved 결정을 질문 비용이 아깝다는 이유로 추측 진행하기 — services→domain 재작업(실사용 검수 P-05)이 실제 발생 사례다
- 작은 요청에 요구사항 맵 전체를 사용자에게 되풀이해 보여주며 확인을 강요하기(맵은 내부 판단 도구다)
- 최소 해법 나침반을 이유로 Gate/Checklist가 요구하는 예외 처리·검증을 생략하기(`CLAUDE.md` Project Harness 절 참조)
