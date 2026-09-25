# 작업 리포트: GitHub 로그인·세션 API

> 작성일: 2026-09-25
> 작업 브랜치: main
> 커밋/PR: 8a07a7008ef576b721b1a4a17377e9ac1e5b5945 (main 직접 게시)
> 상태 기록 버전: 1
> 상태 확인 시각: 2026-09-26T00:32:07+09:00
> 구현 상태: 완료
> 구현 근거: 사용자 로그인 구현 요청 및 AUTH/USER/FRONTEND 계약
> 로컬 검증 상태: 완료
> 로컬 검증 대상: GitHub 로그인 미커밋 working-tree
> 로컬 검증 근거: Ruff/mypy, 전체 pytest 47 passed(실제 PG·GitHub MockTransport), Windows 네이티브 진단은 §5 참조
> 병합 상태: 완료
> 병합 대상: origin/main
> 병합 근거: 사용자 요청에 따라 8a07a7008ef576b721b1a4a17377e9ac1e5b5945을 origin/main에 일반 push 완료
> 배포 상태: 해당 없음
> 배포 근거: 로컬 개발 단계
> 실제 연동 상태: 완료
> 실제 연동 근거: 사용자 화면에서 실제 로그인·프로필·API/DB 연결 확인, 이어 새로고침 유지와 로그아웃 후 새로고침 모두 정상이라고 사용자 확인. 취소/다중 계정/운영 연동까지 검증한 것은 아님
> 작업 범위: L
> 적용 스킬: planning, verification-loop, ui-ux-design, troubleshooting-report
> 적용 Gate: Security Gate, API Gate, Document Gate, UI/UX Gate
> 위험도: 인증
> 위험 작업 여부: 예

## 0. 작업 범위 확인

GitHub 로그인·프로필·세션 갱신·로그아웃을 구현한다. Workspace/GitHub App/분석/AI/운영 배포는 제외. 기존 로컬 하네스 패치 보존, 동기화 없음. 실제 OAuth 로그인은 사용자가 수행했고 기본 로그인·복원·로그아웃 정상 결과를 확인했다.

## 1. 작업 요약

로그인 시작→state/브라우저 바인딩·PKCE→사용자 upsert→Refresh 쿠키→프론트 메모리 Access→/users/me. 15분 Access, 7일 절대 Refresh 만료, 원자적 rotation과 replay family 철회. Origin+CSRF 헤더, host-only HttpOnly 쿠키, 민감 응답 no-store, provider 오류 마스킹.

## 2. 변경 파일

app/domain/auth·user, shared/security·exception·config, main.py, pyproject.toml/uv.lock, config 예시, tests/conftest.py·test_auth.py, 계획·수동 테스트 문서 및 상태 기록. 추가 DB migration 없음.

## 3. 검증 결과

- 백엔드: Ruff check/format, mypy 42 files PASS. 전체 47 tests PASS, GitHub HTTP는 MockTransport만 사용. 실제 테스트 PG에서 동시 로그인 유일성·동시 refresh/replay·세션 family 분리·만료·비활성 계정·CSRF·PKCE·state 재사용·Provider 실패/시간/크기 제한 확인.
- 프론트: typecheck/build PASS, 테스트 8개 PASS(single-flight·expired access retry·실패 표시·refresh 중 logout 순서 포함).
- 개발 서버 HTTP 확인: localhost:8000 /health/ready 및 localhost:5173의 화면·프록시 readiness 200. Vite /api/v1/auth/refresh는 올바른 Origin/CSRF 전달 후 비로그인 401(no-store). 서버는 사용자 수동 테스트용으로 실행 중.
- 문서/참조/상태/adapter 검사 및 실제 로컬 비밀값의 새 코드·문서 포함 여부 검사 PASS.
- 실제 GitHub 기본 흐름은 사용자 확인 완료. 운영 배포 미수행, 이번 원격 CI는 게시 후 확인한다.

## 4. Checklist 결과

Security/API Gate: 구현·자동 검증 범위 PASS. User 모델은 공개 UserAPI를 통해 접근, shared→domain 없음, 토큰 원문 DB 저장 없음, provider 고정 HTTPS/TLS·timeout·응답 검증, 외부 요청 중 DB lock 미보유. HTTP 로컬에만 Secure=false이며 설정이 로컬 출처와 development/test로 제한된다.

UI: 기존 스타일 유지, 로그인 primary link·프로필·로그아웃·취소/실패/재시도·로딩/disabled·aria-live 및 작은 화면 줄바꿈 구현. 실브라우저 기본 로그인 흐름은 사용자 확인 완료이며 전체 접근성·다중 화면 검수를 완료했다고 표현하지 않는다.

## 5. 발견된 문제

