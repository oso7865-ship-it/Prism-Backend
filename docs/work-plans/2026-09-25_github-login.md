# GitHub 로그인 구현 계획

## 작업 계약

Goal: 사용자가 로컬 브라우저에서 GitHub 로그인·프로필·새로고침 복원·로그아웃을 직접 테스트할 수 있는 인증 흐름 구현.

Goals: /api/v1/auth/github/start, callback, refresh, logout, /users/me 및 Vue 로그인 화면. User 공개 API, hash-only state/refresh, PKCE S256, Access JWT 15분/Refresh 절대 만료 7일, rotation/reuse family revoke.

Non-Goals: Workspace 서비스/권한·GitHub App·분석·AI·배포·하네스 동기화·Git 게시. 실제 GitHub 인증 동의와 로그인 수동 테스트는 사용자가 수행한다. 기존 프론트 하네스 변경은 보존한다.

읽은 계약: CORE, PACKAGE-RULES, CONVENTIONS, AUTH, USER, SECURITY, PRIVACY, EXCEPTION, HTTP-API, FRONTEND 및 DB-IDENTITY. planning/verification-loop, 프론트 ui-ux-design, Security/API/Document Gate 적용. 위험: 인증. 사용자 최신 구현 요청이 승인 근거다.

## 설계와 사전 Security Gate

- 로그인 시작: 난수 state/브라우저 바인딩(PKCE verifier) 생성. DB에는 각각 SHA256만, verifier는 10분 HttpOnly 쿠키. callback은 동일 브라우저 쿠키와 purpose/만료/미소비 조건으로 원자적 소비하고 commit 후 GitHub 호출.
- Provider: 고정 HTTPS GitHub host, TLS 검증, redirect 금지, 10초 timeout·32KiB 응답 제한, 응답 Pydantic 검증. GitHub 토큰은 /user 조회 뒤 폐기. code/state/token 및 provider 원문 오류는 로그·응답에 싣지 않는다.
- User: 공개 api.py만 호출. GitHub 숫자 ID UNIQUE를 PostgreSQL upsert로 처리하고 비활성 계정 거부. auth는 user ORM을 import하지 않는다.
- Refresh: 난수 원문은 HttpOnly 쿠키, DB hash만. family별 PostgreSQL transaction advisory lock으로 rotation/replay/logout을 직렬화한다. 교체된 토큰 재사용 시 전체 family 철회를 commit한 뒤 401. 절대 만료 유지. Access 만료 전 잔존은 기존 계약대로 최대 15분, /me는 사용자 활성 상태 확인.
- CSRF: refresh/logout은 정확한 PUBLIC_APP_ORIGIN과 X-PRism-CSRF: 1 헤더 둘 다 요구. CORS 개방 없음. 반환 경로는 / 하나만 허용. JWT는 HS256/issuer/audience/필수 claims 검증.
- 로컬 예외: 등록된 http://localhost:8000 콜백 → http://localhost:5173 복귀. 같은 localhost 호스트 쿠키 + Vite /api 프록시. HTTP 개발에서만 Secure=false, HttpOnly/SameSite=Lax/Path=/ 유지. 설정은 localhost/127.0.0.1 고정 로컬 출처만 허용하고 app_env는 계속 development/test만 지원한다. 배포용 쿠키/프록시 검증은 별도다.
- 설정 누락 시 auth만 503. health 기반 실행은 유지. production 시작은 기존대로 거부. 공통 오류 handler는 validation input과 DB/HTTP 원문을 숨긴다.

사전 Gate: 설계 PASS(인증 주체·입력·CSRF·외부 요청·오류·비밀값 경계 정의 완료). 사후 결과는 실제 검사 후 별도 기록.

## UI 흐름

기존 Home 화면에 GitHub 로그인 링크 → 대기/취소/오류 안내 → 이름·login·로그아웃을 표시한다. Vue는 access를 메모리에만 보관하고 refresh는 single-flight로 공유한다. 로그아웃 실패를 성공으로 표시하지 않는다. 키보드 가능한 기본 링크/버튼, aria-live 오류·진행, 기존 색상/폭/모바일 스타일을 유지한다. 새로운 UI 라이브러리는 필요 없다.

## 체크리스트

- [x] A01 설정·JWT·외부 GitHub 경계와 공개 User API 구현.
- [x] A02 state/PKCE·callback·refresh/replay/logout 트랜잭션 구현.
- [x] A03 API 조립·오류/쿠키/CSRF 정책 구현.
- [x] F01 로그인 화면·메모리 세션·single-flight·오류/재시도 연결.
- [x] T01 변조·만료·브라우저 바인딩·재사용·origin·비활성 계정 자동 테스트.
- [x] T02 실제 테스트 PostgreSQL에서 동시 로그인·rotation/replay 및 rollback 검증. GitHub는 MockTransport로 격리.
- [x] T03 Ruff/mypy/pytest 및 프론트 typecheck/build/test.
- [x] D01 실행·수동 테스트 가이드·Report·작업 큐 갱신.
- [x] 사용자: 실제 GitHub 로그인·프로필·새로고침 유지·로그아웃 정상 확인(사용자 보고).
