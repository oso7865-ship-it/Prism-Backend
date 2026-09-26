# 작업 리포트: PR 분석 실행·정적 분석기

> 작업 범위: M
> 형식 상태: legacy
> 과거 적용 스킬 기록: 미확인 (이전 본문에 남은 적용 기록만 유효)
> 적용 Gate: 기존 본문 검증 범위 참조; 새 Gate 수행을 소급 주장하지 않음
> 위험도: 일반 (기록 형식 정정; 과거 작업 위험은 본문 참조)
> 로컬 검증 근거: 기존 본문 변경·검증 기록을 기준으로 형식 정정; 새 실행 증거 아님
> 실제 연동 상태: 미확인
> 로컬 검증 대상: 과거 보고서 작성 당시 working-tree (본문 기록)
> 형식 정정: 2026-09-26 게시 준비 중 누락 헤더 정리. 과거 검증을 재실행한 것으로 간주하지 않음.

> 작성일: 2026-09-26
> 작업 브랜치: dev
> 커밋/PR: 미커밋 (기존 작업 변경도 함께 존재)
> 상태 기록 버전: 1
> 상태 확인 시각: 2026-09-26T05:25:22+09:00
> 구현 상태: 완료
> 이전 구현 요약: 완료 (아래 초기 범위)
> 구현 근거: 현재 working-tree
> 로컬 검증 상태: 완료
> 이전 로컬 검증 요약: PASS / Windows 네이티브 진단 WARN 별도
> 병합 상태: 미수행
> 이전 병합 요약: 미병합
> 원격 CI: 이번 변경 미실행
> 배포 상태: 미수행
> 이전 배포 요약: 로컬만 적용

## 0. 작업 범위 확인
사용자 1번 분석 실행/결과와 2번 정적 분석기를 함께 구현. 계획→설계→구현→검증→기록. backend/frontend dev, architecture main. 하네스 원본 동기화·AI·GitHub 댓글·커밋/푸시·운영 배포는 범위 밖.

## 변경과 근거
- docs/work-plans/2026-09-26_static-analysis.md에 사전 계약과 체크리스트 기록.
- app/domain/analysis: ORM 3개·API·서비스·worker·고정 SHA 파일 취득·Tree-sitter 구문 분석·별도 parser 프로세스. domain 간 접근은 공개 api.py로 제한.
- migrations/versions/0005_static_analysis.py: frozen SQL로 3개 테이블 추가, 업무 총15테이블, 물리 FK0. 기존 데이터 삭제 없음.
- 일반 요청 멱등 키, 명시적 rerun generation, 원자적 run+Job, workspace 권한/연결 세대/lease fence 재검증. 본인·관리자 취소.
- 4언어 23규칙만 활성. 원문·비밀 값 없이 위치와 고정 메시지 저장. 파일 검사 실패·지원 범위·규칙 미평가를 별도 제공.
- config 예시 기본OFF; 실제 ignored .env만 ANALYSIS_RUNNER_ENABLED=true. 로컬 migration과 서버 재시작 완료.

## 검증 결과
| 검증 | 결과 |
|---|---|
| 전용 prism_test PostgreSQL 전체 pytest | 134 passed, exit0; Starlette deprecation 1 warning, Windows native access violation 진단 별도 발생 |
| parser 취소 kill/reap 테스트 추가 후 규칙 suite | 42 passed (전체 실행 이후 새 테스트1 추가; 현재 총135개, 전체 재실행은 안 함) |
| Ruff check / format | PASS, 116 files formatted |
| mypy app | PASS, 100 source files |
| 0005 migration 왕복/스키마 FK | 통합 suite PASS |
| 실제 개발 DB alembic upgrade head / check | 적용 완료 / No new upgrade operations detected |
| 프론트 최종 build / vitest | PASS / 23 passed |
| Architecture validate_docs.py | PASS; 기존 RELATIONS.md 길이 안내 WARN |
| 실제 조직 PR #47 | COMPLETED + FULL_SCOPE, 1파일, COM-002 1건, 46–137줄 |
| 실제 재분석 | 같은 head c5811bf1048b, generation1 완료; 새 이력 추가 |