### Docker 런타임 소켓 때문에 로컬 DB 시작 실패

- 어디서: 2026-09-25 KST Windows Docker Desktop 4.85.0 시작, 로컬 테스트 전.
- 무엇: dockerInference 및 Secrets Engine engine.sock을 제거할 수 없어 엔진이 시작되지 않음. DB 볼륨은 보존.
- 어떻게: CLI 연결 실패 → 기존 설치 시작 → backend 로그에서 런타임 소켓 오류 확인. 한 폴더만 옮기면 다른 소켓 오류로 실패하고 앞선 소켓도 다시 남음.
- 왜: 남은 AF_UNIX 런타임 소켓 재사용 실패가 로그로 확인됨. OS 내부의 최초 발생 원인은 미확정. [Docker 동일 증상 보고](https://github.com/docker/desktop-feedback/issues/460)는 참고이며 원인 확정 근거를 대체하지 않음.
- 해결: 실패 프로세스 종료 후 두 런타임 폴더를 동시에 .prism-backup-타임스탬프 이름으로 보존하고 재시작. compose의 기존 DB가 healthy로 복구. DB/설정/볼륨 삭제·factory reset 없음. 백업은 %LOCALAPPDATA%/Docker/run.prism-backup-* 및 %LOCALAPPDATA%/docker-secrets-engine.prism-backup-*에 남음.
- 앞으로: 재발 시 사용자/후속 담당자가 정상 종료·소켓 오류 로그부터 확인. 임의의 볼륨 초기화 금지. 복구 완료 기준은 compose healthy 및 실제 DB 연결. 이번 기준 충족.

### Windows DB 테스트 네이티브 진단

- 어디서: 전체 pytest 실행 중 Psycopg 동기 연결/select·fixture 정리 경로.
- 무엇: Windows fatal exception: access violation 스택이 출력됐으나 프로세스는 계속 실행되어 최종 47 passed, exit 0.
- 어떻게: 전체 테스트에서 간헐적으로 재현. 인증 테스트를 별도 실행했을 때는 같은 출력이 관측되지 않았음(그 실행의 테스트 삽입 실수 1건은 파일 위치 수정 후 전체 통과).
- 왜: 미확정. Python/Psycopg/Windows 네이티브 경계 진단이며 이를 단순 무해 경고라고 확정하지 않음.
- 해결: 원인 미해결. 진단을 숨기거나 pytest faulthandler를 비활성화하지 않았다. 테스트 성공과 네이티브 안정성 확인을 구분한다.
- 앞으로: 후속 담당자(미정)가 반복 발생 시 최소 재현과 런타임 버전 조합을 조사. 운영 안정성 완료 주장 금지. 기존 Starlette/httpx deprecation 경고도 별도 유지.

## 6. 미해결 항목

로그인 취소·다중 계정 등 확장 수동 체크, Windows 네이티브 진단 원인, 다중 탭 간 refresh 동기화(현재 한 탭 single-flight), 운영 HTTPS/Secure/프록시 검증, 로컬 OAuth 키 배포 전 교체. Workspace는 다음 단계다. 게시 완료. CI 결과는 아래 게시 기록을 따른다.

## 7. Working Context 반영 여부

최신 Report 포인터와 작업 큐에 로그인 구현 및 사용자 기본 흐름 확인 완료를 반영했다. 이전 상태 요약은 history에 보존. 기존 사용자 하네스 패치와 Working Context 갱신은 로컬에만 보존하고 이번 커밋에서 제외한다. 게시되는 최신 상태는 루트 reports/_LATEST.md를 따른다. 원본/다른 저장소 동기화는 수행하지 않았다.

## 8. 다음 작업

게시·CI 확인 후 다음으로 Workspace·멤버·초대 서비스와 논리 참조·권한 검증.

## 9. 2026-09-26 게시 기록

사용자 기본 로그인 테스트 확인 후 백엔드·프론트 각각 main 게시. 자동 승인 검토가 하네스 변경을 포함한 게시를 거절하여 게시 범위를 로그인 구현과 제품 문서로 축소했다. GENERAL_HARNESS·PROJECT_HARNESS 및 기존 트러블슈팅 스킬 리포트 변경은 로컬에 보존하고 이번 게시에서 제외한다. 실제 비밀값·.env·DB 볼륨 제외. 구현 커밋 8a07a7008ef576b721b1a4a17377e9ac1e5b5945 일반 push 완료.

GitHub Actions 전체 PASS: https://github.com/oso7865-ship-it/Prism-Backend/actions/runs/36155289198 (Linux 테스트·migration 왕복·정적 검사·문서 검사 포함). Windows 네이티브 진단 원인은 별도 미해결이다.
