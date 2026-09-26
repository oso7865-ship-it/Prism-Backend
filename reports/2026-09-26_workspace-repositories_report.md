# 작업 리포트: 팀·저장소 연결

> 작성일: 2026-09-26
> 작업 브랜치: dev
> 커밋/PR: 미커밋
> 상태 기록 버전: 1
> 상태 확인 시각: 2026-09-26T02:14:16+09:00
> 구현 상태: 완료
> 구현 근거: 사용자 1번 묶음 구현 요청
> 로컬 검증 상태: 완료
> 로컬 검증 대상: 이번 working-tree
> 로컬 검증 근거: 백엔드 62 passed·Ruff/mypy, 프론트 build/typecheck 및 15 passed. Windows 네이티브 진단은 아래 미해결 항목 참조
> 병합 상태: 미수행
> 병합 대상: origin/main
> 병합 근거: dev 개발 단계, 게시 미요청
> 배포 상태: 해당 없음
> 배포 근거: 로컬 개발
> 실제 연동 상태: 미수행
> 실제 연동 근거: GitHub App 등록 정보 대기
> 작업 범위: L
> 적용 스킬: planning, verification-loop, ui-ux-design
> 적용 Gate: Security Gate, API Gate, DB Gate, Document Gate, UI/UX Gate
> 위험도: 인증/권한/DB
> 위험 작업 여부: 예

## 작업 계약과 체크리스트
백엔드 docs/work-plans/2026-09-26_workspace-repositories.md에 범위·사전 Gate·검증 기준 기록. 제품 구현 dev, 아키텍처 main. 실제 연동과 자동 테스트를 구분한다.

## 1. 구현 결과
팀 생성/멤버 목록·초대/일회성 대상 검증·탈퇴/제거·역할 변경·소유권 이전, GitHub App 설정 상태·설치 링크·사용자+설치+저장소 관리자 권한 검증, 저장소 연결/해제·중복 배정·재연결 generation, PR metadata 동기화/상세/기존 리뷰 상태·커밋 식별자 조회.
초기 연결과 config v1·SyncRun·Job을 원자적으로 저장한다. 영속 sync는 lease/heartbeat/fence·재시도/소진·ETag/304·rate limit·stale update 차단을 갖춘다. 리뷰 원문/코드/commit message는 GitHub 링크로 안내하며 반환하지 않는다. 규칙 설정 편집·Webhook·분석·AI는 후속이다.

## 2. 변경 범위
백엔드 workspace 서비스/공개 API·router·schema, auth 설치 state 공개 계약, repository/pull_request 도메인, shared GitHub/Job 기반, workflows 연결 조립, main/settings/crypto 의존성, migration 0003, 테스트, 실행 안내. 프론트는 인증된 API 호출과 WorkspacePanel, HomeView·스타일·회귀 테스트. 아키텍처 main에는 ADR-INTEGRATION-002와 HTTP/구현 현황 갱신.

## 3. 검증 결과
- 실제 PostgreSQL 격리 테스트 스키마에서 전체 62 tests PASS(exit0). Workspace 권한/초대 재사용·대상 ID/동시 수락/동시 OWNER 이전, 잘못된 GitHub 사용자·App/권한·설치 목록·suspension, callback binding/replay, 저장소 중복/재연결, sync 합치기/충돌·실패/재시도·lease 복구·stale fence·ETag304·역순 metadata·리뷰 원문 비노출을 확인했다. 외부 HTTP는 MockTransport다.
- 새 migration의 upgrade/downgrade/upgrade와 ORM drift 비교 PASS, 업무 테이블 11개 물리 FK0. 기존 identity 스키마 검사는 그 소유 6개 테이블로 범위를 유지하고 새 migration 전체 검사를 추가했다.
- 로컬 개발 DB에 0003 upgrade 적용, alembic check: No new upgrade operations detected. 기존 데이터 삭제 없음.
- Ruff check/format PASS, mypy 82 files PASS. 프론트 typecheck/build PASS, 15 tests PASS.
- 브라우저 localhost:5173의 비로그인 화면과 연결 확인 버튼에서 API/DB 연결 완료를 확인했다. 실제 사용자 팀 조작/등록한 App callback/설치/PR 조회 UI는 사용자 수동 테스트 대기이며 자동 테스트와 구분한다.
- 아키텍처 문서·선택 도구 검증 PASS(69 markdown, 17 ADR). 릴리스/외부 운영 보안 검증 완료를 의미하지 않는다.

