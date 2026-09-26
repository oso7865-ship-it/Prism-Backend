# DeepSeek 리뷰 하네스 설계·작업 계약

## 목표·경계

사용자가 승인한 리뷰 하네스를 설계 후 구현한다. 개발 에이전트용 GENERAL_HARNESS와 독립적인 제품 코드다. backend review가 신뢰된 문서와 조합기를 소유한다. backend/frontend dev, architecture main. 접근 권한/호출 한도/코드 전송량은 유지한다. DB migration·기존 결과 변경·추가 유료 호출은 없다. 기존 Security Gate와 UI 규칙 적용, 스킬 생성/하네스 동기화 작업 아님.

## 계약

1. 신뢰된 서버 패키지의 공통 원칙·검토 절차·출력 기준·4개 언어 지침 Markdown을 고정 allowlist로 로드한다. 저장소 AGENTS/README/주석은 시스템 지침으로 로드하지 않는다.
2. core+checks+output+입력에 실제 포함된 언어 지침만 SystemMessage로 조합하고 기존 strict JSON schema를 덧붙인다. 코드 JSON은 HumanMessage에 둔다. system 입력 최대24KiB, 기존 user 입력24KiB 한도는 별개이며 출력2000token/호출1회 유지.
3. 전체 패키지 내용과 출력 schema의 SHA256에서 prompt_version(rh1-16hex)을 계산한다. 실행 접수·중복키·worker 버전 검증에 기존 컬럼을 사용한다. 코드 변경은 재시작 후 반영되며 이전 대기 버전은 재호출하지 않는다.
4. 성공 result.harness에 version, 선택 module 이름, 실제 system prompt SHA256을 저장한다. 원문 prompt는 저장하지 않는다. 실패도 row.prompt_version으로 패키지 버전을 추적할 수 있다.
5. issue에 basis=SUPPORTED/NEEDS_CONTEXT를 요구한다. 관측된 코드와 추가 확인을 구분한다. 불확실성만으로 결함을 단정하지 않고 실행 가능한 근거가 없는 추측은 limitations에 남긴다. 이전 결과의 basis/harness 부재는 UI가 호환한다.
6. 알려진 결함·정상 코드·동시성 문맥 부족·지시문 주입 사례로 평가 corpus와 평가기를 만든다. 자동 검증은 schema/anchor/기대 위치/오탐 여부의 기계적 기준이며 실제 LLM 정확도 검증과 구분한다. 모델 평가 시 같은 corpus 결과를 입력받아 비교하며 이번에는 유료 호출하지 않는다.

## 체크리스트

- [x] 현황 조사·설계·권한/전송 경계 확인
- [x] ADR-REVIEW-004·문서/매핑
- [x] 리뷰 문서 패키지·조합/버전·Provider 연결
- [x] 판단 근거 구분·이력 표시
- [x] 평가 사례·평가기·테스트
- [x] 타입/빌드·서버 반영·보고
