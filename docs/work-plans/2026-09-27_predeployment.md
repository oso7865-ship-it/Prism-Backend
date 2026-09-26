# 배포 직전 준비 작업 계약

- 사용자 승인: 스스로 수행 가능한 종합 검증·배포 설정·운영 준비·문서 정리 및 게시. 실제 배포/결제/추가 AI 호출 제외.
- 규모: XL
- 적용 스킬: terminal-ops, git-workflow, troubleshooting-report
- 적용 Gate: Security Gate, DB Gate
- 저장소: architecture main, backend/frontend dev. 기존 evidence-rules 미커밋 변경 보존 후 함께 게시. main 병합과 하네스 원본 동기화는 제외.
- 기준 문서: CORE, PACKAGE-RULES, CONVENTIONS, RENDER, FRONTEND, PRIVACY, ADR-REVIEW-005. 되돌릴 기준: backend93b8bcc, frontend1650120, architecture cac51a0.

## 설계와 완료 기준

현재 앱은 production 모드와 HTTPS origin을 거부하고 쿠키 Secure가 false로 고정돼 있다. production 설정을 별도 검증하며 frontend 동일 출처 OAuth proxy, HTTPS/Secure/정확한 Origin, 비공개 API 캐시, 비밀값 없는 오류를 강제한다. development 기본값·로컬 인증은 유지한다. 배포용 설정 예시는 미정 주소를 명시하고 실제 환경변수/서비스는 생성하지 않는다.

Docker는 Python3.12·uv lock·비root·단일worker·PORT·접근로그OFF·런타임 migration 없음. Render 설정은 자동배포OFF 템플릿, Vercel은 external API rewrite가 SPA fallback보다 먼저이며 no-store와 보안 헤더를 설정한다. 마이그레이션은 배포 전에 명시적으로 한 번 실행하고 실패 시 rollout 중단.

백업·복구 실험은 기존 로컬 PostgreSQL의 별도 _test DB에 이번 작업이 만든 임시 스키마와 합성 표식만 대상으로 한다. 개발 prism DB는 읽기 전용 상태 확인 외 변경하지 않는다. pg_dump custom/pg_restore 및 행·스키마 검증, 실패 시 실서비스 복구 금지. 실데이터 백업은 암호화 보관·별도 접근권한·폐기 절차를 문서화한다.

종합 검증은 기존 API/DB 다중 사용자·권한·해제·취소·중복·실패 테스트와 실제 브라우저 접근 가능한 화면으로 구분한다. 실제 다른 사용자 로그인/조직 승인, 공개 HTTPS OAuth/Webhook, GameGuard 없는 세션은 환경 의존으로 남긴다. AI 품질6/7 및 추가 규칙9개는 사용자 지시대로 후순위다.

## 체크리스트

- [x] ADR·소유 문서·production 정책
- [x] HTTPS 쿠키·Origin·설정 실패 방어 및 테스트
- [x] Docker/Render/Vercel 설정·빌드 검증
- [x] 별도 테스트 DB 백업·복구 실험
- [x] 운영 점검·이관·migration·rollback·잔여 체크리스트
- [x] UI 가능한 실제 경로·모바일/키보드 점검
- [x] 전체 테스트·타입·문서·비밀값 검사
- [ ] architecture 먼저 게시, 소비 revision 갱신, backend/frontend dev 게시·CI

Security 사전 검토: 권한 범위는 유지하고 production에서 추가 제약만 적용한다. 외부 전송/키발급/실배포 없음. DB 사전 검토: 삭제는 이번 검증용 고유 스키마로만 제한하고 검증 전후 식별자를 확인한다. 사용자 승인한 테스트 DB 복구 검증 범위의 정리만 수행한다.
