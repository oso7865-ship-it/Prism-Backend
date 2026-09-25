# 로컬 PostgreSQL 실행과 검증

현재 구현: 인증·팀 업무 테이블 6개 + Alembic 이력 테이블 1개. 전체 17개 설계 중 나머지 11개는 아직 구현하지 않았다. [컬럼 명세](IDENTITY_SCHEMA.md), [공통 규칙](COMMON_SCHEMA.md), [작업 계획](../work-plans/2026-09-25_identity-database.md)을 함께 읽는다.

## 새 PC에서 시작

Python 3.12, uv, Docker Compose를 설치하고 저장소에서 실행한다. Docker Desktop은 엔진이 실행 중이어야 한다. Windows의 사용자별 설치는 `%LOCALAPPDATA%/Programs/DockerDesktop/resources/bin/docker.exe`에 있을 수 있다.

1. `uv sync --locked`
2. `config/development.example`을 `.env`로 복사하고 POSTGRES_PASSWORD와 DATABASE_URL의 암호를 같은 새 로컬 값으로 설정한다. `.env`는 Git 제외 대상이며 PC마다 만든다.
3. `docker compose up -d --wait db`
4. `uv run alembic upgrade head`
5. `uv run alembic check` — ORM과 DB 차이가 없어야 한다.
6. `uv run uvicorn app.main:create_app --factory --loop app.shared.database.event_loop:loop_factory --reload --no-access-log`
7. `http://127.0.0.1:8000/health/ready`가 200 및 `{"status":"ready"}`인지 확인한다.

Windows에서는 Psycopg async가 SelectorEventLoop를 필요로 한다. 프로젝트 loop factory를 Uvicorn 옵션으로 지정하며 Alembic과 async DB 테스트도 같은 factory를 사용한다. 전역 정책을 변경하지 않는다. 관련 원인·검증은 [리포트](../../reports/2026-09-25_identity-database_report.md)에 기록했다.

## HeidiSQL

| 설정 | 값 |
|---|---|
| 네트워크 유형 | PostgreSQL (TCP/IP) |
| 호스트 / 포트 | 127.0.0.1 / 5432 |
| 사용자 / DB | prism / prism |
| 비밀번호 | 해당 PC의 `.env`에 설정한 POSTGRES_PASSWORD |
| 스키마 | public |

users, login_attempts, refresh_sessions, workspaces, workspace_members, invitations가 보인다. alembic_version은 업무 테이블 수에 포함하지 않는다. physical FK는 없으며 관계 컬럼은 UUID다. 부모 존재·Workspace 일치·권한 검증은 향후 서비스 계층의 책임이다. OWNER 부분 UNIQUE는 **최대 한 명**만 보장하며 최소 한 명의 존재까지 보장하지 않는다.

## 전용 DB 검증

개발 DB prism에서는 upgrade만 한다. 테스트 DB는 처음 한 번 `docker compose exec -T db createdb -U prism prism_test`로 만든다. 이미 있으면 재생성하지 않는다.

TEST_DATABASE_URL을 개발 URL과 같은 접속 정보에 **DB 이름만 prism_test**로 바꿔 설정한다. 테스트 fixture는 `_test`로 끝나는 PostgreSQL DB만 허용하고 실행마다 고유한 test_identity 스키마를 만들어 테스트 후 자기 스키마만 삭제한다. fixture 데이터는 DB 제약 자체의 검증용이며 논리 참조 서비스가 구현됐다는 증거가 아니다.

```bash
uv run pytest -q
```

TEST_DATABASE_URL이 없으면 integration 테스트는 skip되므로 전체 DB 검증 통과로 보고하지 않는다. 경쟁 테스트는 별도 연결 2개를 사용한다.

마이그레이션 왕복은 **폐기 가능한 빈 prism_test DB**에서만 수행한다. DATABASE_URL을 테스트 URL로 설정한 별도 셸에서 아래를 실행하고, 종료 후 개발 URL로 복구한다. CI도 임시 DB에서 동일한 왕복과 drift 검사를 한다.

```bash
uv run alembic upgrade head
uv run alembic check
uv run alembic downgrade 0001
uv run alembic upgrade head
uv run alembic check
```

0002 downgrade는 6개 테이블과 데이터를 삭제한다. 데이터 보존 rollback이 아니다. 개발 DB에서 실행하지 않는다. Docker 데이터는 named volume에 남으며 `docker compose down`은 컨테이너만 종료한다. `down -v`는 데이터를 지우므로 일반 종료에 사용하지 않는다. 기존 volume의 암호는 `.env` 변경만으로 바뀌지 않는다.

## 다른 PC 인계 상태

원본 설계는 `665a2003f43c851d4fa3bcd9569059a4533f5409`로 게시했고 architecture.json과 snapshot이 같은 커밋을 가리킨다. 백엔드 게시·CI의 현재 상태는 [최신 기록](../../reports/_LATEST.md)을 따른다. 다른 PC에서는 원격 main을 받은 뒤 위 절차로 의존성과 로컬 DB를 구성한다. `.env`, 가상환경, DB volume은 Git에 올리지 않는다. 하네스 동기화는 보류다.
