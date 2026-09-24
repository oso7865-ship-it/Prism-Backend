# 작업 리포트: 성적표 집계 스크립트(harness-stats) 추가

> Superseded note:  
> 이 보고서의 다음 작업 판단은 `reports/_LATEST.md`가 가리키는 최신 Report로 대체되었다.  
> 과거 의사결정 근거로는 유효하지만, 현재 Next Work 판단은 최신 Report와 `05.WORKING_CONTEXT.md`를 우선한다.

> 작성일: 2026-08-03  
> 패키징/배포일: 해당 없음  
> 작업 브랜치: `harness-stats-260803`  
> 커밋/PR: `7028340`(본 작업), 헤더 갱신 후속 커밋 1건  
> 작업 범위: M  
> 적용 스킬: `terminal-ops`, `verification-loop`, `report-consistency`  
> 적용 Gate: `gates/document-gate.md`  
> 위험도: 구조(스크립트 추가)  
> 위험 작업 여부: 예(사용자의 명시 요청 "만들어줘"가 근거)

---

## 0. 작업 범위 확인

| 항목 | 내용 |
|---|---|
| 요청 요약 | 하네스 평가에서 권고한 "성적표"(측정 자동화)를 스크립트로 구현한다. 하네스 동결 권고의 명시적 예외 항목 |
| 수정 대상 | `scripts/harness-stats.mjs`(신규), `scripts/validate-harness.mjs`(필수 목록), `reports/README.md §4`(사용 안내), `_PENDING_IMPORT_LIST.md §6-1`(반영 상태) |
| 제외 대상 | CI 차단 목록 편입(통계 도구는 판정 도구가 아님), 스킬/Gate 신설 |
| 근거 | 챱챱 환류 분석을 사람이 20~30분 수동 수행했던 것의 자동화. skill-stocktake와 환류(ADR-041)를 데이터 기반으로 전환 |
| 적용 스킬/Gate | 헤더와 동일 |
| 위험도 | 구조 |
| 검증 방법 | 하네스 자체 Report 실데이터로 2개 모드 실행 확인 + 검증 스크립트 7종 |
| 한계 | 헤더 표기가 자유 서식이면 집계 정확도가 떨어짐(예: Gate 이름의 서식 불일치는 분포로만 노출). "적용 스킬" 표기 없이 참조만 한 경우는 집계되지 않음(챱챱 분석 문서의 알려진 한계와 동일) |

## 1. 작업 요약

- `harness-stats.mjs`: `reports/`의 Report 헤더를 집계해 규모 분포, 스킬 발동 빈도(미등록 스킬명 ⚠), Gate 분포, 위험도–Gate 불일치(P-09형), Git 기록 문제(P-01형), L/XL의 planning 발동률(P-05형), 3회 이상 반복 미해결 항목(P-06형, 프로젝트 상수 후보)을 출력한다. `--dir`로 부착 프로젝트 집계, `--include-archive` 지원. 항상 exit 0(통계 전용).
- 실데이터 검증: 하네스 자체 Report 17건(archive 포함)에서 구 템플릿의 Git 기록 부재 14건과 "L/XL 중 planning 2/7"을 정확히 탐지 — 챱챱에서 수동으로 찾았던 유형의 문제를 자동으로 재현했다.

## 2. 변경 파일

| 파일 | 변경 내용 | 이유 |
|---|---|---|
| `scripts/harness-stats.mjs`(신규) | 성적표 집계 | 측정 자동화 |
| `scripts/validate-harness.mjs` | 필수 목록에 추가 | 부착 시 누락 방지 |
| `reports/README.md §4` | 사용 안내 | 환류 시점 실행 절차 |
| `_PENDING_IMPORT_LIST.md §6-1` | 반영 완료 행 | 상태 추적 |

## 3. 검증 결과

| 검증 항목 | 결과 | 비고 |
|---|---|---|
| `--include-archive` 실행(17건) | PASS | 구 템플릿 Git 누락 14건, planning 2/7 탐지 확인 |
| 기본 실행(최신 1건) | PASS | 신 템플릿에서 ⚠ 0건 확인 |
| 검증 스크립트 7종 | PASS | 이 Report 게시 후 재실행 기준 |

## 4. Checklist 결과

| Checklist | 결과 | Report 반영 |
|---|---|---|
| 해당 없음 | — | 스크립트·문서 작업, `gates/document-gate.md` 기준 판정 |

## 5. 발견된 문제

| 심각도 | 문제 | 처리 |
|---|---|---|
| Minor | 하네스 자체 이력에서도 L/XL 중 planning 발동 2/7 — 챱챱과 같은 패턴 | stocktake 관찰 항목으로 기록(스크립트가 이후 자동 감시) |

## 6. 미해결 항목

- Gate 이름 표기가 서식 불일치("Document Gate" vs 백틱 경로) — 집계 분포로 노출되며, 강제 통일은 하네스 동결 원칙에 따라 실전 불편이 확인될 때 처리
- 챱챱 폴더 측 이월 작업(변동 없음)

## 7. Working Context 반영 여부

- 반영 필요: 아니오(템플릿 기본값 설명은 부착 프로젝트 기입 사항)

## 8. 다음 작업

1. PR CI 통과 → `main` 병합
2. **하네스 동결 시작** — 다음 실프로젝트 부착 전까지, 실전 사고 기반이 아닌 하네스 수정 금지(평가 권고 1번)
3. 다음 프로젝트 마무리 시 `harness-stats.mjs` 출력을 환류 Report에 첨부해 챱챱 기준선(재작업 1건, planning 0/7, 미등록 스킬명 5회, WARN 반복 8/10)과 비교
