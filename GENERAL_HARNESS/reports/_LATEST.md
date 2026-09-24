# Reports Latest Pointer

> 목적: 같은 날짜 Report가 여러 개 있을 때 현재 판단 기준 Report를 명시한다.
> 구조: "하네스 유지보수"와 "부착 프로젝트"는 서로 다른 이력이므로 최신 포인터를 분리해서 관리한다(ADR-041). 한쪽 갱신이 다른 쪽을 superseded로 만들지 않는다.

## 현재 최신 Report

| 이력 | 최신 판단 기준 | 기준 |
|---|---|---|
| 하네스 유지보수 최신 | `reports/2026-09-22_1524_flow-full-height-rule_report.md` | 긴 차트는 내부 세로 스크롤 없이 SVG 전체 높이로 펼치는 규칙으로 변경. 하네스 변경을 origin/codex/harness-skill-reinforcement에 공유, PR·병합 전. 활성 20개 |
| 부착 프로젝트 최신 | [프로젝트 Report](../../reports/2026-09-25_foundation_report.md) | 프로젝트 Report는 프로젝트 폴더에 남고, 하네스 규칙의 공백이 드러난 경우 요약만 하네스 유지보수 Report로 환류한다 |

> 주의: 이전 Report는 과거 의사결정 근거와 변경 증거로만 사용한다. Next Work 판단은 이 파일과 `05.WORKING_CONTEXT.md`를 우선한다.

## 읽기 순서

1. `reports/_LATEST.md`
2. 위 표의 최신 Report
3. `05.WORKING_CONTEXT.md`
4. 필요한 경우 superseded Report를 증거로 확인(원본이 `reports/archive/HISTORY_DIGEST.md`의 삭제 이벤트(`PURGE_EVENT`)에 포함되어 있으면 원본 대신 digest 요약으로 확인 — 외부 검수 M-08/X-09)
