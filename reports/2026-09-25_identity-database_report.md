# 작업 리포트: 인증·팀 DB 기반과 로컬 PostgreSQL

> 작성일: 2026-09-25
> 패키징/배포일: 해당 없음
> 작업 브랜치: main
> 커밋/PR: 미커밋
> 상태 기록 버전: 1
> 상태 확인 시각: 2026-09-25T19:50:26+09:00
> 구현 상태: 완료
> 구현 근거: docs/work-plans/2026-09-25_identity-database.md의 승인된 범위
> 로컬 검증 상태: 완료
> 로컬 검증 대상: ebd0c9b 이후 인증·팀 DB working-tree
> 로컬 검증 근거: §3 로컬 PostgreSQL 17 migration 왕복·28 tests·실제 HTTP readiness
> 병합 상태: 미수행
> 병합 대상: origin/main
> 병합 근거: Git 쓰기 범위 제외
> 배포 상태: 해당 없음
> 배포 근거: 로컬 개발 DB 작업이며 서비스 배포 범위 제외
> 실제 연동 상태: 완료
> 실제 연동 근거: 로컬 Docker PostgreSQL 17에 ORM/migration/HTTP readiness 연결 확인. GitHub/AI 연동을 뜻하지 않음
> 작업 범위: L
> 적용 스킬: planning, verification-loop, terminal-ops, troubleshooting-report
> 적용 Gate: DB Gate, Document Gate
> 위험도: DB
> 위험 작업 여부: 예

## 0. 작업 범위 확인

사용자 요청: 먼저 설계·체크리스트·기록 문서를 만들고 6개 모델/migration 및 로컬 Docker PostgreSQL 검증만 진행. 계획의 Non-Goals·데이터 보호 절차를 따른다. 기존 하네스 미커밋 변경은 보존하고 동기화하지 않는다. 되돌릴 기준 커밋은 ebd0c9b9c1922568b69af6949ad18c1ba4cd43a1.

## 1. 작업 요약

사전 계획·체크리스트·리포트 작성 후 6개 ORM과 고정 Alembic 0002를 구현했다. PostgreSQL 17을 Docker로 실행하고 개발 DB에 적용했다. 물리 FK는 0개이며 DB 제약과 향후 서비스의 논리 무결성 책임을 분리했다. 다른 PC용 실행 안내와 미커밋 설계 snapshot을 저장했다.

## 2. 변경 파일

