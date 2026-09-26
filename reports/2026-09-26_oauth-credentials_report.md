# OAuth 로그인 실패 진단

> 작성일: 2026-09-26
> 작업 브랜치: dev
> 커밋/PR: 미커밋
> 작업 범위: M
> 적용 스킬: troubleshooting-report
> 적용 Gate: Security Gate, API Gate, Document Gate
> 위험도: 보안

## 0. 작업 범위 확인
사용자가 로그인 실패 화면을 전달하여 기존 로컬 OAuth 연동을 진단했다. UI 로그인 재실행·신규 자격증명 생성·권한 변경은 하지 않았다. DB 최근 로그인 시도의 시각/소비 여부와 GitHub 고정 토큰 엔드포인트의 오류 분류만 확인했다. 비밀값·토큰·응답 원문은 기록하지 않았다.

## 1. 위치
prism-backend의 .env 로그인용 GITHUB_OAUTH_CLIENT_ID / GITHUB_OAUTH_CLIENT_SECRET, app/domain/auth/github.py의 token exchange. 프론트 로그인 실패 안내와 연결된다.

## 2. 증상
GitHub 로그인 이후 프론트에 '로그인이 취소되었거나 완료되지 않았어요'가 표시된다. 사용자 스크린샷으로 재현 확인. 기대 결과는 로그인 세션 발급 후 메인 이동이다.

## 3. 발생 과정 및 확인
최근 OAUTH_LOGIN 시도가 생성 후 소비된 것을 DB에서 읽었다(2026-09-26 04:20 KST 부근 2건). state/browser binding 검증 이후 단계까지 도달했다. 로컬 Settings는 auth_ready=True, app localhost:5173/API localhost:8000. OAuth와 GitHub App Client ID는 서로 다르다.

동일 로컬 OAuth ID/Secret을 GitHub 공식 토큰 엔드포인트에 보내되 실제 로그인 코드 대신 명백히 무효인 진단 문자열을 사용했다. HTTP200, error=incorrect_client_credentials를 받았다. 새 토큰·세션 발급은 없으며 오류 분류만 출력했다.

## 4. 원인
GitHub가 현재 로컬 OAuth 자격증명 조합을 거절한다. Secret 폐기/만료, 잘못된 복사, ID와 Secret 불일치 중 구체적 계기는 미확정이다. 프론트 라우팅 원인으로 볼 근거는 없다. 존재 여부만으로 계산하는 auth_ready는 실제 GitHub 유효성 보증이 아니다.

## 5. 해결 상태
진단 완료, 복구 대기. 사용자가 로그인용 OAuth App에서 Client ID를 대조하고 새 Client Secret을 발급하여 로컬 .env의 해당 두 설정을 맞춰야 한다. 저장소 GitHub App/PEM 설정은 별도다. 새 자격증명은 채팅/추적 문서에 넣지 않는다. 변경 후 백엔드 재시작과 실제 로그인 성공 확인이 필요하다. 현재 성공으로 표시하지 않는다.

## 6. 후속 조치
사용자 자격증명 갱신 후 같은 고정 엔드포인트 오류 분류와 사용자 화면 로그인→메인→새로고침을 확인한다. 일반 실패 문구는 민감 정보 노출 방지를 위해 유지한다. 서버 내부 안전한 오류 분류 계측은 별도 후속이며 이번에 인증 정책·코드를 변경하지 않았다.

## 사용자 설정 변경 후 재확인
사용자 재확인 요청으로 .env를 다시 읽었다. OAuth와 GitHub App Client ID는 여전히 같지만, GitHub 응답은 incorrect_client_credentials/redirect_uri_mismatch에서 bad_verification_code로 바뀌었다. 의도적으로 무효 코드를 보냈으므로 이는 자격증명/콜백의 앞선 오류가 더 이상 나타나지 않는다는 근거이며 실제 로그인 성공 증거는 아니다. 동일 ID만으로 로그인 불가능하다고 단정하지 않는다. GitHub App 사용자 인증 구성을 사용 중인지는 사용자 설정 확인 대상이다.

확인된 기존 Uvicorn 프로세스만 종료하고 같은 명령으로 백엔드를 재시작했다(PID 10112). 실제 사용자 OAuth 로그인 완료는 사용자 화면 테스트 대기다. 비밀값 및 인증 코드 원문은 기록하지 않았다.

## 조직 저장소 실제 연결 확인
2026-09-26 04:43 KST: 사용자가 로그인 성공을 확인한 뒤 1-team-whyNot-chapchap/chapchap-customer-service 연결을 요청했다. App 설치/미정지/contents·issues·pull_requests read 권한을 읽기 API로 확인했다. 연결 시 Invalid Redirect URI가 발생했고 앱에는 로그인 callback만 남아 있었다. 기존 로그인 callback을 보존하고 http://localhost:8000/api/v1/github-app/callback을 추가하여 저장소 연결용 기존 경로를 복구했다(와일드카드 비활성 유지). 권한 범위와 키는 변경하지 않았다.

사용자의 로그인된 Chrome PRism 화면에서 우리팀에 저장소 연결 성공, 동기화 완료 30개 반영을 확인했다. 목록 #49~#20에서 병합됨 상태가 표시됐다. 더 오래된 PR은 이전 PR 더 가져오기로 후속 조회 가능하다. GitHub 원본 저장소 및 PR 변경은 수행하지 않았다.
