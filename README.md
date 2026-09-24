# PRism Backend

Python 3.12 / FastAPI / SQLAlchemy / PostgreSQL 개발 기반입니다. 로그인·Workspace·PR·Job·분석·AI는 아직 구현하지 않았습니다. 운영 모드는 의도적으로 비활성화했으며 현 단계는 로컬 개발용입니다.

## 실행

Git, uv 0.12.18, Python 3.12가 필요합니다. uv는 필요한 Python을 다운로드할 수 있습니다.

```bash
git clone https://github.com/oso7865-ship-it/Prism-Backend.git prism-backend
cd prism-backend
uv sync --locked
uv run uvicorn app.main:create_app --factory --reload --no-access-log
```

DB 설정이 없어도 `/health/live`는 200입니다. `/health/ready`는 DB에 연결할 수 없으면 503이며 내부 오류·접속 문자열을 공개하지 않습니다. 외부 API 호출은 없습니다. AI_ENABLED=true와 미구현 Job runner 모드는 시작 시 거부합니다.

## 로컬 PostgreSQL

개발 기준 이미지: PostgreSQL 17. 운영 호스팅 선택과는 별개입니다. Docker Desktop 또는 Docker Engine + Compose를 준비한 다음 `config/development.example`을 `.env`로 복사하고 로컬 비밀번호와 DATABASE_URL을 맞춥니다. 예시 비밀번호는 로컬 개발 전용입니다.

```bash
docker compose up -d --wait
uv run alembic upgrade head
uv run uvicorn app.main:create_app --factory --reload --no-access-log
```

HeidiSQL: PostgreSQL TCP/IP / 127.0.0.1 / 5432 / 사용자 prism / DB prism / .env의 비밀번호. 포트는 루프백에만 바인딩합니다. named volume에 데이터가 유지되며 `docker compose down -v`는 데이터를 삭제하므로 평소에는 `docker compose down`만 사용합니다.

마이그레이션은 빈 기준선 0001과 Alembic 이력만 생성합니다. 업무 테이블은 해당 기능에서 도입합니다. API startup에서 migration이나 create_all을 실행하지 않습니다.

## 검증

```bash
uv run ruff check app tests migrations
uv run ruff format --check app tests migrations
uv run mypy app
uv run pytest -q -m "not integration"
```

실제 DB 검사는 별도의 테스트 DB에 TEST_DATABASE_URL을 설정한 후 `uv run pytest -q -m integration`으로 실행합니다. 테스트는 일회성 임시 테이블의 rollback과 세션 트랜잭션을 확인합니다. CI는 PostgreSQL 17 서비스에서 migration upgrade/downgrade/upgrade 및 전체 테스트를 실행합니다. 로컬 Docker가 없는 환경의 실행 누락을 DB 검증 통과로 처리하지 않습니다.

구조: app/main.py는 조립, app/shared/config는 설정, database는 세션·트랜잭션, observability는 health를 소유합니다. 업무 도메인은 실제 기능 추가 시 app/domain 아래에 만듭니다.

다음 작업: 로그인·User·Workspace 권한을 작은 수직 흐름으로 구현. Job/분석/DeepSeek는 후속 단계입니다.

## 하네스와 다른 PC에서 재개

이 저장소 루트의 AGENTS.md → PROJECT_HARNESS/00.PROJECT_CONTEXT.md → 작업별 문서 순서로 읽습니다. 공통 하네스는 [HARNESS](https://github.com/oso7865-ship-it/HARNESS)의 `0b7dcf9d567eaaa0c883eaee73620aa07cf60019` 사본입니다. 상위 폴더가 없어도 사용할 수 있습니다. 원본 유지보수 보고서는 출처 이력이며 현재 제품 상태는 GENERAL_HARNESS/05.WORKING_CONTEXT.md와 부착 프로젝트 최신 Report를 따릅니다.

[아키텍처 연결](docs/ARCHITECTURE.md)과 architecture.json으로 설계의 원본·기준 커밋을 추적합니다. 아키텍처를 바꾸면 원본 저장소에 ADR과 소유 문서를 갱신합니다. 각 저장소의 main이 통합 기준이며 이후 기능 작업은 별도 브랜치·PR·CI로 검증합니다. 초기 빈 저장소의 첫 커밋은 main으로 게시합니다. 브랜치 보호 설정 자체는 아직 적용하지 않았습니다.

작업 시작: git status로 로컬 변경 확인 → 깨끗한 상태에서 git pull --ff-only → 의존성 잠금 기준 설치 → 최신 Report의 미해결 항목 확인. 작업 종료: 검증 → Report/Working Context 갱신 → 커밋·푸시. 비밀 값과 가상환경·node_modules는 Git에 올리지 않습니다.

하네스 연결 검사: `node GENERAL_HARNESS/scripts/validate-project-adapter.mjs --project-root . --require-adapter --strict --json`.
