# 아키텍처 연결

제품 설계의 원본은 [Prism-Architecture](https://github.com/oso7865-ship-it/Prism-Architecture)다. architecture.json의 revision이 이 저장소의 기준 커밋이며 최신 main을 자동으로 적용하지 않는다.

독립 clone에서도 이 문서와 README로 실행·검증할 수 있다. 제품 계약을 수정할 때 원본 저장소의 해당 커밋을 별도 폴더에 clone/checkout하고 AGENTS.md → CORE → 작업별 소유 문서를 읽는다. context_select.py의 경로는 architecture.json의 logical_path_prefix와 현재 저장소 상대 경로를 합쳐 사용한다.

공통 실행 규칙은 원본 HARNESS에서 가져온 GENERAL_HARNESS 사본이다. PROJECT_HARNESS는 제품 문서와 작업 경로를 연결한다. 하네스 변경은 원본 커밋과 localChanges를 비교해 수동 반입하며 다른 제품 사본에서 복사하지 않는다. 제품 ADR은 아키텍처 저장소에서 새 영역 번호로 작성한 후 양쪽 참조 커밋을 갱신한다.

아키텍처 필수 경계: 업무는 domain/feature 소유, shared는 기술 공통 기능, 원문 코드 실행·설치 금지, AI 기본 OFF, 인증·Workspace·GitHub 권한 분리. 현재 로그인·팀 권한·저장소/PR·Webhook·분석·수동 AI 리뷰까지 로컬 구현했다. migration0006 및 실제 연동 범위는 최신 Report를 따른다. README가 실제 구현 현황의 진입점이다.

인증·팀 DB 구현 기준 설계는 원본 커밋 `665a2003f43c851d4fa3bcd9569059a4533f5409`로 게시했다. architecture.json과 [IDENTITY snapshot](database/IDENTITY_SCHEMA.md)·[COMMON snapshot](database/COMMON_SCHEMA.md)을 이 커밋에 연결했다. 각 snapshot의 SHA256은 원본 Git LF 바이트 기준이다.

2026-09-26: 로컬 아키텍처 main에 ADR-INTEGRATION-002(검증된 App 연결·안전한 리뷰 조회)와 HTTP 지도 변경이 있다. 미게시이므로 architecture.json은 기존 원격 기준을 유지한다. 다음 게시 시 아키텍처를 먼저 커밋·푸시하고 새 SHA로 소비 저장소를 갱신한다. 실행 계약은 docs/TEAM_REPOSITORIES.md와 생성된 OpenAPI를 함께 확인한다.

2026-09-26 게시 갱신: 아키텍처 main cac51a07516cd2e36b3bf4cc45c9a17fad050002를 푸시했고 architecture.json을 해당 SHA로 연결했다. 위의 초기 구현 설명/미게시 메모는 당시 이력이며, 현재 구현·검증은 reports/_LATEST.md를 따른다. 과거 DB snapshot은 작성 당시 기준 SHA를 보존한다.
