# 배포 전 점검과 운영 절차

사용자 목표는 실제 배포 직전까지다. 실제 서비스 생성·DNS·키 발급·유료 호출은 이 문서 작성으로 실행하지 않는다. 현재 실행 증거와 게시 상태는 [최신 Report](../reports/_LATEST.md)를 따른다.

## 현재 준비물

- Dockerfile: Python 3.12, lock 고정 의존성, 비root, 단일 worker, PORT, healthcheck. 비밀값과 고객 소스를 이미지에 포함하지 않는다.
- config/production.example: 운영 환경변수 자리. 공개 frontend 주소 두 origin은 동일해야 하며 소문자 hostname·기본 포트 생략 형식을 사용한다. DB TLS는 verify-full과 제공자 CA를 사용한다.
- deployment/render.example.yaml: 자동 배포 OFF·무료 데모 플랜 예시. import도 실제 서비스 생성이므로 이번 작업에서 실행하지 않았다. 무료 기동 지연 때문에 상시 처리 보장은 하지 않는다.
- frontend의 deployment/vercel.template.json: API·health proxy → SPA 순서, private/no-store, 보안 헤더. API 실제 주소 확정 후 PRISM_API_ORIGIN을 설정하고 npm run configure:deployment 실행. 기존 vercel.json은 덮어쓰지 않는다.
- [작업 계획](work-plans/2026-09-27_predeployment.md), [프로젝트 상태](PROJECT_STATUS.md), [정적 분석 범위](STATIC_ANALYSIS.md).

## 나중에 사용자와 확정할 값

| 항목 | 결정/입력 | 검증 기준 |
|---|---|---|
| 배포 주소 | Vercel frontend와 Render API 주소, 필요하면 도메인 | HTTPS 인증서 유효·API origin은 frontend 프록시 주소 |
| DB | provider/region/용량/백업 기간/CA | PostgreSQL 17 호환, verify-full 연결, 저장 공간 및 restore 검증 |
| 운영 인증 | 개발용과 별도 OAuth App/GitHub App 키·JWT·Webhook secret | callback/설치 callback 정확히 일치, 비밀값은 서버 환경에만 저장 |
| 비용·알림 | 월 한도와 수신자 | 플랫폼/DeepSeek 대시보드 알림, 실제 운영 예산 확인 |
| 운영 수준 | 무료 데모 또는 상시 인스턴스 | 무료 유휴/재시도 제한을 수용하는지 명시 |

현재 AI 최대 5회/일 정책은 금액 한도를 대신하지 않는다. AI 기본 OFF로 배포 준비하며 켜기 전 실제 사용자의 전송 동의와 별도 비용 결정을 확인한다.

## 첫 배포 실행 순서 — 현재 미수행

1. backend/frontend dev의 CI 성공과 architecture.json revision을 확인한다. 배포 대상 commit/image digest를 기록한다. main 승격은 별도 결정이다.
2. 새 운영 DB를 만들고 전용 최소 권한 계정과 제공자 CA를 준비한다. PUBLIC_APP_ORIGIN=PUBLIC_API_ORIGIN=frontend HTTPS origin. 두 callback은 각각 /api/v1/auth/github/callback, /api/v1/github-app/callback이다. GitHub Webhook은 실제 API HTTPS의 /webhooks/github로 등록한다. 경로는 HTTP_API 및 구현 router와 재대조한다.
3. 환경변수를 안전한 관리 화면으로 주입한다. env/PEM/DB dump를 Git·로그·VITE_*에 넣지 않는다. config/production.example은 미정 주소라 의도적으로 시작 검증에 실패한다.
4. 트래픽을 받기 전에 승인된 단일 운영 작업으로 alembic current → alembic upgrade head → alembic check를 실행한다. 명령은 backend 이미지의 /app/.venv/bin/alembic로 실행 가능하다. 환경에 따라 pre-deploy 작업 지원 플랜을 확인한다. 앱 CMD에 migration을 넣지 않는다.
5. frontend 설정 생성·빌드 후 배포, backend 기동. /health/live와 /health/ready, 실제 DNS·TLS·DB 지속성을 확인한다. readiness는 SELECT 1 검사이며 migration head 검증을 대신하지 않는다.
6. OAuth 로그인/새로고침/로그아웃, Secure/HttpOnly/host-only cookie, callback query의 로그 제외, API CDN cache MISS/no-store를 확인한다. 실제 조직/다른 사용자로 403 격리를 검사한다.
7. App 연결·PR 이력·분석 취소/재시작 복구·Webhook 서명/중복 전달을 검증한다. App 설정 완료 후 필요한 runner만 켠다. 자동 분석·AI는 사용자가 고른 범위에서 켠다.
8. 오류·비용·DB 백업 지표와 담당자를 확인한 뒤 배포 승인 기록을 남긴다.

