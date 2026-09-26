# GitHub Webhook 실행과 검증

## 현재 동작
`POST /webhooks/github`는 로그인 쿠키 대신 GitHub 원문 body의 HMAC-SHA256을 검증한다. 최대 1 MiB까지 읽고, 지원하는 이벤트의 식별자만 Delivery와 Job에 함께 저장한다. PR 본문·Diff·token·원문 payload는 저장하지 않는다.

- pull_request: opened/reopened/synchronize/ready_for_review/converted_to_draft/closed/edited → 현재 PR 단건 동기화 접수.
- installation: deleted/suspend → 수신 전에 연결된 해당 설치의 저장소를 SUSPENDED로 차단.
- installation_repositories: removed → 제거된 저장소만 차단.
- 기타 이벤트/동작, 미연결 PR: 204. unsuspend/added로 연결을 자동 복원하지 않는다.

수신은 202, 저장된 동일 delivery는 200, 같은 delivery ID의 다른 body/event는 409다. 서명 오류 401, 잘못된 입력 422, 1 MiB 초과 413, Secret/DB 미설정 503. DB 저장 실패에는 성공 응답을 보내지 않는다.

Delivery PROCESSED는 후속 SyncRun+Job 접수 완료를 의미하며 PR 취득 완료는 SyncRun의 COMPLETED로 확인한다. 큐 처리 후 UI의 팀 새로고침/PR 보기로 최신 목록을 확인한다. 화면의 상태 확인은 현재 선택한 수동 SyncRun의 상태다.

## 환경과 실제 GitHub 연결
로컬 `.env`에 `GITHUB_WEBHOOK_SECRET`과 `SYNC_RUNNER_ENABLED=true`를 설정하고 서버를 재시작한다. Secret은 충분히 긴 임의 값이며 로그인/App Client secret과 별개다. `.env`는 Git 제외다. Worker는 1개로 유지한다.

GitHub가 접근할 공개 HTTPS 수신 주소가 확정된 후 App 설정의 Webhook URL을 `https://수신호스트/webhooks/github`로 설정하고, 서버와 동일한 Secret을 입력한다. Pull requests 이벤트 및 설치/설치 저장소 변경 이벤트 수신을 확인한다. 지금은 배포·터널 주소가 미정이므로 GitHub Webhook Active를 켜지 않았다. localhost로 GitHub의 외부 요청을 받을 수 있다고 가정하지 않는다.

실제 활성화 후 GitHub Recent Deliveries의 2xx, DB Delivery 상태, SyncRun COMPLETED, PR metadata 일치를 각각 확인한다. 서명 검증만으로 Workspace 권한을 인정하지 않으며 현재 설치 ID와 저장소 ID·연결 세대로 내부 매핑한다.

## 재시도와 한계
lease 60초/heartbeat 15초/총3회 재시도를 공통 Job 처리기에 위임한다. 다른 동기화가 진행 중이면 30초 후 재시도하며 기존 실행에 합류하지 않는다. 이미 HTTP 취득을 시작한 실행에 합치면 새 이벤트를 놓칠 수 있기 때문이다. 소진 시 FAILED/DEAD로 남기며 성공으로 숨기지 않는다. 수동 PR 동기화로 복구하고 운영 재처리 도구는 후속이다. 동일 delivery 재전송은 실패한 내부 Job을 새로 만들지 않는다.

PR delivery는 수신 시점 연결 세대를 고정한다. 설치 철회는 수신 이후 재연결된 연결을 변경하지 않는다. 원래 GitHub 발생 시각보다 늦게 수신된 철회는 보수적으로 차단할 수 있으므로 재연결로 현재 권한을 다시 검증한다. 자동 분석·AI 설명은 아직 실행하지 않는다.

이번 검증: 자동 테스트에서는 provider를 mock했다. 별도로 로컬 생성 서명 이벤트 → 실행 중 API 202/중복200 → 영속 Delivery PROCESSED → 실제 GitHub 테스트 PR #1 SYSTEM sync COMPLETED 1개를 확인했다. GitHub에서 직접 전송된 delivery의 종단간 검증은 아직 아니다.

근거: [서명 검증](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries), [이벤트 계약](https://docs.github.com/en/webhooks/webhook-events-and-payloads).
