# 작업 리포트: 배포 직전 준비와 종합 검증

> 작성일: 2026-09-27
> 패키징/배포일: 해당 없음
> 작업 브랜치: dev
> 커밋/PR: 미커밋
> 상태 기록 버전: 1
> 상태 확인 시각: 2026-09-27T01:07:12+09:00
> 구현 상태: 완료
> 구현 근거: production 설정·쿠키·Docker·배포 템플릿·운영 문서의 이번 working-tree diff
> 로컬 검증 상태: 완료
> 로컬 검증 대상: 배포 전 작업 트리 및 이전 evidence-rules 변경 포함
> 로컬 검증 근거: backend222 tests, frontend51 tests/build, 합성 DB 복원·컨테이너 smoke와 본문3절
> 병합 상태: 미수행
> 병합 대상: origin/main
> 병합 근거: 구현 저장소는 dev 게시만 승인됨
> 배포 상태: 미수행
> 배포 근거: 사용자 목표는 실제 배포 이전이며 클라우드 서비스를 생성하지 않음
> 실제 연동 상태: 완료
> 실제 연동 근거: 로컬 기존 GitHub OAuth 로그인·저장소2개·조직 PR30개·기존 분석/AI 결과 조회 확인. 공개 배포 연동은 제외
> 작업 범위: XL
> 적용 스킬: terminal-ops, git-workflow, troubleshooting-report
> 적용 Gate: Security Gate, DB Gate
> 위험도: 보안
> 위험 작업 여부: 예

## 0. 작업 범위 확인

사용자가 배포 전 단계에서 스스로 할 수 있는 작업을 승인했다. backend/frontend dev, architecture main. 되돌릴 기준은 backend93b8bcc, frontend1650120, architecture cac51a0. 기존 evidence-rules 미커밋 변경을 보존하고 함께 게시한다. 사전 계약은 backend docs/work-plans/2026-09-27_predeployment.md. GateGuard6-1에 따라 HTTPS/쿠키/TLS 경계와 테스트 DB 스키마 삭제를 위험 작업으로 검토했다. 사용자가 승인한 검증용 임시 스키마만 정리하며 실제 prism DB의 사용자 데이터는 변경하지 않는다. 추가 유료 AI·실제 배포·계정 생성·main 병합·하네스 원본 동기화 제외.

## 1. 작업 요약

production HTTPS origin/DB TLS 검증, Secure cookie·CDN no-store·API 문서 비활성화. 비root 단일worker Docker, Render/Vercel 템플릿, 프론트 설정 생성기, 백업복원 리허설과 운영 절차. ADR-DEPLOY-002와 소유 문서·맵을 동기화했다. 이전 AI 근거/29규칙 변경도 종합 테스트했다.

## 2. 변경 파일

backend Settings/auth/github_router/main·tests/test_production.py, Dockerfile/.dockerignore/config/deployment, scripts/check_backup_restore.py·check_container.py·CI, docs/PREDEPLOYMENT.md·PROJECT_STATUS·README. frontend deployment/template·generator·tests 및 이전 AIReviewEvidence. architecture ADR-DEPLOY-002·RENDER·FRONTEND·context-map·DECISIONS. 자세한 파일은 Git diff로 추적한다.

## 3. 검증 결과

| 항목 | 결과 | 관측 |
|---|---|---|
| 전체 backend | PASS | reports/2026-09-27_predeployment-windows.json: 222 passed/52.28초, 전용 prism_test |
| Windows native | PASS | 모듈 before/after false, native진단0. 이번 세션 관측이며 GameGuard 내부 결함 수정 주장 아님 |
| frontend | PASS | npm test 51개, npm run build/typecheck 54modules |
| lint/type | PASS | ruff/format139파일, mypy110소스 |
| Docker/Parser | PASS | 비root uid999, network none, 1CPU/512MiB. 네 언어100개 소형 합성 파일28.312초, memory.peak141434880bytes. timeout kill·health live200/DB없음ready503 |
| backup/restore | PASS | prism_test 합성2행/인덱스2개, 한글 byte일치·임시스키마 정리. 개발DB·실데이터 미사용 |
| 브라우저 | PASS | 실제 로컬 OAuth→홈, 저장소2개·조직 PR30개, Enter로 #49 진입, 기존 정적/AI 결과 표시. 390px scrollWidth375, 320px305, viewport복원 |
| 아키텍처 | PASS | 73문서/21ADR/285링크. 기존 RELATIONS 길이 WARN 유지 |
| 추가 유료 AI | 해당 없음 | 호출0. 이전7회6/7 결과 보존, 개선 후순위 |

