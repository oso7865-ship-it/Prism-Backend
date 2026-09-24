# 작업 리포트: harness-orphan-check-explicit-list-fix

> Superseded note:
> 이 보고서의 다음 작업 판단은 `reports/_LATEST.md`가 가리키는 최신 Report로 대체되었다.
> 과거 의사결정 근거로는 유효하지만, 현재 Next Work 판단은 최신 Report와 `05.WORKING_CONTEXT.md`를 우선한다.

> 작성일: 2026-07-12
> 작업 범위: M (검증 스크립트 로직 재작성, HISTORY_DIGEST 구조 변경)
> 적용 스킬: `report-consistency`
> 적용 Gate: Document Gate
> 위험 작업 여부: 예 (검증 스크립트 핵심 로직 변경. 별도 사용자 확인 없이 진행 — 지난 라운드에 스스로 남긴 "알려진 한계"를 실제로 재현·검증해 고치는 후속 작업이라 위험도가 낮다고 판단)

이 Report에는 "게시 상태" 필드를 두지 않는다(D-028).

---

## 0. 작업 범위 확인

| 항목 | 내용 |
|---|---|
| 요청 요약 | 별도 첨부 없이 (1) 제 이전 Report 원본, (2) 삭제 로그의 날짜 cutoff 방식이 실제로 실패하는 것을 보여주는 조작된 `HISTORY_DIGEST.md`(같은 날짜의 가짜 고아 행 1개 추가)를 전달받음. 실제로 재현되는지 확인하고 근본 수정 |
| 수정 대상 | `reports/archive/HISTORY_DIGEST.md`(삭제 로그를 명시적 파일 목록 방식으로 재구성), `scripts/validate-report-consistency.mjs`(고아 행 검사 로직 재작성), `10.ADR.md`(ADR-032, ADR-031 부분대체 표기), `_WORKING_CONTEXT_HISTORY.md`(D-031), `_PENDING_IMPORT_LIST.md`(ADR 개수 32개로 갱신) |
| 제외 대상 | 없음 |
| 검증 방법 | 조작된 digest(가짜 고아 행 포함)를 실제로 적용해 기존 로직의 실패를 먼저 재현 확인 → 수정 → 같은 조작본으로 재현 테스트해 이번엔 WARN이 뜨는지 확인 → 정상 상태로 되돌려 PASS 확인 |
| 한계 | 새로운 삭제가 생길 때마다 PURGED_FILES 목록에 파일명을 수동으로 추가해야 한다 — 이 목록 자체가 갱신을 빠뜨리면(또 다른 "자기 참조 갱신 누락" 사례가 될 수 있음) 여전히 놓칠 수 있다. 다만 최소한 "날짜라는 뭉뚱그려진 정보로 추정하는" 것보다는 훨씬 명확하다 |

---

## 1. 재현 확인

전달받은 조작된 `HISTORY_DIGEST.md`(같은 날짜에 실제로 없는 파일 `2026-07-12_same-day-missing-probe_report.md`를 가리키는 행 1개 추가)를 그대로 적용해 `validate-report-consistency.mjs`를 실행한 결과:

```txt
PASS validate-report-consistency: ... no orphan rows ...
```

**실제로 재현됨** — 지난 라운드에 "알려진 한계"로만 남겨뒀던 문제가 진짜로 통과되는 것을 확인했다. 원인은 `dateMatch[1] > purgeCutoff`(엄격한 초과 비교)라서, 삭제일과 같은 날짜는 "이전"으로 취급돼 검사 대상에서 빠졌기 때문이다.

---

## 2. 수정 내용

`HISTORY_DIGEST.md`의 삭제 로그를 날짜 기반 추정에서 **명시적 파일 목록** 방식으로 전면 교체했다. `<!-- PURGED_FILES_START -->` ~ `<!-- PURGED_FILES_END -->` 사이에 실제로 삭제된 30개 파일명을 전부 나열한다. `scripts/validate-report-consistency.mjs`는 이제 이 목록에 있는 파일명만 "삭제 확인됨"으로 인정하고, 목록에 없는 고아 행은 날짜와 무관하게 전부 경고한다.

---

## 3. 수정 후 재테스트

| 상태 | 결과 |
|---|---|
| 정상 상태(조작 없음) | PASS |
| 조작된 상태(같은 날짜 가짜 고아 행 추가) | **WARN** — `HISTORY_DIGEST.md references 1 file(s) not present in reports/archive/ and not listed in PURGED_FILES: 2026-07-12_same-day-missing-probe_report.md` |
| 조작본 원복 후 재확인 | PASS |

수정 전에는 조작된 상태에서도 PASS가 나왔고, 수정 후에는 정확히 그 항목을 짚어 WARN이 뜬다.

---

## 4. 기록

- `10.ADR.md` ADR-031의 상태를 `Partially superseded by ADR-032`로 갱신(날짜 cutoff 부분만 대체, 삭제 결정 자체는 유효).
- `10.ADR.md`에 ADR-032 추가, `_WORKING_CONTEXT_HISTORY.md`에 D-031 추가: "자기 참조 검증 로직에서 날짜처럼 뭉뚱그려진 정보로 추정하지 않고, 명시적 식별자 목록으로 대조한다."
- `_PENDING_IMPORT_LIST.md`의 ADR 개수를 32개로 갱신(재검토 기준선 30개를 이미 넘김).

---

## 5. 게시 전 검증 (6개, validate-package 제외)

```txt
PASS validate-harness
PASS validate-docs (43 markdown files checked)
PASS validate-skills (12 skills checked)
PASS validate-no-personal-paths
PASS validate-references (path + section references resolve)
PASS validate-report-consistency (PURGED_FILES 방식으로 정상 동작 확인)
```

전부 PASS이므로 게시를 진행한다.

---

## 6. Working Context 반영 여부

- 반영 필요: 예(ADR/D-log에 반영 완료, `05.WORKING_CONTEXT.md`는 프로젝트 전용이라 추가 반영 없음)

---

## 7. 다음 작업

없음. 다만 PURGED_FILES 목록 자체를 향후 라운드에서 빠짐없이 갱신하는지는 계속 지켜봐야 한다.
