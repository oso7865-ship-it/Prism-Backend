# 작업 리포트: harness-archive-purge-decision

> Superseded note:
> 이 보고서의 다음 작업 판단은 `reports/_LATEST.md`가 가리키는 최신 Report로 대체되었다.
> 과거 의사결정 근거로는 유효하지만, 현재 Next Work 판단은 최신 Report와 `05.WORKING_CONTEXT.md`를 우선한다.

> 작성일: 2026-07-12
> 작업 범위: L (archive 원본 30개 삭제, 관련 참조·검증 로직 정합화)
> 적용 스킬: `report-consistency`
> 적용 Gate: Document Gate
> 위험 작업 여부: 예 — **파일 삭제(`04.GATEGUARD.md §6-1`의 파일 손상 가능 작업, 예외 없이 실시간 확인 필요). 사용자가 "요약만 남기고 원본은 지울려고"로 명시적 확인함**

이 Report에는 "게시 상태" 필드를 두지 않는다(D-028).

---

## 0. 작업 범위 확인

| 항목 | 내용 |
|---|---|
| 요청 요약 | §12 마지막 결정 사항("archive Report 16개의 옛 경로를 그대로 둘지, 보정할지")에 대해 사용자가 원래 제시된 두 선택지 대신 "원본을 아예 삭제하고 요약만 남긴다"는 제3의 결정을 내림. 삭제 전 실제 영향을 먼저 테스트해 사용자에게 알린 뒤 진행 |
| 수정 대상 | `reports/archive/*.md`(30개 삭제, `HISTORY_DIGEST.md`만 유지), `reports/archive/HISTORY_DIGEST.md`(삭제 로그 신설), `_WORKING_CONTEXT_HISTORY.md`(깨진 링크 1건 수정), `_SOURCE_MAPPING.md`(깨진 링크 2건 수정), `06.REPORT_TEMPLATE.md`(보관 원칙에 삭제 예외 경로 추가), `09.AGENT_WORKFLOW.md`(기본 원칙에 예외 참조 추가), `scripts/validate-report-consistency.mjs`(고아 행 검사를 삭제 로그 cutoff 인지형으로 개선), `10.ADR.md`(ADR-031), `_WORKING_CONTEXT_HISTORY.md`(D-030), `_PENDING_IMPORT_LIST.md`(ADR 개수 갱신) |
| 제외 대상 | 없음 |
| 검증 방법 | 삭제 **전에** 임시 복제본으로 실제 영향(어떤 스크립트가 FAIL/WARN으로 바뀌는지)을 먼저 테스트해 사용자에게 알렸다. 삭제 후 새 cutoff 로직을 정상/회귀 두 경우로 테스트했다(과거 항목은 경고 안 함, 삭제 로그 이후 날짜의 새 고아는 여전히 경고함) |
| 한계 | 삭제된 30개 Report의 상세 근거·검증 로그는 이제 `HISTORY_DIGEST.md`의 한 줄 요약으로만 남는다. 더 깊은 맥락이 필요한 과거 판단은 재현할 수 없다 |

---

## 1. 결정 내용

archive Report 30개(2026-07-12 기준 전부)의 원본을 삭제하고 `reports/archive/HISTORY_DIGEST.md`만 유지한다. 삭제 사실은 `HISTORY_DIGEST.md`의 "삭제 로그" 표에 날짜·대상·사유·근거와 함께 기록한다.

**"오래된 Report는 삭제하지 않는다"는 기존 기본 원칙 자체는 유지한다** — 이번 결정은 그 원칙에 대한 예외를 만든 것이다: 사용자가 명시적으로 요청하면 "요약 선행 보존 + 삭제 로그 기록" 조건으로 삭제할 수 있다.

---

## 2. 삭제 전 실측한 영향 (사용자에게 사전 안내)

| 스크립트 | 삭제 전 | 삭제만 하고 아무것도 안 고칠 경우 |
|---|---|---|
| `validate-report-consistency.mjs` | PASS | WARN(고아 행 30개) |
| `validate-references.mjs` | PASS | **FAIL**(`_WORKING_CONTEXT_HISTORY.md`의 직접 링크 1건이 깨짐 — 게시 차단) |

이 실측 결과를 사용자에게 먼저 알린 뒤 "그래도 지우겠다"는 확인을 받고 진행했다.

---

## 3. 수정 내역

1. `reports/archive/HISTORY_DIGEST.md` 상단에 "삭제 로그" 섹션 신설(삭제일 2026-07-12, 대상 30개, 사유, 근거 ADR-031).
2. archive 안의 Report 원본 30개 삭제(`HISTORY_DIGEST.md` 제외).
3. 깨졌던 직접 링크 3건을 수정 — `_WORKING_CONTEXT_HISTORY.md` 1건, `_SOURCE_MAPPING.md` 2건. 전부 "원본은 삭제됨, `HISTORY_DIGEST.md` 참고" 형태로 정리.
4. `06.REPORT_TEMPLATE.md`의 보관 원칙에 "삭제 가능 조건"을 명시(요약 선행 보존 + 삭제 로그 + 실시간 사용자 확인).
5. `09.AGENT_WORKFLOW.md`의 "삭제하지 않는다" 기본 문장에 예외 경로 참조를 추가.
6. `scripts/validate-report-consistency.mjs`의 고아 행 검사를 "삭제 로그" 표의 cutoff 날짜 인지형으로 개선 — cutoff 이전 항목은 고아여도 경고하지 않고, 그 이후 항목만 검사한다. 정상 케이스(PASS)와 회귀 케이스(cutoff 이후 가짜 항목 추가 시 WARN 발생 확인 후 원복)를 모두 테스트했다.
7. `10.ADR.md`에 ADR-031, `_WORKING_CONTEXT_HISTORY.md`에 D-030을 기록.
8. `_PENDING_IMPORT_LIST.md`의 ADR 개수를 31개로 갱신 — 재검토 기준선(30개)을 넘겨서 다음 하네스 자체 수정 라운드에서 `validate-adr-unique.mjs` 도입 여부를 실제로 판단하기로 명시.

---

## 4. 게시 전 검증 (6개, validate-package 제외)

```txt
PASS validate-harness
PASS validate-docs (42 markdown files checked — 72에서 30개 감소)
PASS validate-skills (12 skills checked)
PASS validate-no-personal-paths
PASS validate-references (path + section references resolve, 깨졌던 링크 3건 수정 확인)
PASS validate-report-consistency (archive digest complete, 고아 행 경고 없음 — cutoff 로직 정상 동작)
```

전부 PASS이므로 게시를 진행한다.

---

## 5. §12 결정 사항 최종 정리

세 번째 검수부터 이어져 온 §12의 사용자 확인 사항 5건이 전부 마무리됐다:

1. 배포 SoT = ZIP (ADR-027)
2. 최종 검증은 채팅에 기록 (ADR-027, 이후 D-028로 더 근본적으로 재설계)
3. 결제 복합 Gate 동의 (ADR-027)
4. 외부 근거 비보존 유지 (ADR-026)
5. `05.WORKING_CONTEXT.md` 신규 템플릿 전환 (ADR-027)

그리고 이번 다섯 번째 검수의 §12에서 새로 생긴 2건도 마무리:

6. 배포 모델 = 템플릿 복제 (ADR-030)
7. archive 원본 = 삭제 + 요약 보존 (ADR-031, 원래 제시된 두 선택지 대신 제3의 결정)

---

## 6. 다음 작업

없음. 외부 검수 다섯 라운드(2026-07-10~12)와 그 사이 사용자 결정 사항 전부 반영 완료.