동시 접수 2개가 같은 run을 반환하고 Job 1개를 생성함을 검증했다. 큐/lease 후 취소, source 취득 중 취소/연결 철회/원격 snapshot 변경은 결과 저장 없이 종료한다. 일시 오류3회 소진, symlink/size/truncated tree/blob hash mismatch/구문 오류, 교차 테넌트, cap/1-based 위치/원문 비직렬화도 검사했다.

## 트러블슈팅 1: Windows 파서 프로세스 실행
- 어디서: app/domain/analysis/parser_process.py, Windows/Psycopg SelectorEventLoop, 2026-09-26 KST.
- 어떤 문제: 실제 parser 실행이 NotImplementedError로 실패해 통합 분석이 ANALYSIS_FAILED가 됨.
- 어떻게 발생: asyncio.create_subprocess_exec를 Selector loop에서 호출했음. 단독 기본 loop 테스트에서는 발견되지 않음.
- 왜: Windows SelectorEventLoop는 asyncio subprocess transport를 지원하지 않음. DB 드라이버 때문에 loop 자체 교체는 맞지 않음(원인 확인).
- 해결: subprocess.Popen + asyncio.to_thread communicate, timeout 및 취소 시 kill/reap. 격리된 환경/pipe와 stderr 차단 유지. 통합 및 실제 Java PR 완료, 취소 child 종료 테스트 PASS.
- 앞으로: Windows CI에서 동일 loop 통합 검사 유지. 배포 시 컨테이너 자원 제한/네트워크 격리 강화는 운영 단계 후속. 현재 프로세스 분리가 완전한 OS sandbox는 아님.

## 트러블슈팅 2: 기존 Windows 네이티브 진단 재발
- 어디서: 전체 pytest의 Windows/DB TestClient 실행 중.
- 어떤 문제: Windows fatal exception: access violation 진단이 출력됨. pytest는 계속 진행해 134 passed, exit0으로 종료됨.
- 어떻게 발생: PostgreSQL 연결을 쓰는 전체 회귀에서 재발. 과거 Webhook Report에도 기록된 이슈.
- 왜: 정확한 네이티브 원인 미확인. Psycopg/Windows 이벤트 루프 경계가 기존 조사 대상이며 확정 원인으로 단정하지 않음.
- 해결: 이번 작업에서 해결하지 않음. 테스트 통과와 진단을 별개로 기록하며 숨기지 않음.
- 앞으로: 담당자 미정. 운영 전 Linux CI 동일 suite 및 Windows 드라이버 최소 재현/버전 비교로 원인 확인. 완료 기준은 동일 재현에서 네이티브 진단 제거.

## 남은 범위
DeepSeek Review/비용·모델 정책, 고급 제안 규칙15개, 사용자 규칙 설정, Vue SFC/타입·데이터 흐름 분석, 공개 Webhook 실제 전송 및 운영 배포. 지원 언어에서도 활성 구문 규칙 검사만 하며 보안 무결성 보증이 아니다. GitHub PR이 움직인 과거 snapshot의 임의 diff 재구성은 미지원이다.

## 판정과 인계
초기 분석 실행과 정적 규칙 기능은 로컬 구현·실계정 검증 완료. Windows 진단은 미해결 WARN으로 유지. 문서/설계의 38개 제안을 전체 구현했다고 표현하지 않는다. 자격증명은 ignored .env에만 유지하며 게시하지 않았다. 다음 PC 이동 전에 사용자가 요청하면 관련 dev/main 변경을 검토 후 커밋·푸시해야 한다.

## 후속: DeepSeek 키 입력 자리 준비

사용자 요청으로 ignored `.env`와 config/development.example에 `DEEPSEEK_API_KEY=` 자리를 마련하고 Settings에 SecretStr 필드를 추가했다. 기존 값은 보존했다. 설정 로드·repr 마스킹·Ruff·.env Git 제외 확인 PASS. AI_ENABLED=false 유지, 실제 DeepSeek 호출/서버 재시작 없음.

## 후속: LangChain 패키지 설치

사용자 명시 요청으로 uv add langchain langchain-deepseek 실행. pyproject.toml/uv.lock 및 로컬 가상환경 반영 완료. langchain 1.4.2, langchain-core 1.6.5, langchain-deepseek 1.1.1. uv pip check 및 ChatDeepSeek import PASS. AI_ENABLED=false 유지, 모델 호출 없음. 다른 PC에서는 uv sync --locked로 재현한다.
