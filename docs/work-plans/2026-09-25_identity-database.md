# 인증·팀 DB 구현 및 로컬 PostgreSQL 검증 계획

작성일: 2026-09-25. 범위: 사용자가 지정한 1번(6개 ORM·migration), 2번(로컬 Docker DB·검증). 이 문서는 착수 전 설계·체크리스트이며 실제 결과는 [작업 리포트](../../reports/2026-09-25_identity-database_report.md)에 기록한다.

## 목표와 범위

- users, login_attempts, refresh_sessions, workspaces, workspace_members, invitations의 PostgreSQL 모델과 Alembic 0002를 구현한다.
- 물리 FK 없이 PK·UNIQUE·CHECK·NOT NULL·부분 인덱스를 기존 설계대로 적용한다.
- 개발용 DB와 별도 검증용 DB를 구분하고 실제 PostgreSQL에서 생성→rollback→재적용, 제약·경쟁·트랜잭션 rollback을 검증한다.
- Non-Goals: OAuth/Refresh/Workspace 서비스·API·권한 로직, UI, 나머지 11개 테이블, 운영 배포·외부 API, 하네스 동기화, Git 쓰기. ORM만으로 애플리케이션 관계 무결성까지 완성됐다고 하지 않는다.

## 설계 근거와 출처

architecture.json의 기존 기준 커밋은 c8070204eedb6a620481ef263e9e55ab9457d6e6이다. 이번 작업은 그 뒤 사용자와 확정한 **미커밋 아키텍처 작업본**의 ADR-DATA-003 및 DB-IDENTITY/DB-SCHEMA를 추가 입력으로 사용한다. 그 변경이 원격 커밋에 포함됐다고 표시하지 않는다. 명세 snapshot은 docs/database/IDENTITY_SCHEMA.md에 보관하고 원본 경로·기준과 함께 추적한다.

읽은 기준: CORE, PACKAGE-RULES, CONVENTIONS, DATA-MODEL, DB-SCHEMA, DB-IDENTITY, ADR-DATA-003, DATABASE. 하네스 planning/verification-loop, DB Gate 및 ERD Checklist를 적용한다. 위험도는 DB/구조다. 사용자 최신 요청이 구현·로컬 DB 준비·검증의 근거이며 기존 사용자 데이터에는 destructive 검증을 하지 않는다.

## 구현 설계

| 책임 | 위치·방식 |
|---|---|
| 공통 PK/생성시각·수정시각 | shared/database의 기술적 mixin, UUID v4는 Python default, 시각은 timestamptz/UTC |
| User ORM | domain/user/models.py |
| 로그인 시도·Refresh ORM | domain/auth/models.py |
| Workspace·Member·Invitation ORM | domain/workspace/models.py |
| 모델 등록 | migrations/env.py가 명시 import, shared에서 domain을 import하지 않음 |
| migration | 0001 빈 기준선 유지, 0002에 독립된 고정 Table/Index 정의; 실행 시 현재 ORM을 import해 DDL 생성하지 않음 |
| 관계 | UUID 컬럼만, ForeignKey/relationship/cascade 없음. 존재·팀·역할 검증은 다음 서비스 단계 |
| 시간 갱신 | SQLAlchemy onupdate=func.now() 및 server_default=func.now(); raw SQL 작성자는 updated_at 갱신 책임 |
| 검증 | metadata 컴파일/경계 검사 + 실제 PG catalog·제약·두 연결의 경쟁·transaction rollback + Alembic drift 검사 |

## 데이터 보호·롤백

개발 DB prism은 named volume에 보존하고 upgrade만 한다. 개발 DB에 기존 행이 있으면 그대로 유지한다. downgrade/drop 검증은 이번 작업 전용 prism_test DB에서만 수행한다. 테스트 DB라는 명시적 환경변수와 DB 이름 확인 없이는 destructive 검증을 시작하지 않는다. fixture는 임시 schema로 격리해 종료 시 자기 schema만 제거한다. 기존 개발/사용자 DB와 외부 서버를 대상으로 하지 않는다.

