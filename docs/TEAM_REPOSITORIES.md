# 팀·GitHub 저장소 연결 실행 및 테스트

## 현재 범위
Workspace 생성/목록, 멤버 목록·초대·가입·제거/탈퇴·역할 변경·소유권 이전, GitHub App 저장소 연결/해제, 최근 30개·페이지·단건 PR sync, 영속 Job 재시도/lease 복구, PR metadata·기존 리뷰 상태/커밋 목록을 구현했다. 리뷰/코멘트 원문과 코드 조각은 GitHub 링크에서 확인한다. 자동 분석·AI·Webhook·규칙 설정 편집은 후속 단계다.

## DB와 서버
기존 로그인용 .env를 유지하고 `uv sync --locked`, `uv run alembic upgrade head`를 실행한다. revision 0003은 기존 데이터 변경 없이 테이블 5개를 추가한다. 총 11개 업무 테이블, 물리 FK 0개.

```powershell
uv run uvicorn app.main:create_app --factory --loop app.shared.database.event_loop:loop_factory --host 127.0.0.1 --port 8000 --no-access-log
```

프론트는 npm ci 후 npm run dev. http://localhost:5173 로 접속한다. 테스트용 키가 없으면 팀 기능만 사용할 수 있다. App 설정 상태 API는 비밀값을 반환하지 않는다.

## GitHub App 등록 (로그인용 OAuth App과 별도)
GitHub Settings → Developer settings → GitHub Apps → New GitHub App에서 등록한다.

- 이름: GitHub 전체에서 유일한 이름, 예: PRism Local + 사용자 구분값.
- Homepage: http://localhost:5173
- Callback URL: http://localhost:8000/api/v1/github-app/callback
- 사용자 인증은 web application flow, device flow는 사용하지 않는다. 설치 후 OAuth 사용자 인증을 자동 요청하는 설정은 끄고 앱 화면의 연결 버튼에서 시작한다.
- Repository permissions: Metadata read, Contents read, Pull requests read, Issues read. 쓰기 권한 요청 없음. Account/Organization 추가 권한 불필요.
- Webhook: 이번 단계는 비활성. Webhook 수신·자동 분석은 후속 구현이다.
- 초기에는 본인 계정/Organization의 선택한 저장소만 설치한다. Organization 승인 대기는 설치 완료가 아니다.
- App ID, App slug, Client ID, 생성한 Client secret, 생성한 private key를 로컬 .env에 설정한다. 이 키는 로그인용 OAuth ID/secret과 다르다.

```dotenv
GITHUB_APP_ID=123456
GITHUB_APP_SLUG=your-unique-app-slug
GITHUB_APP_CLIENT_ID=your-app-client-id
GITHUB_APP_CLIENT_SECRET=your-local-app-secret
GITHUB_APP_PRIVATE_KEY="PEM 파일 내용을 한 줄로 넣고 줄바꿈을 \n으로 표현"
SYNC_RUNNER_ENABLED=true
```

위 값은 설명용이며 실제 키가 아니다. PEM은 Git에 추가하지 않는다. 키를 설정한 뒤 API를 재시작한다. 앱은 설정이 완성되기 전 연결을 503으로 거절한다. SYNC_RUNNER_ENABLED=true는 영속 sync를 처리하는 단일 embedded runner를 활성화한다. 서버 프로세스/worker 수는 1로 유지한다.

## 사용자 수동 테스트
1. 로그인 후 팀 생성. 다른 계정으로는 내 팀 목록/리소스에 접근할 수 없어야 한다.
2. 초대받을 계정의 '내 계정'에 표시된 GitHub 숫자 ID를 입력. 초대 토큰은 생성 직후 한 번만 표시한다. 링크는 URL fragment를 사용한다. 대상자는 먼저 로그인한 뒤 링크를 열거나 토큰을 입력한다.
3. MEMBER는 팀 조회만 가능하고 초대·연결 관리 버튼이 없어야 한다. OWNER가 ADMIN으로 바꾸면 MEMBER 초대/제거·저장소 관리가 가능해진다. ADMIN 승격/소유권 이전은 OWNER만 가능하다.
4. 초대 만료/취소/재사용과 다른 GitHub 계정의 수락은 거절된다. OWNER는 소유권 이전 전에 탈퇴할 수 없다.
5. GitHub App 설치 링크에서 선택한 저장소에 App을 설치한다. 팀 화면에 owner/repository 입력 후 GitHub 권한 확인을 진행한다. 로그인한 PRism 계정과 다른 GitHub 사용자로 인증하면 실패한다. GitHub 저장소 관리자여야 한다.
6. 연결 후 PR 보기→상태 확인 또는 수동 동기화. 최근 갱신 PR 30개, 이전 페이지, PR 상세와 리뷰 상태를 확인한다. 원문은 GitHub에서 본다. 초기 sync는 분석/AI를 만들지 않는다.
7. App 권한 철회 후 동기화는 실패하고 저장소는 SUSPENDED가 된다. 연결 해제 후 새 sync는 거절된다. 재연결은 같은 연결 ID의 generation을 증가시킨다.
8. 서버 중단 뒤 재시작하면 만료 lease를 회수한다. 현재 실행자 권한과 연결 세대를 다시 검증한다. 오래된 worker의 결과는 fence로 거절한다.

## 현재 한계와 다음 작업
GitHub App 실계정 연결과 테스트 PR #1 조회는 확인했다. 리뷰·코멘트·커밋 API는 각 호출 최대30개와 다음 페이지를 제공하며 UI는 첫30개를 표시하고 나머지는 GitHub로 안내한다. 앱 내부 목록은 최대1,000개까지 로드한다. 설치 철회 Webhook과 SYSTEM sync는 구현했으며 실제 GitHub Webhook 활성화는 공개 수신 주소가 필요하다. 분석 Worker·AI·공개 배포는 다음 단계다. 취소 가능한 sync API와 원문 코멘트 렌더링 UI는 이번 범위에 포함하지 않았다.

공식 근거: [App user token/PKCE](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-a-user-access-token-for-a-github-app), [GitHub App REST](https://docs.github.com/en/rest/apps/apps).
