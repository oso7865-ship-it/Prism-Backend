# API Design

> 목적: REST API의 URL, Method, Request, Response, 상태코드, 권한 조건을 정리한다.  
> 사용 위치: `GENERAL_HARNESS` 공통 스킬  
> 출력물: API 설계

---

## 0. Harness Control Rule

- 이 스킬은 `00.HARNESS_RULES.md`의 하위 모듈이다.
- 충돌 시 이 스킬의 절차를 중단하고 `00.QUICK_REF.md`와 `00.HARNESS_RULES.md §3` 우선순위에 따라 상위 규칙을 따른다. 위험 작업 WARN은 사용자 확인 전 스킬 단독으로 진행하지 않는다.

---

## 1. Trigger

- 새 API 명세 작성
- 프론트/백엔드 연결 전 API 구조 정리
- 요청/응답/상태코드 검수
- 기존 API 명세에 실패 응답이나 권한 조건이 빠졌는지 점검

---

## 2. Do Not Trigger

- DB 테이블만 설계하는 경우
- 단순 코드 오타 수정
- 이미 승인된 API 명세가 `gates/api-gate.md`의 PASS 기준(Method/URL/Request/Response/실패 응답/인증·권한)을 전부 충족해 그대로 구현만 하는 경우. **승인됐어도 이 중 하나라도 빠져 있으면 Do Not Trigger가 아니라 위 Trigger("실패 응답이나 권한 조건이 빠졌는지 점검")가 우선한다(외부 검수 M-03, G-10).**
- 외부 공식 문서 확인이 필요한 최신 API를 추측으로 작성해야 하는 경우

---

## 3. Required Inputs

별도 AI Runtime의 API·RAG·Tool 연동 계약을 다루면 [AI Runtime Handoff](../../AI_RUNTIME_HANDOFF_TEMPLATE.md)로 양측 소유권·실패 계약·인증·검증 범위를 수집한다. `checklists/ai-runtime-integration-checklist.md`를 적용하며 누적 Gate는 `08.QUALITY_GATE.md §7-2`를 따른다. 일반 API 설계에는 이 추가 입력을 요구하지 않는다.

| 입력물 | 필요 이유 |
|---|---|
| `gates/api-gate.md` | API Gate 기준 확인 |
| `checklists/api-checklist.md` | 세부 확인 항목 검수 |
| 요구사항 또는 화면 흐름 | API가 해결할 사용자 흐름 확인 |

---

## 4. Procedure

1. 요구사항에서 리소스와 행위를 분리한다.
2. URL은 리소스 중심으로 정의한다.
3. HTTP Method를 선택하고 이유를 확인한다.
4. Path, Query, Body를 구분한다.
5. 성공 Response와 Error Response를 모두 정의한다.
6. Auth와 Permission 조건을 확인한다.
7. 이 명세의 상태를 `Candidate`(초안), `Confirmed`(확정), `Deprecated`(폐기/대체) 중 하나로 표시한다.
8. 상태 표시가 없더라도 구현 흔적이 있으면 `Confirmed` 여부를 먼저 확인한다.
9. `gates/api-gate.md`로 PASS/WARN/FAIL을 판정한다.

### 4-1. Candidate / Confirmed 표시 규칙

| 상태 | 의미 | 변경 시 처리 |
|---|---|---|
| Candidate | 아직 프론트/백엔드 구현에 쓰이지 않은 초안 | 자유롭게 수정 가능. 수정 시 사용자 확인 불필요 |
| Confirmed | 프론트 또는 백엔드가 이미 구현에 사용 중인 확정본 | 변경 시 영향 범위(프론트/백엔드 양쪽)를 확인하고, 범위가 넓으면 `04.GATEGUARD.md`의 구조 작업 기준에 따라 사용자 확인 |
| Deprecated | 더 이상 새 구현 기준으로 사용하지 않는 폐기/대체 명세 | 새 구현 기준으로 사용 금지. 대체 API 또는 폐기 사유를 함께 표시 |

명세 문서에 상태 표시가 없더라도 코드, 테스트, 화면, 서버 구현에서 사용 중인 흔적이 있으면 즉시 `Candidate`로 간주하지 않는다. 이 경우 `Confirmed` 여부를 먼저 확인하고, 불명확하면 `04.GATEGUARD.md`의 구조 작업 WARN 기준을 적용한다. `Confirmed` 명세를 근거 없이 `Candidate`처럼 가볍게 수정하지 않는다.

---

## 5. Quality Gate

| 판정 | 기준 |
|---|---|
| PASS | URL, Method, Request, Response, Error Response, Auth, Permission이 모두 정의되고 계약 상태(`Candidate`/`Confirmed`/`Deprecated`)가 명시됨 |
| WARN | 구현은 가능하지만 실패 응답 형식, 권한 조건, 프론트 필요 필드, 또는 계약 상태 표시 중 일부가 약함(`gates/api-gate.md` §1-1의 예외에 해당하지 않는 경우). 실패 응답이 아예 없으면 WARN이 아니라 FAIL이다 |
| FAIL | Request/Response/실패 응답이 없거나 인증/권한 기준이 없고, 프론트와 백엔드 연결 기준을 판단할 수 없음. 또는 `Confirmed` 명세를 영향 범위 확인 없이 수정함 |

---

## 6. Output Format

```md
## API Design 결과

- 사용 이유:
- 확인한 입력물:
- URL / Method:
- Request(Path/Query/Body):
- Response(성공):
- Error Response:
- Auth / Permission:
- 계약 상태(Candidate/Confirmed/Deprecated):
- 판단 결과:
- PASS/WARN/FAIL:
- 위험 WARN 여부:
- 다음 연결:
```

---

## 7. Handoff

다음 연결(Procedure 9단계에서 `gates/api-gate.md` 판정을 이미 마쳤다는 전제): `skills/error-handling/SKILL.md` → `skills/security-review/SKILL.md` → `06.REPORT_TEMPLATE.md`

---

## 8. Anti-Patterns

- URL을 동사 중심으로 과하게 설계하기
- 성공 응답만 정의하고 실패 응답을 빼기
- 인증 필요 여부와 권한 조건을 나중으로 미루기
- 프론트에서 필요한 필드를 확인하지 않고 Response를 확정하기