## 4. Gate와 경계
Security/API/DB: 위 자동 검증 범위 PASS. SQL은 repository/store가 소유하고 다른 도메인은 api.py로 접근한다. bearer 인증과 최신 멤버십·팀 스코프, workspace→연결→sync→job 잠금 순서, 외부 HTTP 중 DB lock 없음, 안전한 오류, 비밀값·원문 코드 미저장. job heartbeat는 Job만 잠그고 다른 업무 잠금을 취하지 않는다.
UI: loading/empty/error/retry/disabled, 레이블·aria-live, 소유권 이전·탈퇴·해제 확인, 공유 범위 안내, 응답 allowlist·Vue text 렌더. 인증된 전체 화면·다중 계정·모바일 실브라우저 검수는 사용자 확인 대기다.

## 5. 트러블슈팅
### 샌드박스 esbuild 파일 접근
- 어디서: Windows frontend npm build/test의 Vite 설정 로딩.
- 무엇: 상위 디렉터리 Access denied로 esbuild가 설정 파일을 해석하지 못했다.
- 어떻게: vue-tsc 이후 esbuild 시작 단계 실패. 코드 타입 오류가 아닌 경로 접근 진단 확인.
- 왜: 샌드박스 파일 접근 제한. 같은 코드의 호스트 실행으로 구분했다.
- 해결: 승인된 호스트 실행에서 build 및 15 tests 통과. 보안 설정/파일 ACL을 임의 변경하지 않았다.
- 앞으로: 같은 환경 제한이면 접근 오류와 코드 실패를 구분하고 허용된 실행 환경에서 같은 명령을 검증한다.

### 기존 Windows Psycopg 네이티브 진단 재관측
- 어디서: 전체 DB 테스트 실행 중 Psycopg 동기 select/DDL 경로.
- 무엇: Windows fatal exception: access violation 진단 스택 출력 후 실행이 계속되어 최종 62 passed·exit0.
- 어떻게: 이전 로그인 작업 때와 같은 종류이며 이번 전체 재실행에서도 간헐적으로 관측. 별도 성공 실행과 진단 출력 실행을 구분한다.
- 왜: 원인 미확정. Python/Psycopg/Windows 네이티브 경계 가능성만 있고 무해하다고 확정하지 않는다.
- 해결: 미해결. faulthandler 비활성화나 오류 숨김 없음. 테스트 PASS와 네이티브 안정성을 동일시하지 않는다.
- 앞으로: 후속 담당자는 재현 환경/버전과 최소 재현을 확보해 조사한다. 운영 안정성 완료 주장 금지. 기존 Starlette/httpx deprecation은 별도 미해결이다.

## 6. 미해결 및 다음 단계
사용자의 GitHub App 등록·실제 secret/private key 설정·실계정 테스트가 필요하다. backend docs/TEAM_REPOSITORIES.md에 정확한 설정과 수동 시나리오를 제공했다. 로그인 OAuth 설정은 그대로 보존한다. 외부 App을 대신 생성하거나 권한을 부여하지 않았다.
분석 실행/자동 Webhook은 다음 묶음. 설치 철회는 현재 sync 실패로 SUSPENDED 전환하며 Webhook 실시간 반영은 후속이다. 원문 리뷰 렌더링·규칙 편집·Sync 취소 UI는 현재 구현 범위 밖이다.
이번 변경은 미커밋·미푸시이며 CI는 미실행이다. 아키텍처 신규 ADR도 로컬 main 변경이며 architecture.json 원격 기준 SHA는 게시 후 갱신해야 한다. 하네스 원본/사본 동기화는 수행하지 않았다.

## 7. 작업 기록
체크리스트와 이 Report를 먼저 생성한 뒤 설계→구현→검증했다. 최신 포인터는 본 Report이며 Working Context에 현재 상태를 반영한다. 사용자가 맡기로 한 실제 외부 연동 테스트는 완료로 체크하지 않는다.

추가 검증: 재시도 3회 소진과 멤버 권한 철회 시 외부 HTTP 미호출을 추가한 GitHub 연동 테스트 14개 PASS. 전체62개 통과 이후 추가된2개를 포함한 관련14개 재실행이며 전체64개를 재실행했다고 주장하지 않는다. DB Gate는 PK/NOT NULL/UQ/CHECK/UTC 시각·상태 전이·논리 연결/정책 snapshot·soft disconnect·인덱스 및 migration 왕복/drift 근거로 PASS.