Docker 숫자는 소형 fixture 순차 처리 측정이다. 최악100파일/동시 요청/공개 환경 자원 보장은 아니다. 이번 브라우저 검증에서 실제 다른 사용자 동의나 조직 권한 부여는 수행하지 않았다. 신규 production 환경의 OAuth proxy/TLS/Webhook 실전송은 미수행.

## 4. Checklist 결과

Security Gate: HTTPS/정확한 Origin·Secure 쿠키·TLS·서버 secrets·캐시 차단 PASS(로컬 설정/테스트 범위). DB Gate: _test 고정·고유 스키마·원본 비접근·복구 비교·정리 PASS. 비밀값/문서/Report/adapter 검사는 게시 직전 결과를 후속 기록한다. Docker는 .env/PEM/test/report 제외. 실제 주소·키·CA·예산·알림 수신자 결정은 배포 실행 전 미정 항목이다.

## 5. 발견된 문제

위치: 기존 Settings/auth cookie. 증상: production/HTTPS origin 거부·Secure=false 고정. 과정: 배포 전 설정 검토에서 발견. 원인: 로컬 개발 계약만 구현됨. 해결: production 별도 검증과 Secure/삭제 일치·no-store 추가,14테스트 통과. 후속: 공개 frontend proxy에서 cookie/Location 실제 보존 확인.

컨테이너 검증 스크립트 초안은 parser 상태 이름을 ANALYZED로 잘못 예상해 실패했다. 실제 계약 INCLUDED로 수정 후 같은 100파일 검사 통과. 제품 parser 결함은 아니었다. 브라우저 AX에서는 pressed button이 checkbox로 나타나 locator 탐색1회 실패했으며 DOM button과 Enter로 실제 진입 확인했다.

## 6. 미해결 항목

공개 주소·DB provider/CA·운영 키·비용과 알림 수신자, 실제 배포 OAuth/Webhook·다사용자 종단 검증. 실제 데이터 복원/PITR·최악 부하·강제 프로세스 재기동 운용은 별도 환경에서 검증한다. AI내용6/7·정적규칙9개는 사용자 지시대로 후순위. 하네스 동기화 보류.

## 7. Working Context 반영 여부

반영 필요: 예. 이번 결과와 사용자 결정/실배포 경계를 각 저장소 Working Context 및 최신 포인터에 반영한다. 이전 evidence-rules 보고서는 별도 작업의 검증 이력으로 보존한다.

## 8. 다음 작업

아키텍처 main 먼저 게시 → consumer revision 갱신 → backend/frontend dev 게시 → 해당 SHA의 CI 확인. 실제 배포는 하지 않는다. 사용자 입력 없이 수행 가능한 이번 범위의 게시·검증을 마친 뒤 남은 결정을 보고한다.

## 9. 게시 전 검증과 아키텍처 게시 (2026-09-27T01:10:20+09:00)

work-records/docs/skills/references/report-consistency/no-personal-paths/harness 검사 양쪽 PASS. 아키텍처 main c9275e62bb0efba3e42910e3dbcfe3b77f21409b commit/push 성공, consumer revision 갱신. 구현 두 저장소 dev는 게시 준비 상태. 진행 Job0 확인 후 최신 API로 재시작, frontend proxy readiness200·API private/no-store 확인.

게시 전 secret 검사: backend370/front228 tracked files의 금지 파일·알려진 패턴 PASS, 세 저장소에서 로컬 .env 비밀값과의 literal 비교 일치0. 원문 키를 출력하거나 저장하지 않았다. Git 소유권 때문에 escalated 하위 검사1회 실패했고 정상 sandbox에서 같은 검사 재실행 PASS. 전역 safe.directory는 변경하지 않았다.
