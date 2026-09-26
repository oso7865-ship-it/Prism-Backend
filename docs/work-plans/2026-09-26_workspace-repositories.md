# 팀·저장소 연결 구현 계획

> 작업 브랜치: dev
> 작업 범위: L
> 적용 스킬: planning, verification-loop, ui-ux-design
> 적용 Gate: Security Gate, API Gate, DB Gate, Document Gate, UI/UX Gate

## 작업 계약
목표: Workspace 생성→멤버 초대/가입→RBAC→GitHub App 저장소 연결→최근 PR 동기화/조회까지 구현한다.
Goals: 일회성 대상 지정 초대, OWNER 이전 직렬화, 역할별 API/화면, 사용자+App 권한 확인, 물리 FK 없는 논리 참조, 영속 PR sync와 제한된 외부 리뷰 조회.
Non-Goals: 정적 분석/AI/Webhook/공개 배포/하네스 사본 동기화. 실제 App 등록과 키 입력은 사용자 설정에 의존한다. 요청 없는 Git 게시 없음.
수정: workspace/auth 공개 설치 state 계약, repository/pull_request, shared GitHub/Job, bootstrap, 새 migration, 테스트, Vue 기능 화면, 실행 문서. 아키텍처는 main에서 API 지도·구현 현황을 갱신하며 정책 변경이면 ADR 추가.
근거: CORE, PACKAGE-RULES, CONVENTIONS, WORKSPACE, REPOSITORY, PULL-REQUEST, PR-SYNC, HTTP-API, DB-GITHUB, DB-EXECUTION, JOBS.
사전 Security/DB Gate: 설계 PASS. 모든 API 인증 및 최신 팀 권한, Workspace 잠금→자식 행→Job 순서, 초대 hash만 저장, state/PKCE 브라우저+사용자+팀 바인딩, GitHub 고정 TLS endpoint와 응답 크기/시간 제한, provider token 메모리 전용, 타 팀 404, 내부 오류 마스킹. 사용자 요청이 기능/DB/보안 변경 근거. 사후 테스트는 별도.

## 체크리스트
- [x] W1 Workspace 목록·생성·멤버·초대·탈퇴/제거·역할·OWNER 이전 API; 실제 PG 경쟁/권한/재사용 테스트.
- [x] G1 GitHub App 설정·설치 안내·state/PKCE callback·사용자/저장소 관리 권한 검증; 위조/재사용/철회 테스트.
- [x] R1 저장소 연결/해제·세대·설정 v1 및 migration; FK0/중복 연결/권한 재검증.
- [x] P1 영속 최근30개/페이지/단건 sync 접수·Worker·PR 목록/상세/리뷰; lease/fence/재시도/역순/접근 실패 테스트.
- [x] F1 팀 선택·초대 수락·멤버 관리·연결·동기화·PR UI. loading/empty/error/retry와 접근성.
- [x] V1 Ruff/mypy/전체 PostgreSQL 테스트, migration 왕복/check, Vue build/tests, 문서 검사.
- [x] D1 수동 테스트 안내·App 등록값·리포트·다음 작업 기록.
- [x] U1 실제 GitHub App 등록 및 실계정 연결·PR 조회: meerkatgram-v2-post Draft PR #1, COMPLETED 1개 확인.

검증 세부 결과·Windows 네이티브 잔여 진단·실브라우저 검수 범위는 ../../reports/2026-09-26_workspace-repositories_report.md를 따른다. 리뷰 본문을 표시하지 않는 단계별 응답 계약은 ADR-INTEGRATION-002에 기록했다.