빈 신규 DB는 별도 백업할 데이터가 없다. 기존 데이터가 발견되면 파괴적 downgrade를 하지 않고 필요한 경우 백업 후 별도 계획으로 이관한다. 0002 downgrade는 6개 테이블을 삭제하는 동작이므로 실제 데이터 보존 rollback으로 안내하지 않는다. migration 실패는 PostgreSQL DDL transaction rollback을 확인한다. docker compose down -v는 실행하지 않는다.

## 전체 체크리스트

- [x] S01: 기존 코드·명세·로컬 변경 확인, 목표/제외 범위·되돌릴 기준 기록.
- [x] S02: 사전 설계·체크리스트·작업 Report 생성.
- [x] I01: 6개 모델·공통 컬럼·모델 등록 구현.
- [x] I02: 0002 upgrade/downgrade와 명세 동일성 검수.
- [x] I03: 필수값·허용 상태·SHA256·만료·소비/철회 컬럼 CHECK 구현.
- [x] I04: 사용자/멤버/토큰 UNIQUE, OWNER/PENDING 초대 부분 UNIQUE 및 조회 인덱스 구현.
- [x] T01: metadata·FK 0·shared→domain 금지·offline migration 검증.
- [x] E01: Docker 엔진 확인, 기존 컨테이너/포트 영향 없는 개발 DB 준비.
- [x] E02: 개발 DB readiness 및 0002 upgrade, 다른 연결에서 테이블 확인.
- [x] T02: 전용 테스트 DB에서 upgrade→downgrade 0001→upgrade 및 Alembic check.
- [x] T03: 실제 PG의 FK 0·PK/UQ/CHECK·NULL·인덱스 확인 및 무효값 거부.
- [x] T04: 독립 연결로 동일 GitHub ID·활성 OWNER·초대 중복 insert 경쟁 검증.
- [x] T05: 정상 ORM roundtrip·전체 transaction rollback·소유권 변경 실패 rollback 검증.
- [x] T06: Ruff check/format, mypy, 전체 pytest(실제 DB 포함), 기존 health 회귀.
- [x] D01: 실행 방법·HeidiSQL 접속 정보·검증 증거·미구현 관계 서비스 경계 기록.
- [x] D02: Report·최신 포인터·작업 큐 갱신, 하네스 동기화 없이 기록 일치 확인.

부모 존재·교차 팀 쓰기·권한 철회/삭제 경쟁은 **다음 서비스 구현 단계**의 게이트다. 이번에는 raw SQL에 FK 방어가 없다는 사실과 DB에 맡긴 제약만 검증한다. 이 항목을 모델 단계의 완료 증거로 바꾸지 않는다.

## 전체 프로젝트 후속 체크리스트

아래는 다음 단계의 요약이며 이번 실행 범위가 아니다. 기능별 착수 때 세부 설계·테스트를 추가한다.

- [x] 코드·원본 설계 커밋/푸시, architecture.json 실제 revision 연결, 구현 커밋 CI 성공(665a200 / a2873f6).
- [ ] GitHub OAuth 로그인·callback·User 생성 및 세션 회전/폐기 API.
- [ ] Workspace 생성·멤버·초대·권한, 부모 존재/팀 일치/OWNER 유지의 트랜잭션 검증.
- [ ] GitHub App 실제 연결·저장소 권한·웹훅 및 관련 테이블.
- [ ] 분석 Job·실행 격리·결과 저장 및 나머지 도메인 테이블.
- [ ] DeepSeek 연결·비용/실패 처리·기본 OFF 해제 조건 검증.
- [ ] 프론트엔드 로그인·팀·저장소·분석 결과 화면 연결.
- [ ] 배포 주소·환경 확정 및 배포/E2E 검증.
- [ ] 하네스 동기화(사용자 요청에 따라 보류).
