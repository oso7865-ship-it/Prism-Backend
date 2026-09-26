# 로컬 GitHub 로그인 확인

## 준비

이 문서의 실행 예시는 로컬 개발용이다. 프론트와 콜백을 모두 **localhost**로 연다. localhost와 127.0.0.1을 브라우저 주소에서 섞으면 로그인 바인딩 쿠키를 공유하지 못한다.

GitHub OAuth App: Homepage `http://localhost:5173`, Redirect URI `http://localhost:8000/api/v1/auth/github/callback`. wildcard·Device Flow는 끈다. 로그인용 OAuth App과 저장소 접근용 GitHub App은 별도다. GitHub 만료 access/refresh를 받아도 사용자 확인 후 둘 다 보존하지 않으며 PRism 자체 세션을 사용한다.

`.env`에 다음을 설정한다. 현재 PC에는 전달받은 로컬 OAuth 값과 별도로 생성한 JWT 서명키를 설정했다. 키를 README나 프론트 `.env`에 복사하지 않는다. 이 로컬 OAuth Secret은 사용자 요청에 따라 유지하며 배포 전 폐기·교체한다.

```dotenv
AUTH_ENABLED=true
PUBLIC_APP_ORIGIN=http://localhost:5173
PUBLIC_API_ORIGIN=http://localhost:8000
GITHUB_OAUTH_CLIENT_ID=발급한_ID
GITHUB_OAUTH_CLIENT_SECRET=발급한_Secret
JWT_SIGNING_KEY=32바이트_이상의_독립된_난수_서명키
```

DB 설정은 [로컬 PostgreSQL](database/LOCAL_POSTGRES.md)을 따른다. AUTH_ENABLED=false 또는 키/DB 설정 누락 시 로그인은 503이고 health 기능은 계속 사용할 수 있다. APP_ENV=production의 HTTPS·Secure cookie·TLS 설정은 [배포 전 준비](PREDEPLOYMENT.md)를 따른다. 공개 환경의 실제 OAuth 검증은 별도다.

## 실행

백엔드 저장소에서:

```bash
uv sync --locked
docker compose up -d --wait db
uv run alembic upgrade head
uv run uvicorn app.main:create_app --factory --loop app.shared.database.event_loop:loop_factory --reload --no-access-log
```

프론트 저장소의 별도 터미널에서:

```bash
npm ci
npm run dev
```

브라우저에서 **http://localhost:5173**을 연다. Vite가 `/api`를 백엔드로 전달하고 로그인 callback만 등록한 8000 포트로 돌아온다. 호스트가 동일하므로 쿠키는 두 포트에서 공유된다. 포트 점유 오류가 있으면 기존 프로세스를 확인하고, 주소를 임의로 바꿔 등록값과 어긋나게 만들지 않는다.

## 직접 테스트 체크리스트

- [ ] 연결 확인 → API와 DB 연결 완료.
- [ ] GitHub로 로그인 → 동의 화면 → localhost:5173 복귀 → 이름/@login 표시.
- [ ] 새로고침 → 로그인 상태 유지.
- [ ] 로그인 상태 확인 → 프로필 표시 유지.
- [ ] 로그아웃 → 로그아웃 안내 → 새로고침해도 비로그인 유지.
- [ ] GitHub 동의 취소 → 취소 안내, 다시 로그인 가능.
- [ ] 새 시크릿 창에서 로그인 → 기존 계정을 중복 생성하지 않음.
- [ ] DevTools Application: localStorage/sessionStorage에 인증 토큰 없음. refresh는 HttpOnly, SameSite=Lax, host-only 쿠키.
- [ ] 다른 Origin/CSRF 헤더 없는 refresh·logout 호출 → 403. Origin 검사를 단순 curl로 우회해 실제 사용자 인증이 된다고 해석하지 않음.

HTTP 로컬 개발에 한해서 쿠키 Secure=false다. 실제 배포에서는 HTTPS/Secure·동일 출처 callback proxy·Origin·캐시·cookie 전달을 별도 검증해야 한다. 이 구현은 그 운영 검증을 완료했다고 주장하지 않는다.

## 엔드포인트

| 경로 | 동작 |
|---|---|
| GET /api/v1/auth/github/start | GitHub authorize로 302, return_path는 /만 허용 |
| GET /api/v1/auth/github/callback | state/바인딩/PKCE 검증 후 refresh cookie와 프론트 302 |
| POST /api/v1/auth/refresh | rotation, access_token/token_type/expires_in 반환 |
| POST /api/v1/auth/logout | 현재 로그인 family 철회 및 쿠키 삭제, 204 |
| GET /api/v1/users/me | Authorization: Bearer access JWT로 현재 활성 프로필 조회 |

refresh/logout은 `Origin: http://localhost:5173`과 `X-PRism-CSRF: 1`을 둘 다 요구한다. 프론트가 자동으로 설정하며 Origin은 브라우저가 보낸다. Access는 15분, Refresh family는 최초 발급부터 7일(갱신해도 연장하지 않음). 사용한 refresh 재사용은 family 전체를 철회하므로 여러 탭이 동시에 갱신하면 재로그인이 필요할 수 있다. 현재 single-flight는 한 탭 안에 적용된다.

## 오류 확인

- 503: Docker/DB readiness, AUTH_ENABLED, OAuth 키, JWT_SIGNING_KEY 확인.
- 로그인 실패: 등록 callback 주소, 브라우저 localhost 일치, 쿠키 허용 여부를 확인하고 처음부터 다시 시도.
- 403: 프론트 origin 일치·CSRF 헤더 확인. 전체 Origin 허용으로 바꾸지 않음.
- GitHub code/state/token, 쿠키 원문, `.env` 전체를 오류 스크린샷·로그·Report에 붙이지 않음.

백엔드 자동 테스트는 GitHub HTTP를 MockTransport로 격리한다. 실제 GitHub 동의·계정 로그인 결과는 사용자가 위 체크리스트로 확인한다.
