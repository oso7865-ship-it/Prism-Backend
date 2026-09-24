# AI Runtime Handoff Template

> 목적: 업무 서비스와 별도 AI Runtime 사이의 책임·계약·검증 근거를 인계한다. 프로젝트 전용 서비스명·URI·권한·DB 정책은 이 공통 템플릿에 고정하지 않는다.
> 발동: 별도 AI Runtime의 API·RAG·Tool 연동 계약을 신설하거나 변경할 때. 일반 문서 작성, 모델 사용만 있는 작업에는 적용하지 않는다.

## 1. 인계 기준

- 제공자 / 소비자 / 각 담당자:
- 기준 저장소·커밋 또는 working-tree 식별·문서 버전:
- 계약 상태: Candidate / Confirmed / Deprecated
- 책임 기준 문서·포함/제외 범위·어댑터 route(있으면):
- 계약 확정 조건과 합의 근거:
- 구현·로컬 검증·병합·배포·실제 연동 상태: Report Template의 단계별 상태와 근거로 기록

Confirmed는 양측 계약 확정 상태다. 구현·배포·실제 연동 완료를 뜻하지 않는다.

## 2. 소유권과 권한 경계

- 업무 상태 전이·최종 저장·외부 부수 효과의 소유자:
- Runtime의 책임과 허용/금지된 DB·SQL·Write Tool 범위:
- 사용자·테넌트·리소스 권한 확인 주체:
- 클라이언트/Gateway 직접 호출 허용 여부와 근거:
- 모델 출력·검색 문서·Tool 인자를 신뢰하지 않고 검증하는 경계:

## 3. 전송과 실패 계약

- 동기/비동기 선택·URI/Method·요청/성공/오류 DTO·스키마 버전:
- request/trace ID, 멱등성 키 범위·유효기간·중복 요청 처리:
- timeout·retry 상한·재시도 가능 오류·취소/늦은 응답 처리:
- callback/polling·중복/순서 역전·부분 실패·재처리 소유자:
- failure code·retryable·degraded/사람 인계·가용성 한계:

## 4. 호출 신원과 위임

- 서비스 신원·검증 방법·issuer/audience/scope 등 적용 필드:
- 사용자 Subject·테넌트의 타입·전달 방식·검증·만료:
- 원본 Client/Gateway 자격증명의 전달 허용 범위와 근거:
- 역방향 호출 인증·권한·키 교체·검증 실패 시 거부 기준:

특정 토큰 방식이나 역할을 기본값으로 추정하지 않는다. 프로젝트가 선택한 인증 방식의 검증 근거를 기록한다.

## 5. 데이터와 관측

- 최소 입력/출력·파일/URL·RAG 근거·Tool DTO의 접근 범위·보관/삭제:
- Prompt·개인정보·비밀값·원본 URL의 로그/Metric/Trace 제외 또는 마스킹:
- 비민감 request/trace 상관관계·장애 탐지·운영 담당자:

## 6. 검증과 미결정 사항

- 제공자/소비자 계약 테스트: 정상·인증 실패·잘못된 ID/상태/스키마·timeout·중복·순서 역전 사례
- 실행 대상 버전·환경·명령·예상/관측 결과·증거 위치:
- mock 기반 계약 검증과 실제 Runtime 통합 검증의 구분:
- [AI 연동 체크리스트](checklists/ai-runtime-integration-checklist.md) 결과와 미확인 항목:
- 미결정 운영값·결정 담당자·다음 확인 방법·구현 중단 조건:

검증하지 않은 항목을 성공으로 채우지 않는다. Gate 선택과 최종 집계는 `08.QUALITY_GATE.md §7-2`, 상태 기록은 `06.REPORT_TEMPLATE.md`를 따른다.