## 백업과 복원

이번 리허설은 scripts/check_backup_restore.py로 prism_test의 무작위 backup_drill 스키마만 생성해 pg_dump -Fc/pg_restore를 실행한다. 두 합성 행(한글 포함)과 PK/unique index를 비교하고 스키마를 정리한다. 개발 prism DB와 실제 고객 데이터는 읽거나 변경하지 않는다. reports/2026-09-27_backup-restore.json에 원문 없이 결과·해시만 기록한다. 전체 실제 데이터·사용자 권한·확장·provider PITR 검증은 아니다.

운영 백업은 제공자의 자동 백업/PITR 기능과 보존 정책부터 확인한다. 별도 pg_dump가 필요하면 DSN을 명령줄에 직접 적지 않고 보안 연결 설정을 사용하며 암호화된 접근 제한 저장소에 보관한다. dump에는 사용자/세션/초대/리뷰 데이터가 포함되므로 공유 저장소에 올리지 않는다. 복원은 원본 DB를 덮어쓰지 않는 별도 DB에 pg_restore --exit-on-error로 수행한다. 스키마 head·행 수·unique index·논리 관계 orphan 검사·읽기 흐름을 검증한 뒤 새 연결로 전환한다. 원본 백업 삭제/전환은 담당자의 실행 승인 대상이다. 보존 기간과 RPO/RTO는 실제 규모/복구 시간 측정 후 정한다.

## 장애·롤백·일상 점검

| 신호 | 조사 | 대응 |
|---|---|---|
| readiness 503 | DB 가용성/TLS/접속 한도, 비밀값 없는 오류 코드 | 새 배포 중단, DB 연결 복원 후 다시 확인 |
| Job 대기/실패 증가 | runner flag, lease, attempt, provider rate limit | 원인 확인 후 UI 재시도. 진행 행/lease 직접 삭제 금지 |
| Webhook 누락 | GitHub delivery 응답/서명/중복 처리 | 공개 endpoint 복구 후 승인된 delivery 재전송 또는 PR 수동 동기화 |
| AI 오류/비용 증가 | 일일 사용량/실패 코드/provider 대시보드 | AI OFF, 추가 유료 재평가는 별도 승인 |
| 새 버전 장애 | 이전 이미지와 현재 schema 호환성 | 호환되는 앱 버전으로 복귀. DB downgrade/복원 자동 실행 금지 |

앱 버전, schema revision, health 성공/실패, Job 상태별 수·최대 대기 시간, AI 사용량, DB 용량·백업 최근 성공을 점검한다. 고객 소스·diff·OAuth code·쿠키·토큰·프롬프트 전체를 운영 로그/알림에 복사하지 않는다. 현재 외부 모니터링 계정·알림 수신처는 미설정이다. 데이터 보관/삭제는 아키텍처 PRIVACY 계약을 따르며 자동 purge를 검증 없이 새로 켜지 않는다.

## 다른 컴퓨터에서 이어가기

세 저장소 clone 후 architecture main, backend/frontend dev checkout. 각 README대로 Python3.12/uv0.12.18, Node24, Docker PostgreSQL17을 준비한다. 개인 .env와 PEM은 Git에 없으므로 안전한 별도 전달이 필요하다. 실제 값을 채운 뒤 DB migration·health·로그인부터 확인한다. 컨테이너/DB 볼륨은 Git clone으로 이전되지 않는다. 필요한 데이터는 위 복원 절차로 별도 이관한다.

## 완료 경계

로컬/CI 테스트, 이미지 빌드, 템플릿, 합성 데이터 복원은 배포 준비 증거다. 공개 HTTPS의 proxy 쿠키·GitHub 실전송·외부 DB 백업·100파일 피크 자원·실사용 부하는 공개 환경/규모가 정해진 뒤 별도 판정한다. AI 내용 평가6/7의 오탐 잔여와 미구현 규칙9개는 사용자 지시대로 후순위다.
