# 작업 리포트: Git-first 운영 및 AGENTS 표준화

> Superseded note:  
> 이 보고서의 다음 작업 판단은 `reports/_LATEST.md`가 가리키는 최신 Report로 대체되었다.  
> 과거 의사결정 근거로는 유효하지만, 현재 Next Work 판단은 최신 Report와 `05.WORKING_CONTEXT.md`를 우선한다.

> 작성일: 2026-07-21  
> 작업 범위: L  
> 적용 스킬: `git-workflow`, `report-consistency`, `quality-gate`  
> 적용 Gate: Quality Gate  
> 위험도: 구조

## 0. 작업 범위 확인

| 항목 | 내용 |
|---|---|
| 요청 요약 | ZIP 없이 Git으로 운영하고, `main` 병합만 공식 반영으로 정한다. 기존 단수형 진입 문서를 `AGENTS.md`로 표준화하고 제거한다. |
| 수정 대상 | 루트 진입 문서, Git/Report/Quality/Workflow 규칙, ADR·이력·보류 목록 |
| 제외 대상 | 과거 archive Report와 과거 ZIP 관련 ADR의 역사 내용 변경, ZIP export 검증 스크립트 삭제 |
| 근거 | 사용자 결정, 하네스 규칙·Report 템플릿·Quality Gate·Agent Workflow 문서 |
| 검증 방법 | 하네스 검증 스크립트, Markdown 참조 검색, Git diff 수동 검수 |

## 1. 작업 요약

- Git 저장소를 배포·이력 Source of Truth로 전환했다.
- 작업 브랜치 push는 공유 진행 상태, `main` 병합만 공식 반영으로 정의했다.
- 루트 진입 파일을 `AGENTS.md`로 표준화하고 기존 단수형 문서를 제거했다.
- `CLAUDE.md`와 `AGENTS.md`는 자동 검증에서 제외하고, 변경 시 수동 검수하도록 명시했다.
- ZIP 검증기는 삭제하지 않고 사용자가 export를 요청할 때만 적용하도록 축소했다.

## 2. 변경 파일

| 파일 | 변경 내용 | 이유 |
|---|---|---|
| `AGENTS.md` | 최소 진입 지도 신설 | 표준 파일명과 얇은 지도형 정책 적용 |
| 기존 단수형 진입 문서 | 제거 | 단일 진입점 유지 |
| 하네스 규칙 | Git 공식 반영 정책과 선택적 export 검증 | Git-only 운영 반영 |
| Report 템플릿 | Git 기반 Report 완료 트랜잭션 | ZIP 중심 완료 흐름 제거 |
| Quality Gate | package 검증을 선택적 export로 한정 | 일반 Git 작업의 과도한 FAIL 방지 |
| Agent Workflow | Git 기반 템플릿 부착 흐름 | ZIP 복제 모델 대체 |
| ADR-039 | 구조 결정 근거 보존 | Git-first 전환의 결정 기록 |

## 3. 검증 결과

| 검증 항목 | 결과 | 비고 |
|---|---|---|
| 하네스 구조·스킬·문서·참조 검증 | PASS | 선택적 ZIP 검증은 요청되지 않아 제외 |
| 최신성 검증 | PASS | 이전 최신 Report에 superseded note를 추가 |
| 제거된 단수형 파일명 참조 검색 | PASS | archive와 사용자 전용 초안은 제외한 현재 문서 기준 |
| Git diff 수동 검수 | PASS | 진입 문서·공식 반영 기준 확인 |

## 4. 남은 작업

- 사용자가 요청할 때만 커밋·push하며, `main` 병합 전에는 공식 반영으로 보고하지 않는다.
