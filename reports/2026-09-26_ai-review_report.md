# 작업 리포트: 수동 DeepSeek AI 리뷰

> 적용 스킬: ui-ux-design, vue-ui-polish
> 적용 Gate: Security Gate, DB Gate, UI/UX Gate
> 상태 기록 버전: 1
> 구현 근거: 기존 본문 변경·검증 기록을 기준으로 형식 정정; 새 실행 증거 아님
> 로컬 검증 근거: 기존 본문 변경·검증 기록을 기준으로 형식 정정; 새 실행 증거 아님
> 실제 연동 근거: 기존 본문 변경·검증 기록을 기준으로 형식 정정; 새 실행 증거 아님
> 형식 정정: 2026-09-26 게시 준비 중 누락 헤더 정리. 과거 검증을 재실행한 것으로 간주하지 않음.

> 작성일: 2026-09-26
> 상태 확인 시각: 2026-09-26T15:46:46+09:00
> 작업 브랜치: backend/frontend dev, architecture main
> 커밋/PR: 미커밋
> 구현 상태: 완료
> 이전 구현 요약: 완료 — 승인된 1~6단계
> 로컬 검증 상태: 완료
> 이전 로컬 검증 요약: PASS, 기존 Windows 진단 WARN 별도
> 로컬 검증 대상: 현재 working tree
> 병합 상태: 미수행
> 이전 병합 요약: 미진행 / 대상 origin/main
> 배포 상태: 미수행
> 이전 배포 요약: 미진행 — 로컬만
> 실제 연동 상태: 완료
> 이전 실제 연동 요약: PASS — GitHub 조직 PR + DeepSeek
> 작업 범위: L
> 적용 스킬/Gate: security-gate, db-gate, ui-ux-design, vue-ui-polish, browser QA
> 위험도: DB·외부 코드 전송·유료 API, 사용자 전체 단계 승인 범위

## 0. 작업 범위 확인

설계·체크리스트를 먼저 작성한 뒤 LangChain DeepSeek, 제한된 코드 문맥, 영속 결과/사용량, UI, 실제 PR 검증을 구현했다. 기존 미커밋 변경을 보존했다. 커밋·push·공개 배포는 하지 않았다.

## 1. 설계와 구현

- ADR-REVIEW-003이 FINDINGS_ONLY 초기 설계를 대체. OWNER가 매 요청 동의하며 팀원은 조회한다.
- analysis 공개 API로 고정 분석 스냅샷을 읽는다. 최대8파일/patch8KiB/전체입력24KiB, 삭제 줄·원문 본문 제외, 비밀 의심 파일 제외, 파일 ID 익명화.
- LangChain ChatDeepSeek JSON mode + strict schema + 파일/줄 검증. 도구·tracing·자동재시도 없음.
- review_runs / migration0006, 물리 FK 없음. execution_key·상태 CHECK·이력/예산 인덱스. 원문 입력·응답은 미보관.
- 호출1회/출력2000토큰/60초, Workspace UTC 하루5회 접수/동시1개. lease 만료·실패 재호출0. 요청/전송전/저장시 권한과 연결 세대 재확인.
- 화면: 동의·요청·취소·진행 상태·최근50개 이력·요약/근거/제안/한계·토큰·실패 안내. 정적 결과와 분리.
- config/development.example은 AI OFF, 로컬 ignored .env만 AI ON/deepseek-flash. API 키 출력·커밋 없음.

## 2. 검증 근거

| 검증 | 결과 |
|---|---|
| Backend pytest, prism_test의 격리 스키마 | 146 passed / 43.28초 |
| ruff app tests + 새 migration/env | PASS |
| mypy app | 108 source files PASS |
| alembic upgrade head / check | 0006 적용, drift 없음 |
| 운영 개발 DB 물리 FK 조회 | 0개 |
| Frontend typecheck/build | PASS, 49 modules |
| Frontend vitest | 35 passed / 5 files |
| architecture validate_docs.py | PASS, 18 ADR; 긴 관계 문서 경고1개 |
| 화면 320/375/414/768/1440px | 가로 넘침 없음; 375px 캡처 육안 확인 |
| 브라우저 오류/경고 로그 | 현재 캡처 0개 |
| 새로고침 | 완료 이력/요약/토큰 복원 |

AI OFF, 동의/다른 팀 거부, 중복 재사용, 취소, timeout, 일 한도, lease 만료 재호출0, 권한 변경 전/중간 차단, 결과 폐기, 정적 분석 유지, 비밀 필터/입력 크기/출력 schema/위치 검증을 포함한다. 실패 사례는 fake provider로 검증했으며 실제 장애 주입을 DeepSeek에 수행하지 않았다.

## 3. 실제 호출

모델 목록 API에서 deepseek-flash/deepseek-v4-pro를 확인했다. 기존 GitHub 로그인으로 UI에서 요청했다.

- 조직 저장소: 1-team-whyNot-chapchap/chapchap-customer-service.
- PR47: 9,122byte 단일 patch가8KiB를 초과해 FAILED. call_attempts=0, 토큰0, 과금 불확정 false. 제한을 완화하지 않았다. 이후 NO_SAFE_CONTEXT 안내를 응답 검증 오류와 구분했다.
- PR49: COMPLETED, run 9fa33ab8-80f5-4bbc-8c25-3a04efba2887, head 562e52893788e68abccee20cd82d4b4265a0b6db.
- 외부 호출1회, 처리5.53초(취득 포함), 입력6314/출력396토큰, 검토6파일/제외7파일. 구체적 issues0, 요약과 검토 한계 저장. 결함 부재/안전성 보장 아님.
- 정적 Finding11건 그대로 유지. 새로고침으로 결과 유지 확인.

## 4. 운영·남는 한계

DB 적용 전 pg_dump를 로컬 TEMP/prism-before-ai-review.sql에 보관했다(Git 외부). API는 현재 uvicorn으로 로컬8000에서 실행, 자동 reload 없이 실행 중이므로 이후 백엔드 수정 때 재시작해야 한다. frontend5173 및 DB는 유지했다.

자동 비밀 탐지는 불완전하고 제한된 코드 밖 의미/실행 검증은 못 한다. 횟수/출력 제한은 금액 상한 보장이 아니며 공개 운영의 금액 예산/retention/배포는 후속 작업이다. 반환된 요약의 f1…은 외부 전송용 익명 ID이며 개별 issue가 있으면 검증된 실제 경로·고정 HEAD 링크로 표시한다.

pytest 시작 시 기존 Windows native access-violation 진단이 출력됐지만 전체 테스트는 계속되어 exit0이다. 이 플랫폼 진단 원인은 이번 기능 범위에서 해결하지 않았으며 별도 조사 대상이다. 전 migration ruff의0005 UP0348건은 기존 경고여서 이번 검증은 새 migration과 앱/테스트에 한정했다.

실행 제한 또는 문제 발생 시 AI_ENABLED=false 후 API 재시작으로 새 접수를 차단한다. 기존 DB를 downgrade/삭제하지 않는다. 하네스 동기화는 사용자 요청대로 보류.