- app/domain/user/models.py, auth/models.py, workspace/models.py 및 패키지 init: 6개 모델.
- app/shared/database/mixins.py, event_loop.py: UUID/시간 및 Windows 호환 loop.
- migrations/env.py, versions/0002_identity_tables.py, alembic.ini: 모델 등록·고정 DDL·loop·설정.
- tests/test_identity_database.py, test_database.py: PostgreSQL 제약·경쟁·rollback·경계 회귀.
- docs/work-plans/2026-09-25_identity-database.md, docs/database/*, docs/ARCHITECTURE.md, README.md: 계획·명세 출처·실행 안내.
- .github/workflows/ci.yml: alembic check 추가. reports 및 Working Context: 결과/큐 갱신.
- .env는 새 로컬 암호를 사용하는 Git 제외 파일. 비밀값은 문서/출력에 싣지 않는다.

## 3. 검증 결과

| 체크 | 실제 검증 | 결과 |
|---|---|---|
| I01–I04/T01 | 6개 ORM과 migration 검수, metadata·offline SQL·shared import 경계 테스트 | PASS, 업무 6개 / FK 0 |
| E01 | Docker client/server 29.6.2, `docker compose up -d --wait db` | PASS, postgres:17 healthy, 새 named volume |
| E02 | 개발 prism에 Alembic upgrade/check, 별도 SQL 연결 inspect | PASS, revision 0002, 업무 6개 + alembic_version, FK 0 |
| T02 | 새 prism_test의 기존 업무 행 0 확인 후 upgrade → check → downgrade 0001 → upgrade → check | PASS, downgrade 후 alembic_version만 남음. 두 번 모두 No new upgrade operations detected |
| T03 | 실제 PG catalog PK/CHECK/partial index, 무효 상태·NULL·hash·만료·짝 컬럼·membership UQ | PASS |
| T04 | 독립 연결 2개의 GitHub ID/OWNER/PENDING 초대 동시 insert | PASS, 각각 한 commit과 해당 UNIQUE 오류 |
| T05 | 여섯 ORM 저장/재조회, OWNER 변경 실패 시 앞선 User insert까지 rollback | PASS |
| T06 | `ruff check app tests migrations`, `ruff format --check app tests migrations`, `mypy app` | PASS, mypy 19 files |
| T06 | TEST_DATABASE_URL=전용 DB, `python -m pytest -q -p no:cacheprovider` | PASS, 28 passed, DB skip 없음 |
| E02/T06 | 실제 Uvicorn 프로세스 + 명시 loop, HTTP GET /health/ready | PASS, 200 및 ready. 검증 서버 종료, DB 유지 |
| D01/D02 | work-records strict, project-adapter strict, docs/skills/references/report-consistency/no-personal-paths/harness 검사 | PASS |
| D01/D02 | Git diff --check, .env ignore 확인, 새 코드·문서에 실제 로컬 암호 포함 여부 검사 | PASS. 기존 no-secrets 스크립트의 tracked-file 검사와 별도 수행 |
| T01 | offline 테스트에 로컬 .env 없이 사용할 URL을 명시한 뒤 non-integration 재검증 | PASS, 6 passed / 22 deselected. Ruff check/format도 통과 |

이번 결과는 로컬 Windows/Python 3.12/Docker PostgreSQL 17의 미커밋 작업본이다. 원격 CI·배포는 미수행이다. 개발 DB에 downgrade하지 않았고 테스트는 고유 schema를 제거했다. PostgreSQL은 계속 실행 중이다.

## 4. Checklist 결과

요청한 1·2번 체크리스트 완료. 데이터 보존·destructive 테스트 격리·명세 일치·DB 제약·경쟁 검증 통과. 논리 참조/교차 팀/권한/정확히 한 OWNER를 서비스가 유지하는 검증은 다음 단계이며 이번 완료 범위에 포함하지 않는다. 하네스 동기화 및 Git 쓰기는 수행하지 않았다.

## 5. 발견된 문제

Docker가 일반 PATH에 없어 처음 감지하지 못했으나 사용자별 설치의 바이너리로 확인했다. 재설치하지 않았다. [공식 설치 안내](https://docs.docker.com/desktop/setup/install/windows-install/)의 사용자별 경로와 일치했다.

### 트러블슈팅: Windows에서 Psycopg async migration 실패

- 사건 상태: 해결 검증 완료. 원인 상태: 확인.
- 관련 변경: 이번 미커밋 작업, app/shared/database/event_loop.py 및 migrations/env.py.

#### 어디서 발생했나

2026-09-25 KST 로컬 Windows/Python 3.12에서 Alembic 0001 적용 및 0002 autogenerate 시 발생했다. 정확한 최초 발생 시각·지속 시간은 미확인. 위치: migrations/env.py의 asyncio.run 진입점과 Psycopg connection_async.

#### 어떤 문제가 있었나

DB 연결을 기대했으나 `Psycopg cannot use the 'ProactorEventLoop' to run in async mode` 오류가 발생했다. ORM 쿼리 실행 전 연결 단계에서 실패했다. Docker DB는 healthy였고 URL 비밀값은 기록하지 않았다.

#### 어떻게 발생했나

실행 중인 로컬 PostgreSQL을 향해 기본 asyncio.run으로 async SQLAlchemy 엔진 연결을 시작하면 Windows 기본 Proactor loop가 선택된다. 최초 migration 명령이 이 경로를 재현했다.

#### 왜 발생했나

Psycopg의 Windows async 연결은 Proactor와 호환되지 않는다. 설치된 connection_async의 win32/Proactor 검사와 [Psycopg 공식 문서](https://www.psycopg.org/psycopg3/docs/advanced/async.html)로 확인했다. Uvicorn의 custom loop 설정은 factory를 직접 호출하므로 실제 loop 인스턴스를 반환해야 한다. DB 불가용이 원인은 아니었다.

#### 어떻게 해결했나

| 순서 | 시도 | 결과 |
|---|---|---|
| 1 | 기본 asyncio.run으로 migration | Proactor 호환 오류 발생 |
| 2 | 명시 SelectorEventLoop factory를 추가하고 Alembic·async 테스트에 전달 | 동일 DB에서 migration 및 전체 테스트 통과 |
| 3 | 설치된 Uvicorn config 구현을 읽어 custom factory 반환 계약 확인, 실행 명령에 --loop 지정 | 실제 Uvicorn HTTP readiness 200 |

명시 실행 진입점의 근본 호환 수정이다. 전역 정책 변경은 하지 않았다. 로컬 검증은 위 §3과 연결된다. Linux 원격 CI는 아직 실행하지 않았으며 future async subprocess 동작은 이번 범위 밖이다.

#### 앞으로 어떻게 대응하나

| 조치 | 원인과의 연결 | 담당 | 실행 조건 | 완료 기준 | 상태 |
|---|---|---|---|---|---|
| README 실행 옵션과 loop regression test | 기본 Windows loop 재유입 방지 | 이번 작업 | 현재 | factory 및 실제 readiness 통과 | 완료 |
| 이후 async DB entrypoint에도 factory 적용 | 신규 진입점에서 같은 오류 방지 | 후속 구현 담당 미정 | entrypoint 추가 시 | Windows 실제 DB 테스트 | 대기 |
| 분석 worker의 subprocess/loop 설계 별도 검토 | Windows Selector의 subprocess 제약 | 후속 구현 담당 미정 | worker 설계 시 | worker 실행 테스트 통과 | 대기 |

Starlette/httpx deprecation 경고 1건은 기존 의존성 조합에서 발생한다. 테스트 실패는 없으며 의존성 갱신 작업 때 호환성을 검토한다. Alembic path_separator 경고는 설정으로 해소했다.

## 6. 미해결 항목

요청한 1·2번의 구현 차단 항목은 없다. Git 미커밋·미푸시 및 원격 CI 미수행. 아키텍처 source snapshot도 미커밋 작업본에서 가져왔으므로 원본 게시 후 실제 revision 갱신이 필요하다. OAuth·인가·관계 무결성 서비스, 나머지 11개 테이블, 하네스 동기화는 후속 범위다.

## 7. Working Context 반영 여부

프로젝트와 부착 하네스 최신 Report 포인터 및 Working Context에 완료 상태와 다음 큐를 반영했다. 이전 상태 요약은 Working Context history에 보존했다. 하네스 원본/다른 저장소와 동기화하지 않았다.

## 8. 다음 작업

코드·원본 설계의 커밋/푸시 및 실제 revision 연결을 별도 진행하고, 다음 구현은 GitHub OAuth → User/Workspace 서비스·논리 관계 검증 순서로 설계한다. 로그인 API는 이번에 시작하지 않았다.
