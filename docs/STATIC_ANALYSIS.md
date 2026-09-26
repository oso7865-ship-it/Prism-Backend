# 정적 분석 실행

## 실행과 확인
`uv sync --locked` → `uv run alembic upgrade head` → ignored `.env`의 `ANALYSIS_RUNNER_ENABLED=true` → 서버 재시작. GitHub App Contents/Pull requests 읽기 권한과 설치된 저장소 연결이 필요하다. AI 키는 필요 없다. Windows는 README의 Selector loop_factory 실행 명령을 유지한다.

클라이언트: 저장소와 PR → 저장소 → PR → 현재 PR 분석. `PENDING → RUNNING → COMPLETED`와 검사 범위를 확인한다. 본인 요청 또는 OWNER/ADMIN이 취소할 수 있다. 최근 50개 이력과 같은 커밋 재분석을 지원한다. COMPLETED는 오류 0개 보증이 아니며 PARTIAL/NONE과 파일별 제외 사유를 함께 읽는다.

## API
모든 경로는 `/api/v1/workspaces/{w}` 아래이며 Bearer 인증과 팀 권한을 검사한다.

| 경로 | 계약 |
|---|---|
| POST /analyses | `{pr_id, rerun_of?}`; 202, 고정 SHA/설정/규칙/실행기 기준 중복 요청은 기존 run 반환 |
| GET /pull-requests/{p}/analyses | 최신 50개, active_rules와 runner_enabled |
| GET /analyses/{a} | 상태·통계·SHA·coverage·공개 오류 코드 |
| GET /analyses/{a}/files | 100개와 next_cursor, 파일별 상태·평가 규칙 |
| GET /analyses/{a}/findings | 중요도 우선/동일 중요도 ID 순, 100개와 next_cursor |
| POST /analyses/{a}/cancel | 본인 또는 관리자; terminal에 멱등 |

최초 요청 generation0, 명시적 rerun은 같은 base/head에 현재 규칙·설정으로 generation 증가. GitHub가 그 PR의 base/head를 바꾼 경우 SNAPSHOT_CHANGED로 실패하며 PR 재동기화 후 현재 PR 분석을 사용한다. 과거 임의 diff 재구성은 지원하지 않는다. 연결 해제/팀 접근 철회/lease 상실/취소 후 늦은 결과는 저장하지 않는다.

## 활성 범위
Rule set `static-1.1.0`, 규칙별 버전 `1.0.0`. 제안 38개 중 아래 29개가 활성이다.

| 영역 | 활성 규칙 | 내용 |
|---|---|---|
| 공통 | COM-001,002,003,004,009,010 | 500줄 파일, 60줄 함수, 조건/반복 중첩4 초과, 인수 5개 초과, credential 형식, private key 블록 |
| Java | JAVA-004,005,006,007,008 | 빈 catch, wildcard import, 빈 반복문, public static 비final 필드, 문자열 literal 참조 비교 |
| Python | PY-001,002,003,004,005,006,008 | mutable literal 기본 인수, bare except, pass except, eval/exec, wildcard import, 포괄 except |
| JavaScript | JS-001,002,003,004,005,006 | var, 느슨한 비교(null 비교 제외), debugger, 빈 catch, eval/Function |
| TypeScript | TS-001,002,003,004,005 | any, ts-ignore, ts-nocheck, non-null assertion, 이중 assertion |

Tree-sitter가 선언/구문 구조를 검사하며 사용자 코드를 실행하거나 패키지를 설치하지 않는다. 심볼 해석·타입 검사·데이터 흐름·프레임워크 의미 분석은 지원하지 않는다. 설정의 rules/layer_mappings 변경은 CONFIG_UNSUPPORTED로 거부한다. ignored_paths는 구문 규칙에 적용되고 비밀 형식 검사는 유지된다.

## 제한과 저장
최대 첫 100개 변경 파일, 파일당 200KiB, 합계 2MiB, run 120초, parser 5초, 파일당 finding 100개. 결과에는 파일 경로·줄·고정 메시지·코드만 저장한다. 원문은 메모리/프로세스 pipe로만 전달하고 DB/로그/임시 파일에 저장하지 않는다. 이는 OS 보안 sandbox 전체를 제공한다는 의미는 아니다.

삭제·바이너리·LFS·심볼릭 링크·용량 초과·파서 실패를 기록한다. Vue SFC는 미지원이다. 미지원 텍스트/선언 파일/생성 파일은 비밀 형식 검사만 가능하며 전체 구문 검사로 표시하지 않는다. 지원 언어 파일이 없으면 NONE, 일부 미평가/제한은 PARTIAL이다. diff patch가 완전하지 않으면 CONTEXT로 표시해 새 결함으로 단정하지 않는다.

## 검증
규칙별 위반2·정상2·유사정상1 이상 fixture, 4언어 구문 오류, 프로세스 timeout, PostgreSQL 통합 권한/경합/취소/재시도/snapshot 변경/연결 철회/마이그레이션 테스트를 실행한다. 실제 증거와 미해결 환경 이슈는 최신 Report에 기록한다.

## 규칙 확장 (static-1.1.0)

기존23개에 COM-003(조건/반복 깊이>4), PY-004/005(내장 eval/exec 직접 호출), PY-008(포괄 except), JS-005/006(eval/Function 동적 코드 생성)을 추가한29개다. 이름 바인딩·동적 변경을 확신할 수 없으면 해당 규칙 NOT_EVALUATED/BINDING_UNRESOLVED, 파일 범위 PARTIAL이다. 파일 안의 다른 이름 사용까지 보수적으로 제외하며 전역 타입/심볼 해석은 하지 않는다. 런타임 monkey patch와 외부 주입은 검증하지 않는다. PY-003과 PY-008 중복은 제외한다. 함수 경계에서 깊이를 초기화하며 else-if/elif는 같은 깊이로 취급한다. 새6규칙은 version1.0.0이고 기존 규칙 버전은 유지한다. 나머지9개 후보는 비활성이다.
