# PostgreSQL 물리 스키마 설계

> 구현 입력 snapshot, 2026-09-25. 원본: Prism-Architecture / docs/architecture/contracts/schema/README.md.
> 게시된 원본 커밋: 665a2003f43c851d4fa3bcd9569059a4533f5409.
> 원본 SHA256 (Git LF): 517a4c3d97e5efda22a85e3292c5e8e7baef8ab4504812a63e1e42f8dce658fc
> 이 사본은 독립 clone에서 구현 기준을 확인하기 위한 기록이다. 새 정책을 여기서 독립 변경하지 않는다.

> 원본 문서 ID: `DB-SCHEMA` · 소유: `data-contracts` · 기준: `2026-09-25`
> 읽는 때: 컬럼·타입·인덱스·마이그레이션을 구체화할 때

**17개 업무 테이블의 구현 기준 설계다. 인증·팀 6개는 ORM·마이그레이션·로컬 DB 적용을 완료했고 나머지 11개는 설계 단계다.** PostgreSQL 17을 기준으로 한다. 기존 Alembic 버전 관리 테이블은 17개에 포함하지 않는다. 업무 의미는 각 도메인, 저장 타입·키·인덱스는 이 패키지가 소유한다.

처음 읽는다면 테이블 설명과 관계 참조 안내 (아키텍처 원본 참조)에서 각 테이블의 용도와 `자식 컬럼 → 부모 테이블` 관계를 확인한 뒤 아래 상세 컬럼 명세로 이동한다.

| 문서 | 테이블 | 수 | 구현 순서 |
|---|---|---:|---|
| 인증·팀 (아키텍처 원본 참조) | users, login_attempts, refresh_sessions, workspaces, workspace_members, invitations | 6 | 첫 로그인·Workspace 수직 기능 |
| GitHub·PR (아키텍처 원본 참조) | repository_connections, rule_config_versions, pull_requests, pull_request_sync_runs | 4 | 저장소 연결·PR 동기화 |
| 분석·AI (아키텍처 원본 참조) | analysis_runs, findings, analysis_file_results, review_runs, finding_explanations | 5 | 정적 분석 후 선택적 AI |
| 실행·웹훅 (아키텍처 원본 참조) | jobs, webhook_deliveries | 2 | PR 동기화 시 jobs, 자동 접수 시 webhook |

## 공통 표기와 타입

- 표의 `N`은 NOT NULL, `Y`는 NULL 허용이다. `/`로 함께 적은 이름은 **각각 별도 컬럼**이며 같은 타입·NULL 규칙을 적용한다. 명시한 기본값 외에는 DB 기본값이 없고 생성자가 값을 제공한다.
- 모든 테이블은 공통 `id uuid PRIMARY KEY`와 `created_at timestamptz NOT NULL DEFAULT now()`를 갖는다. id는 애플리케이션에서 UUID v4를 생성한다. 다른 표에 반복하지 않는다. UUID는 접근 권한을 증명하지 않는다.
- 변경 가능한 테이블의 `updated_at timestamptz NOT NULL DEFAULT now()`는 해당 표에 명시하며 모든 UPDATE에서 애플리케이션이 갱신한다. DB가 자동 갱신한다고 가정하지 않는다. 시각은 UTC, API는 시간대 포함 ISO 8601이다.
- GitHub 숫자 ID는 `bigint CHECK (> 0)`, 내부 관계 ID는 `uuid`. PostgreSQL enum 대신 `varchar` + CHECK 허용 목록을 사용한다. 값 추가는 migration 대상이다.
- `H256` 표기는 실제 `varchar(64) NOT NULL` + `CHECK (value ~ '^[0-9a-f]{64}$')`다. NULL 허용 여부는 표를 따른다. 토큰 해시와 내용 digest는 별개의 의미다.
- `GitSHA`는 `varchar(64)` + `CHECK (value ~ '^([0-9a-f]{40}|[0-9a-f]{64})$')`다. 저장한 SHA 길이와 실제 공급자 응답의 호환성은 어댑터에서 검증한다.
- 자유 텍스트는 `text`, JSON은 `jsonb`다. JSON 최상위 타입은 CHECK, 내부 allowlist·버전·크기·민감정보는 DTO 검증으로 제한한다. 임의 원문 저장 공간으로 사용하지 않는다.
- `UQ(a,b)`는 DB UNIQUE, `IDX`는 별도 B-tree 인덱스다. 조건부 UQ는 partial unique index다. PK/UQ가 만든 인덱스를 중복 생성하지 않는다. 쿼리별 실제 실행 계획 검증은 구현 후 수행한다.

## 관계 정책: 물리 FK 0개

모든 관계 컬럼은 논리 참조다. SQL `FOREIGN KEY`/`REFERENCES`, ORM ForeignKey, 관계 강제 트리거, ON DELETE CASCADE를 생성하지 않는다. PK·UNIQUE·NOT NULL·단일 행 CHECK는 유지한다. 다른 행/테이블의 존재와 테넌트 일치를 CHECK로 보장한다고 주장하지 않는다. ADR-DATA-003 (아키텍처 원본 참조)

관계 컬럼을 바꿔 다른 Workspace로 자식을 옮기지 않는다. 부모 ID·workspace_id·연결 세대·실행 입력은 생성 후 불변이다. 재연결·재분석은 정해진 세대/새 실행 정책을 사용한다. 자식 생성 시 서버가 조회한 부모에서 workspace_id를 채우고 요청 값과 대조한다.

