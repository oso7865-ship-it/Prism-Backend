# PR 분석 실행과 정적 분석기

## 작업 계약
- 목표: 고정 PR snapshot 분석을 접수하고 취소/재분석·이력·파일 검사 범위·Finding을 실제 UI에서 조회한다.
- Goals: 영속 run+job, workspace 권한/연결 세대 검증, 동일 snapshot 멱등성, 별도 프로세스 parser, Java/Python/JS/TS 구문 기반 규칙, 원문 없는 결과 저장, PR 상세 분석 UI.
- Non-Goals: DeepSeek/자동 분석/Webhook 자동 접수, 타입·데이터 흐름·전체 저장소 분석, 저장소 코드 실행, 38개 제안 규칙 전부 활성화, 고객별 규칙 편집 UI, Git 게시/운영 배포/하네스 동기화.
- 근거: 사용자 1번 분석 실행 + 2번 정적 분석기 동시 구현 요청. 기존 Analysis Contracts/Pipeline/Results 스키마/ADR-ANALYSIS-001 준수. backend/frontend dev, architecture main 유지.
- 위험: 구조·DB·보안. 사용자 요청 범위 안의 3개 결과 테이블 추가(물리 FK 없음), 기존 공개 도메인 API 확장. 서버 권한 검증을 유지하고 GitHub 원문은 memory/pipe만 사용. 저장소 의존성 설치/코드 실행 금지.
- 스킬/Gate: planning, verification-loop, 기존 Vue UI 규칙. Security Gate/API Gate/DB Gate/UI Gate/Document Gate.

## 설계
분석 요청은 PR ID로 저장된 base/head SHA를 고정하고 설정/규칙/실행기 digest와 연결 세대를 execution_key에 넣는다. 일반 요청 generation0은 중복 반환, rerun_of는 이전 run을 검증한 뒤 같은 snapshot의 generation+1. workspace 잠금으로 생성/취소/완료 경합을 직렬화한다. Job lease/fence/heartbeat/attempt history를 재사용하고 취소·철회 뒤 늦은 결과는 저장하지 않는다. 기존 Workspace 계약에 따라 모든 멤버 분석 시작·조회, 요청자 본인 또는 OWNER/ADMIN 취소.

GitHub PR snapshot을 취득 전후 검사하고 고정 SHA contents의 regular file만 읽는다. 100파일/200KiB/파일/2MiB/run/120초 제한. patch 줄 범위를 확신하지 못하면 CONTEXT로 표시하며 새 결함이라고 단정하지 않는다. 삭제/바이너리/LFS/심볼릭 링크/미지원/크기/파싱 실패는 사유를 기록한다. Tree-sitter Python binding과 4개 grammar를 lockfile로 고정한다. parser는 비밀 환경을 제거한 프로세스에서 JSON pipe로 입력받아 5초 안에 종료하고 timeout/cancel 때 kill+reap한다. 전체 저장소 clone, dependency install, hook, shell 실행 없음.

초기 활성 규칙은 fixture로 검증 가능한 공통 파일 길이/함수 길이/인수 수/credential·private-key 형식 및 각 언어의 명시적 구문 규칙으로 제한한다. 미구현 제안은 활성화하지 않으며 버전/활성 목록/제한을 문서화한다. Secret 결과는 위치/고정 메시지만 저장한다. 파일별 cap100과 parser 실패·미평가 규칙은 coverage에 반영한다.

## 체크리스트와 검증
- [x] 결과 ORM 3개/0005 migration/공개 snapshot·config API; migration 왕복·drift·FK0 검사
- [x] 접수/상태/이력/files/findings/cancel API; 멱등성·권한·테넌트·rerun 검증
- [x] 고정 SHA GitHub 취득/제한/parser 프로세스; snapshot 변경·경로·크기·시간·원문 비저장 검증
- [x] 활성 규칙/버전/5개 이상 fixture(정상2·위반2·유사정상1)/언어 확장자·구문 실패 검증
- [x] worker retry/fence/cancel/연결 철회/원자적 완료 테스트
- [x] PR 상세 분석 UI/상태·coverage·결과·재시도/빌드·타입 검사·회귀
- [x] 실제 조직 PR 분석·결과 화면 확인(원본 저장소 쓰기 없음)
- [x] 설계 구현 현황/README/Report/최신 포인터/작업 기록

검증 결과와 미해결 Windows 진단은 [Report](../../reports/2026-09-26_static-analysis_report.md)에 기록했다. 전체134 tests 이후 parser 취소 회귀1개 추가, 해당 suite42 tests PASS. 실제 조직 PR #47 최초/재분석 완료.
