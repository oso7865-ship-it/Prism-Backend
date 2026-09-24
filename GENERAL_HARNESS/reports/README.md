# Reports README

> 목적: Report 누적 시 최신성 판단과 보존 기준을 고정한다.

## 1. 최신 Report 판단 순서

1. `reports/_LATEST.md`에 명시된 Report
2. 파일명에 시간이 있으면 가장 늦은 시간
3. superseded note가 없는 최신 유지보수 Report
4. 판단 불가 시 사용자 또는 maintainer 확인

## 2. 보존 기준

| Report 유형 | 처리 |
|---|---|
| 최신 Report | 현재 Next Work 판단 기준 |
| Superseded Report | 과거 의사결정 근거와 변경 증거로 보관 |
| 오래된 Report | 삭제보다 Working Context 요약 후 증거 보관 우선. **단, 사용자가 명시적으로 요청하면 `06.REPORT_TEMPLATE.md §8`의 예외 절차(요약 선행 보존 + 삭제 이벤트 기록)로 원본을 삭제할 수 있다 — 그 경우 `reports/archive/HISTORY_DIGEST.md`의 삭제 이벤트(`PURGE_EVENT` 블록)가 유일한 근거가 된다(외부 검수 M-08/X-09, ADR-031/034).** |

## 3. Superseded 원칙

새 Report가 이전 Report의 다음 작업이나 상태 판단을 대체하면, 이전 Report 상단에 `Superseded note`를 추가한다.

## 4. 성적표 집계 (환류용)

프로젝트 마무리 또는 skill-stocktake 시점에 `scripts/harness-stats.mjs`를 실행해 Report 헤더를 집계한다.

```txt
node scripts/harness-stats.mjs                   # 이 폴더(reports/) 집계
node scripts/harness-stats.mjs --dir <경로>       # 부착 프로젝트의 reports/ 집계
node scripts/harness-stats.mjs --include-archive # archive 포함
```

출력: 규모 분포, 스킬 발동 빈도(미등록 스킬명 탐지), Gate 분포, 위험도–Gate 불일치, Git 기록 문제, L/XL의 planning 발동률, 3회 이상 반복된 미해결 항목(프로젝트 상수 후보). **통계이며 판정이 아니다** — 결과 해석과 처리 판단은 `skills/skill-stocktake/SKILL.md`와 `06.REPORT_TEMPLATE.md §5-2`를 따르고, 환류 Report(ADR-041 경로)에 출력을 첨부한다.