## 애플리케이션 무결성 프로토콜

MVP는 **Workspace별 짧은 쓰기 트랜잭션을 직렬화**한다. FK를 없애도 임의 SQL까지 관계 무결성이 보장되지는 않는다. API·Job·관리 스크립트·cleanup 모두 같은 프로토콜을 사용해야 한다.

1. 사용자 동작이면 최신 활성 user를 공개 user 계약으로 `FOR SHARE` 잠금/검증한다. 다음으로 Workspace를 `FOR UPDATE`로 잠그고 활성 상태·최신 membership·권한을 확인한다. Workspace 생성은 새 행과 OWNER membership을 하나의 트랜잭션에 삽입한다.
2. 해당 Workspace 안에서 필요한 연결→PR/설정→분석→Finding/Review 등 부모를 소유 도메인의 공개 계약으로 조회한다. 부모 존재·workspace 일치·연결 세대·허용 상태를 모두 확인한 뒤 자식을 쓴다. 확인·쓰기 사이에 commit하지 않는다.
3. 같은 Workspace의 역할 변경·연결 해제·권한 철회 처리·결과 저장·cleanup도 같은 Workspace 행을 먼저 잠근다. 사용자의 비활성화는 user 행 갱신 잠금과 충돌하도록 한다. 단순 존재 조회 후 별도 트랜잭션 insert는 금지한다.
4. 여러 사용자/Workspace를 잠글 때 각 종류의 ID 오름차순으로, user→Workspace→업무 부모→Job 순으로 잠근다. Job claim은 Job 행만 잠그고 즉시 commit한다. 그 잠금을 유지한 채 Workspace를 잠그지 않는다. 업무 RUNNING 전환/결과 저장 시에는 Workspace→업무 행→Job 순으로 fence를 다시 확인한다.
5. 외부 API·LLM·소스 분석을 기다리는 동안 이 잠금을 유지하지 않는다. 입력 확인→commit→외부 처리→새 트랜잭션에서 권한/세대/lease 재검증→결과와 Job 상태 원자적 저장으로 나눈다.
6. 전역 설치 Webhook은 Workspace 없는 기술 접수를 허용한다. 실제 업무 변경 시 등록된 연결을 조회해 Workspace 단위 프로토콜을 적용한다. 최초 로그인·Refresh는 아직 Workspace가 없으므로 user/auth 소유 트랜잭션을 사용한다.

이 직렬화는 초기 규모를 위한 보수적 선택이다. 병렬 처리량 개선은 PostgreSQL 동시성 테스트와 새 ADR을 거쳐 더 좁은 잠금으로 바꾼다. PostgreSQL 행 잠금의 실제 충돌 관계는 공식 문서 (아키텍처 원본 참조), CHECK·UNIQUE 범위는 제약 문서 (아키텍처 원본 참조)를 기준으로 한다.

## 삭제·보관·고아 데이터 점검

기간의 기준은 Privacy (아키텍처 원본 참조)다. 이 문서는 기간을 다시 정하지 않는다. workspace/user/연결 참조는 보존 중 자식이 있으면 hard delete하지 않는다. 현재 MVP는 회원·Workspace 영구 삭제 API를 제공하지 않는다.

- cleanup은 Workspace 잠금 후 실행 중/대기 Job과 그 부모를 제외한다. 삭제 후 저장하려는 worker도 같은 잠금과 부모/fence 검사에서 거부된다.
- 삭제 순서: finding_explanations → review_runs → findings·analysis_file_results → analysis_runs → pull_requests. 설정 버전은 참조하는 분석이 없을 때만 정리한다. 기술 Job은 terminal/보관 기간 조건으로 별도 정리한다.
- terminal Job의 aggregate_id는 이력 식별자이므로 업무 데이터가 먼저 만료되면 없는 대상을 가리킬 수 있다. READY/LEASED Job에는 이 예외가 없다. 과거 actor는 비활성 사용자 행을 유지하며, 외부 GitHub 작성자 ID에는 내부 users 존재를 요구하지 않는다.
- 보관 기한이 다른 부모·자식은 참조가 남은 부모를 잠시 유지한다. 예: AI 설명이 남아 있는 분석을 먼저 삭제하지 않는다. 개인정보 영구 삭제 절차는 전체 그래프를 별도로 다룬다.
- 운영 점검은 child LEFT JOIN parent로 부모 누락과 workspace/세대 불일치를 검사한다. user/membership, 연결/config/PR, 실행/result, review/finding, 활성 Job을 포함한다. 위 terminal Job 예외·외부 ID는 구분한다. 발견 시 관련 쓰기를 차단하고 트러블슈팅 기록 후 복구하며 자동 무차별 삭제하지 않는다.

## 구현 시 통과할 검증

실제 PostgreSQL에서 FK 개수 0, 지정 PK/UQ/CHECK 존재, OWNER·연결 중복 insert 경쟁, 자식 생성/부모 cleanup 경쟁, 다른 팀 ID 주입, 동시 역할 철회/결과 저장, stale worker, rollback을 검증한다. JSON 상태·범위·비밀정보 검증은 애플리케이션 테스트도 필요하다. 이 설계 문서의 링크/매핑 검사 PASS는 위 실행 검증 PASS가 아니다.
