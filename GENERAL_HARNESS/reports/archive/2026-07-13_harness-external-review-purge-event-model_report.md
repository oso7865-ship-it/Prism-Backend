# 작업 리포트: harness-external-review-2026-07-13-purge-event-model

> Superseded note:
> 이 보고서의 다음 작업 판단은 `reports/_LATEST.md`가 가리키는 최신 Report로 대체되었다.
> 과거 의사결정 근거로는 유효하지만, 현재 Next Work 판단은 최신 Report와 `05.WORKING_CONTEXT.md`를 우선한다.

> 작성일: 2026-07-13
> 작업 범위: XL (삭제 이벤트 모델 재설계, 트랜잭션·Gate 라우팅·Checklist 잔여 정합화)
> 적용 스킬: `report-consistency`, `quality-gate`, `verification-loop`(회귀 테스트 실행)
> 적용 Gate: Document Gate, Skill Gate
> 위험 작업 여부: 예 (삭제 승인 모델·게시 트랜잭션·Gate 판정 매트릭스 변경. 사용자가 "수정작업 진행해줘"로 명시적 확인함)

이 Report에는 "게시 상태" 필드를 두지 않는다(D-028). 이 Report 작성 시점의 사전 검증은 45개 markdown 기준이었다 — 이 Report 자신을 포함한 최종 개수는 게시 후 확인해 다음 메시지로 전달한다(M-09 재발 방지, 아래 §1 참고).

---

## 0. 작업 범위 확인

| 항목 | 내용 |
|---|---|
| 요청 요약 | 일곱 번째 외부 검수(재검수, 53개 파일 독립 대조, Critical 0건)의 Major 9건, Minor 5건 전부 반영 |
| 수정 대상 | `reports/archive/HISTORY_DIGEST.md`(삭제 이벤트 모델 도입), `scripts/validate-report-consistency.mjs`(이벤트 기반 검증 전면 재작성), `skills/report-consistency/SKILL.md`, `06.REPORT_TEMPLATE.md`(§8-1 retained/purged 명시, §8-2 초안 롤백·188행 정정, §8-3 첫 전환 분기), `08.QUALITY_GATE.md`(노드명 정정, 죽은 참조 제거, Verification 누적 규칙, 흐름도 표기), `gates/security-gate.md`(외부연동 확인 축 분리), `gates/db-gate.md`(Index 분리), `checklists/release-checklist.md`, `checklists/payment-red-blue-checklist.md`(로컬 1:1 재정렬), `checklists/*.md`(5개, 필드명 정정), `05.WORKING_CONTEXT.md`(retained/purged 반영), `_SOURCE_MAPPING.md`(5·6차 통계 정정), `10.ADR.md`(ADR-034, ADR-033 부분대체) |
| 제외 대상 | 없음 |
| 검증 방법 | 게시 전 6개 스크립트 실행. 삭제 이벤트 모델을 5가지 시나리오(정상/정상 2차삭제/자기승인 시도/가짜ADR 인용/중복 event_id)로 직접 재현 테스트 |
| 한계 | 삭제 이벤트 불변성은 파일 기반 시스템의 구조적 한계상 완전히 강제할 수 없다(누구든 과거 이벤트 블록을 고칠 쓰기 권한은 있음) — 다만 "그냥 숫자 하나 바꾸기"보다 "새 불변 이벤트를 명시적으로 추가하기"를 훨씬 눈에 띄는 행위로 만들었다 |

---

## 1. 삭제 이벤트 모델 — 가장 중요한 수정 (M-06/X-06/G-06)

**재현한 문제**: 지난 라운드의 "명시적 목록"(PURGED_FILES) 방식도, 실제 파일을 지우고 목록에 추가하고 삭제 로그의 누계 count를 일관되게(30→31) 함께 바꾸면 새로운 승인 증거 없이 조용히 PASS했다. 반대로 정상적인 두 번째 삭제 이벤트(진짜 승인받고 1개 더 지움)를 시도하면, 단일 누계 count 하나뿐이라 옛 count(30)와 새 목록 길이(31)가 안 맞아 오히려 FAIL했다.

**수정**: 삭제를 "이벤트"로 구조화했다. `HISTORY_DIGEST.md`에 `PURGE_EVENT`(각각 `event_id`/`date`/`approval`/`count`를 헤더에 갖는 독립 블록)를 도입했다. 이벤트는 추가만 하고 기존 이벤트는 고치지 않는다. `scripts/validate-report-consistency.mjs`가 각 이벤트를 독립적으로 검증한다: event_id 전체 유일성, count와 실제 파일 목록 길이 일치, `approval`이 `10.ADR.md`에 실제로 존재하는 ADR인지, 목록의 파일이 digest 표에 실제로 있는지, archive에 실제로 없는지.

**재현 테스트 5건**:

| 시나리오 | 결과 |
|---|---|
| 정상 상태 | PASS |
| 정상적인 2차 삭제(실제 파일 삭제 + 새 이벤트, 실재 ADR-033 인용) | **PASS**(예전엔 FAIL했던 케이스) |
| 자기승인 시도(파일은 안 지우고 이벤트만 추가) | **FAIL**(물리적으로 존재한다고 정확히 지적) |
| 존재하지 않는 ADR-9999를 근거로 인용 | **FAIL** |
| event_id 중복 | **FAIL** |

---

## 2. Major 9건 처리 요약

| 번호 | 문제 | 수정 내용 |
|---|---|---|
| M-01 | 미게시 초안이 롤백 대상에 없음 | §8-2 3번에 초안 파일 롤백/격리 문구 추가 |
| M-02 | §8-2:188이 여전히 "작성+포인터"로 단순화, 첫 프로젝트 전환 미정의 | 188행을 §8-3 참조로 교체, §8-3에 "이전 _LATEST가 하네스 Report면 그대로 둔다" 분기 추가 |
| M-03 | 비민감 경로가 외부연동 확인을 건너뜀, 계약 Gate에 Verification 강제 없음 | security-gate 흐름도에서 비민감 경로도 외부연동 확인(H)을 거치도록 수정, §7-2에 "실제 코드 있으면 Verification 항상 누적" 규칙 추가 |
| M-04 | DB Index가 필수 항목이면서 PASS 필수 아님(모순) | Index를 §1(필수 항목)에서 분리해 §1-1(권장 항목)로 이동 |
| M-05 | Release 비밀값 분리, Payment 로그의 §2/결과요약 불일치 | Release §2 FAIL 목록에 비밀값 분리 반영, Payment PASS에 로그 기록 명시 |
| M-06 | PURGED_FILES 단일 목록도 자기승인·다중 이벤트 실패 | §1의 삭제 이벤트 모델로 근본 재설계(5가지 테스트 완료) |
| M-07 | §8-1 자체가 "이동만, 삭제 없음" 단정 | §8-1, `05.WORKING_CONTEXT.md §4`를 retained/purged 두 상태로 재서술 |
| M-08 | Source Mapping의 5·6차 검수 통계가 서로 뒤바뀜 | 실제 라운드별 정확한 수치(5차: C4/M8/m7, 6차: C0/M10/m5)로 정정 |
| M-09 | 직전 Report의 44/45 수치 차이가 정정 후에도 반복 | 이 Report §0/헤더에서 "정확한 사전 수치만 기록하고 최종 수치는 채팅에서 확인"으로 순서 자체를 재확인 |

---

## 3. Minor 5건 처리 요약

| 번호 | 문제 | 수정 내용 |
|---|---|---|
| m-01 | 검증기 개수 "6개" 하드코딩 잔여 | §8-2 3번의 "6개 중"을 "위 스크립트 전체 중"으로 교체 |
| m-02 | Quality Gate 흐름도 B/M 노드명 불일치, 존재하지 않는 §7 표 참조, "최종 판정" 용어 혼용 | 노드명 M으로 정정, 죽은 표 참조를 §7-2 매트릭스 참조로 교체, 4번을 "Gate 집계 판정"으로 재명명 |
| m-03 | Payment Checklist 로그의 PASS/WARN 경계 겹침 | PASS에 로그 기록 명시, WARN을 "일부만" 경우로 한정 |
| m-04 | Checklist 필드명이 여전히 "최종 판정" | 5개 Checklist 전부 "Checklist 판정(전체 최종 판정 아님)"으로 교체 |
| m-05 | report-consistency 단독 PASS 문구가 실제 범위보다 강함 | PASS 문구를 "no UNEXPLAINED orphan rows"로 정확화, archive 디렉터리 부재 시 이 섹션이 스킵됨을 명시 |

---

## 4. 게시 전 검증 (6개, validate-package 제외)

```txt
PASS validate-harness
PASS validate-docs (45 markdown files checked)
PASS validate-skills (12 skills checked)
PASS validate-no-personal-paths
PASS validate-references (path + section references resolve)
PASS validate-report-consistency (PURGE_EVENT 구조적 검증 통과, 5가지 시나리오 테스트 완료)
```

전부 PASS이므로 게시를 진행한다.

---

## 5. 알려진 한계 (정직하게 남김)

- 삭제 이벤트 불변성은 파일 기반 시스템의 근본 한계상 암호학적으로 강제되지 않는다.
- `_SOURCE_MAPPING.md`의 부분 참조 검사(제외 문서에서도 `reports/` 패턴만 선택 검사)는 여전히 구현하지 않았다.
- `01.SKILL_TEMPLATE.md`와 실제 12개 스킬의 자동 동기화 검사도 여전히 없다.

---

## 6. 다음 작업

없음.
