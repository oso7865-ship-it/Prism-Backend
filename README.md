# PRism Backend

Python 3.12 / FastAPI / SQLAlchemy / PostgreSQL 개발 기반입니다. 인증·팀 6개 테이블과 마이그레이션을 구현했습니다. GitHub 로그인·프로필·세션 갱신·로그아웃 API를 로컬 구현했습니다. 실제 GitHub 기본 로그인 흐름은 사용자 확인 완료이며 Workspace·PR·Job·분석·AI는 후속입니다. 운영 모드는 비활성화했으며 현 단계는 로컬 개발용입니다.

## 실행

Git, uv 0.12.18, Python 3.12가 필요합니다. uv는 필요한 Python을 다운로드할 수 있습니다.

```bash
git clone https://github.com/oso7865-ship-it/Prism-Backend.git prism-backend
cd prism-backend
uv sync --locked
uv run uvicorn app.main:create_app --factory --loop app.shared.database.event_loop:loop_factory --reload --no-access-log
```

DB 설정이 없어도 `/health/live`는 200입니다. `/health/ready`는 DB에 연결할 수 없으면 503이며 내부 오류·접속 문자열을 공개하지 않습니다. 외부 API 호출은 없습니다. AI_ENABLED=true와 미구현 Job runner 모드는 시작 시 거부합니다.

## 로컬 PostgreSQL

개발 기준 이미지: PostgreSQL 17. 운영 호스팅 선택과는 별개입니다. Docker Desktop 또는 Docker Engine + Compose를 준비한 다음 `config/development.example`을 `.env`로 복사하고 로컬 비밀번호와 DATABASE_URL을 맞춥니다. 예시 비밀번호는 로컬 개발 전용입니다.

```bash
docker compose up -d --wait
uv run alembic upgrade head
uv run uvicorn app.main:create_app --factory --loop app.shared.database.event_loop:loop_factory --reload --no-access-log
```

HeidiSQL: PostgreSQL TCP/IP / 127.0.0.1 / 5432 / 사용자 prism / DB prism / .env의 비밀번호. 포트는 루프백에만 바인딩합니다. named volume에 데이터가 유지되며 `docker compose down -v`는 데이터를 삭제하므로 평소에는 `docker compose down`만 사용합니다.

마이그레이션은 빈 기준선 0001 다음 0002에서 users, login_attempts, refresh_sessions, workspaces, workspace_members, invitations를 생성합니다. 물리 FK는 없으며 논리 관계 검증은 다음 서비스 단계입니다. API startup에서 migration이나 create_all을 실행하지 않습니다. [컬럼 명세](docs/database/IDENTITY_SCHEMA.md)와 [로컬 DB·HeidiSQL·별도 테스트 DB 안내](docs/database/LOCAL_POSTGRES.md)를 참고하세요.

## 검증

```bash
uv run ruff check app tests migrations
uv run ruff format --check app tests migrations
uv run mypy app
uv run pytest -q -m "not integration"
```

실제 DB 검사는 `_test`로 끝나는 별도 DB에 TEST_DATABASE_URL을 설정한 후 `uv run pytest -q -m integration`으로 실행합니다. 임시 스키마에서 제약조건·동시 쓰기·ORM 저장·트랜잭션 rollback을 검증합니다. CI에는 PostgreSQL 17 migration 왕복과 `alembic check`, 전체 테스트를 구성했습니다. 테스트 DB가 없어 skip된 경우 DB 검증 통과로 처리하지 않습니다.

구조: app/main.py는 조립, app/shared/config는 설정, database는 세션·트랜잭션, observability는 health를 소유합니다. 업무 도메인은 실제 기능 추가 시 app/domain 아래에 만듭니다.

다음 작업: 로그인·User·Workspace 권한을 작은 수직 흐름으로 구현. Job/분석/DeepSeek는 후속 단계입니다.

## 하네스와 다른 PC에서 재개

이 저장소 루트의 AGENTS.md → PROJECT_HARNESS/00.PROJECT_CONTEXT.md → 작업별 문서 순서로 읽습니다. 공통 하네스는 [HARNESS](https://github.com/oso7865-ship-it/HARNESS)의 `0b7dcf9d567eaaa0c883eaee73620aa07cf60019` 사본입니다. 상위 폴더가 없어도 사용할 수 있습니다. 원본 유지보수 보고서는 출처 이력이며 현재 제품 상태는 GENERAL_HARNESS/05.WORKING_CONTEXT.md와 부착 프로젝트 최신 Report를 따릅니다.

[아키텍처 연결](docs/ARCHITECTURE.md)과 architecture.json으로 설계의 원본·기준 커밋을 추적합니다. 아키텍처를 바꾸면 원본 저장소에 ADR과 소유 문서를 갱신합니다. 각 저장소의 main이 통합 기준이며 이후 기능 작업은 별도 브랜치·PR·CI로 검증합니다. 초기 빈 저장소의 첫 커밋은 main으로 게시합니다. 브랜치 보호 설정 자체는 아직 적용하지 않았습니다.

작업 시작: git status로 로컬 변경 확인 → 깨끗한 상태에서 git pull --ff-only → 의존성 잠금 기준 설치 → 최신 Report의 미해결 항목 확인. 작업 종료: 검증 → Report/Working Context 갱신 → 커밋·푸시. 비밀 값과 가상환경·node_modules는 Git에 올리지 않습니다.

하네스 연결 검사: `node GENERAL_HARNESS/scripts/validate-project-adapter.mjs --project-root . --require-adapter --strict --json`.

## 확인된 검증 기록

[초기 구현 CI](https://github.com/oso7865-ship-it/Prism-Backend/actions/runs/36039579708)는 이전 5개 테스트 기준 기록입니다. 이번 DB 단계는 로컬 Docker PostgreSQL 17에서 migration 왕복·drift 검사, 테스트 28개 및 실제 Uvicorn readiness 200을 확인했습니다. [이번 구현 커밋의 원격 CI](https://github.com/oso7865-ship-it/Prism-Backend/actions/runs/36127425357)도 통과했습니다. 현재 게시 상태는 [최신 Report](reports/_LATEST.md)를 따릅니다. [작업 계획·체크리스트](docs/work-plans/2026-09-25_identity-database.md), [검증·트러블슈팅 리포트](reports/2026-09-25_identity-database_report.md)를 참조하세요.

## GitHub 로그인 수동 테스트

[실행 방법·설정·수동 체크리스트](docs/GITHUB_LOGIN.md). 프론트는 http://localhost:5173 을 사용합니다. 로컬 OAuth 설정은 `.env`에만 있으며 Git에 포함하지 않습니다. 최신 구현·검증 상태는 [Report](reports/2026-09-25_github-login_report.md)를 따릅니다.
