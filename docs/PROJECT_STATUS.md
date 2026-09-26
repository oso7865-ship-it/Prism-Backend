# PRism 개발 진행 현황

기준일: 2026-09-26. 로컬 구현과 최근 검증 보고서를 대조한 현황이다. 공개 서비스 출시 완료율이나 남은 작업 시간의 측정값은 아니다. backend/frontend는 dev, 아키텍처는 main에서 작업하며 구현 변경은 각 origin 브랜치에 게시했고 CI를 확인했다. 실제 커밋/관측 결과는 최신 Report를 따른다.

## 진행률 산정

아키텍처 quality/TESTING.md의 MVP 구현 순서 8단계를 동일 가중치로 보고 완료1·부분0.5·미착수0으로 계산하면 6/8, 약75%다. 단계별 난이도/작업량은 서로 다르므로 일정 예측에는 사용하지 않는다. 로그인→저장소→PR→정적 분석→수동 AI 리뷰의 로컬 핵심 흐름은 동작 확인됐다.

| 단계 | 상태 | 확인된 범위와 남는 작업 |
|---|---|---|
| 1. 기본 구조·DB·설정·CI | 초기 범위 완료 | 독립 저장소, PostgreSQL17, migration0006, 논리 관계. 원격 CI에서 migration 왕복·drift·테스트 검증 완료 |
| 2. 로그인·사용자·팀 권한 | 초기 범위 완료 | 실제 OAuth 로그인, 팀·멤버·초대·권한 구현. 공개 운영의 다사용자 종단 검증은 별도 |
| 3. GitHub App·PR·Sync Job | 초기 범위 완료 | 개인/조직 저장소 연결, PR 이력·상세·동기화 실제 확인 |
| 4. 분석 실행·Worker·결과 | 초기 범위 완료 | 고정 SHA, 접수·이력·취소·복구·결과, 실제 조직 PR 분석 |
| 5. 네 언어 정적 규칙 | 부분 완료 | Java/Python/JS/TS 활성23개, 목표 후보38개 중 고급15개와 품질 측정 후속 |
| 6. Webhook | 부분 완료 | 서명·중복·영속 처리 및 로컬 서명 이벤트 검증. 공개 HTTPS 주소에서 GitHub 실전송 미검증 |
| 7. 선택적 DeepSeek 리뷰 | 초기 범위 완료 | LangChain 실제 호출·동의·한도·결과·버전 하네스. 모델 품질 확대 평가는 후속 |
| 8. 데모 배포·운영 검증 | 미착수 | 공개 주소/DB 호스팅 결정, 배포 OAuth·proxy, 백업/복구·cleanup·자원/재기동 검증 필요 |

## UI와 품질 증거

로그인/메인/저장소/팀 페이지 분리, 파란 계열 UI, PR 탐색·상세 복원·상태 안내를 구현했다. 기존 보고서에서 320~1440px 브라우저 검수, 최신 frontend38 tests/build PASS를 확인했다. 전체 접근성 인증이나 모든 장애 경로 검증은 아니다.

backend 전체146 tests는 AI 리뷰 구현 당시 기록이며 이후 하네스 관련31개 검증과 이번 지침 변경 관련27개 검증을 구분한다. 이번에 전체 회귀 테스트를 재실행한 것은 아니다. 기존 Windows 드라이버 native access-violation 진단 원인은 후속 조사 대상이다.

## 이번 페르소나 반영

작업 계약: 사용자 승인 문구를 core.md에 반영하고 지침 안내와 현황 기록을 갱신한다. 일반 지침 수정이며 권한/DB/호출 한도 변경 없음. 기존 terminal-ops 및 관련 하네스 회귀 테스트 적용. GENERAL_HARNESS 동기화/추가 유료 호출/커밋·푸시 제외.

기본 역할은 근거 중심 시니어 코드 리뷰어다. 언어만으로 프론트/백엔드나 실행 환경을 추정하지 않고, 보이는 코드에 맞춰 발생 조건·영향·최소 개선안을 정중하게 설명한다. 작성자 의도 존중, 불확실성 표시, 취향/불필요한 재설계/억지 지적 배제를 명시했다.

- 새 지침 버전: rh1-3255b8329435eda1.
- pytest tests/test_review_harness.py tests/test_review_policy.py: 27 PASS, 1.05초. 캐시 폴더 접근 경고1개, 검증 실패 없음.
- 진행 Job0 확인 후 API 재시작, /health/ready HTTP200 확인.
- 기존 유료 평가1사례 PASS는 이전 버전 rh1-d9133f8d1cc6f1c1의 결과다. 새 페르소나의 실제 유료 응답 품질을 검증한 것으로 간주하지 않는다.

## 남은 작업 우선순위

2026-09-26 후속: [AI 품질·안정성 검증](../reports/2026-09-26_quality-stability_report.md)을 수행했다. 유료7사례 자동6/7 PASS, 락 문맥 부족에서 추측성 지적2개로1사례 FAIL. 추가 경계 테스트를 포함한 backend170개 PASS. Windows 진단은 재현했으나 근본 원인 미확인이다. 지침은 rh1-3b9b53482a3791ef로 보완·재시작했고 수정 버전 유료 재평가는 미수행이다. 따라서 아래1·3의 검증을 시작했지만 품질/안정성 잔여 항목은 남아 있다.

1. AI 평가7사례 확대 및 반복 평가: 누락·오탐·불확실성·심각도·지시문 주입 저항 확인. 유료 실행은 별도 승인 범위로 진행.
2. 정적 분석 고급15개 후보와 실제 코드 품질 측정. 규칙 설정과 제외 범위 UX 검토.
3. 조직/다사용자 권한·취소·네트워크 장애·접근성의 종단 검증, Windows 진단 조사.
4. 배포 주소/DB 호스팅 확정 후 실제 GitHub Webhook 수신과 OAuth 배포 테스트.
5. 백업/복구·보관/삭제·모니터링·금액 예산/알림·재기동/자원 한도 등 공개 운영 준비.
6. 게시 정리는 이번 승인으로 수행했다: README/OPEN_ITEMS 정정, 아키텍처 먼저 게시 및 consumer revision 갱신, dev 푸시와 최신 구현 CI 성공. 과거 snapshot의 작성 시점 SHA는 보존한다.

하네스 원본 동기화는 사용자 요청대로 보류한다. GitHub 자동 댓글, 자동 수정/머지, RAG, 전체 저장소 분석, Vue SFC는 이번 완료 선언 범위가 아닌 확장 후보다.

## 근거

- [AI 리뷰 구현·실제 호출](../reports/2026-09-26_ai-review_report.md)
- [하네스 구현과 유료 평가 기록](../reports/2026-09-26_review-harness_report.md)
- [정적 분석 범위](../reports/2026-09-26_static-analysis_report.md)
- [Webhook 검증 범위](../reports/2026-09-26_webhook_report.md)

아키텍처의 일부 초기 미정 항목과 backend README의 초기 다음 작업 문구는 실제 진행보다 뒤처져 있다. App 등록/연결과 AI 구현 여부는 위의 최근 실연동 기록을 기준으로 판정했다. 본 문서는 확인하지 않은 원격 게시·배포를 완료로 취급하지 않는다.

## 2026-09-26 게시 준비 후속

수정 지침7회 재평가도 자동6/7 PASS, 락 문맥 부족의 추측성 지적2건 FAIL 유지. Windows native 오류는 nProtect GameGuard 모듈 npggNT64.des+0x2769 발생으로 특정했으며 외부 모듈 내부 결함이나 깨끗한 세션 비교는 후속이다. backend170 tests, frontend38 tests/build PASS. 현재 게시/CI 사실은 [최신 Report](../reports/_LATEST.md)를 따른다. 과거 미커밋 표기는 당시 상태이며 하네스 원본 동기화·공개 배포는 미진행이다.

## 2026-09-27 최신 개발 상태

AI 근거 계약을 서버 검증과 UI에 연결했고 static-1.1.0은29개 규칙이다. backend208 tests, frontend40 tests/build, Windows/Linux mypy PASS. 새 AI 실제 유료7회 평가 결과는 구조7/7, 내용6/7로 락 문맥 부족 오탐1건이 남았다. Windows는 테스트 중 GameGuard가 로드되어 clean-session 검증 미완료(native진단2회). 실제 app110파일에서 새 규칙7개 관찰을 수동 점검했으나 정확도/누락률의 일반화된 측정은 아니다. 남은 정적 후보는9개다. dev 및 architecture main 미커밋, 기존 게시 CI 결과와 구분한다. 상세는 최신 Report를 따른다.

## 2026-09-27 배포 전 준비

사용자가 목표를 실제 배포 이전으로 한정했다. production HTTPS/쿠키/TLS 검증, Docker/Render/Vercel 템플릿, 운영·복구 절차를 추가했다. 백엔드222 tests, 프론트51 tests/build PASS. 이번 Windows 회귀는 GameGuard 모듈 before/after 모두 false, native진단0이다(이전 진단의 근본 원인 수정 주장 아님). 별도 테스트 DB 합성 데이터 복원 PASS. 네 언어100개 소형 파일의 네트워크 차단512MiB 컨테이너 검사에서 peak141,434,880bytes 관찰. 최악 입력/실사용 부하 측정은 아니다.

주소·DB provider/CA·운영 키·비용/알림 수신처 확정과 실제 공개 OAuth/Webhook은 후속이다. AI6/7 품질과 규칙9개는 보류한다. 임의의 배포 완료율을 추가 산출하지 않는다. 현재 게시 결과는 최신 Report를 따른다.

최종 Origin 보완 후 backend224 tests PASS. Windows 추가 전체 회귀에서 GameGuard 모듈 로드/native진단2회가 다시 관찰되어 환경 의존 이슈는 유지한다. 직전222개/진단0은 당시 실행 결과다. Linux CI와 구분하며 최종 게시 SHA는 최신 Report를 따른다.

최종 Linux CI36255001493: backend85038e2 전체225 tests·migration왕복/drift·Docker build/100소형파일 PASS. frontend98a4fce/51 tests·architecturec9275e6 CI 성공. 배포 전 구현 게시 완료이며 실제 배포는 미수행.
