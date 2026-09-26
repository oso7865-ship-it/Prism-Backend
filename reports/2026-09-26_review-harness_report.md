# 작업 리포트: DeepSeek 리뷰 하네스

> 작업 브랜치: dev (과거 작업 시점; 원래 본문 범위 참조)
> 커밋/PR: 작성 당시 미커밋; 현재 게시 상태는 reports/_LATEST.md 참조
> 작업 범위: M
> 형식 상태: legacy
> 과거 적용 스킬 기록: 미확인 (이전 본문에 남은 적용 기록만 유효)
> 적용 Gate: 기존 본문 검증 범위 참조; 새 Gate 수행을 소급 주장하지 않음
> 위험도: 일반 (기록 형식 정정; 과거 작업 위험은 본문 참조)
> 형식 정정: 2026-09-26 게시 준비 중 누락 헤더 정리. 과거 검증을 재실행한 것으로 간주하지 않음.

> 작성일: 2026-09-26 · 확인: 2026-09-26T20:25:27+09:00
> 브랜치: backend/frontend dev, architecture main · 미커밋
> 구현: 완료 · 로컬 검증: PASS, 기존 Windows 진단 WARN
> 병합/배포: 미진행 · 추가 유료 모델 호출: 0
> 범위: M · Security Gate/기존 UI 규칙 적용

## 0. 작업 범위 확인

사용자가 승인한 모델용 리뷰 하네스를 설계 후 구현했다. GENERAL_HARNESS와 별개의 제품 기능이다. 기존 호출 한도/접근 권한·소스 전송 제한 유지. DB migration/기존 결과 수정/하네스 동기화 없음.

## 구현

ADR-REVIEW-004와 소유 문서·결정/context-map을 갱신했다. review/harness의 core/checks/output 및 Java/Python/JavaScript/TypeScript Markdown을 allowlist로 읽어 실제 입력 언어만 SystemMessage에 조합한다. 저장소 코드·지침·주석은 HumanMessage 데이터다. 모델 도구 권한은 계속 없다.

문서·출력 schema·조합 revision의 digest가 prompt_version이며 현재 rh1-d9133f8d1cc6f1c1이다. 성공 result.harness에는 version/modules/system_digest만 저장한다. 원문 prompt 미보관. 전체 언어 지침을 포함한 system6087bytes로24KiB 이내. 사용자 코드 JSON24KiB 제한은 별개이며 system도 API 입력 토큰을 소비한다.

새 지적 basis=SUPPORTED/NEEDS_CONTEXT. 전자는 제공 코드 근거, 후자는 추가 확인 필요로 표시한다. NEEDS_CONTEXT+ERROR는 서버가 거부한다. 이 분류는 모델 판단이며 실행 검증과 다르다. 기존 결과는 basis/harness 없이 조회되고 기존 prompt_version도 표시한다.

## 검증

- 관련 backend31개 PASS /7.66초: 언어별 선택·신뢰 경계·digest 변경·system 한도·실제 Provider wiring(mock ChatDeepSeek)·출력 anchor/basis·DB 이력 metadata·이전 지침 Job 외부호출0.
- ruff PASS, mypy110파일 PASS.
- frontend typecheck/build PASS(51modules),38개 테스트 PASS.
- architecture validator PASS,19 ADR; 기존 긴 관계 문서 경고1개.
-7개 합성 평가 사례와 오프라인 CLI 구현. reference fixture로 schema/anchor 기대치 scorer7개 PASS. 실제 모델 출력 평가나 정확도 측정이 아니다.
- API 시작 후 ready200. 실행 전 대기/진행 Job0 확인. 프런트 개발 서버도 재실행.

## 한계·후속

실제 DeepSeek에 새 지침을 보낸 유료 평가 호출은 이번에 실행하지 않았다. 다음 수동 리뷰부터 적용된다. 같은 corpus·모델·지침 버전으로 실제 출력 여러 회를 수집해 누락/오탐/일관성/토큰을 비교하고 근거의 의미는 사람이 rubric으로 검수해야 한다.

기존 Windows native access-violation 진단이 일부 테스트에서 출력됐지만31개 완료 exit0이다. 원인 해결은 후속이다. 공개 배포·금액 예산·보관 정책·Git 게시와 하네스 동기화는 미진행.

## 후속: 유료 평가 1회 시도 (2026-09-26 20:28 KST)

- 작업 계약: 사용자 요청에 따라 기존 DeepSeekProvider로 python-mutable-default 합성 사례를 1회 평가한다. terminal-ops 적용. 수정 범위는 평가 증거/이 보고서이며 제품 코드·DB·환경·Git 게시 제외. 외부 API 비용은 사용자 요청으로 승인됨. schema/anchor 자동 점수와 의미 검수를 완료 기준으로 삼았다.
- 실행: backend에서 .venv/Scripts/python.exe -X utf8 - 로 로컬 평가 코드 실행. deepseek-flash, rh1-d9133f8d1cc6f1c1, core/checks/output/python 모듈. 재시도 0.
- 결과: Provider 호출 1회가 0.234초 후 OpenAIConnectionError로 실패했다. 응답을 수신하지 못해 schema/의미 평가 미실시. 원인이 네트워크 제한인지 서비스 상태인지는 확인되지 않았다. 유료 평가 성공으로 집계하지 않는다.
- 사용 토큰/실제 과금: 응답이 없어 확인 불가. 0원 또는 과금 발생으로 단정하지 않는다.
- 검증: 프로세스 exit0은 실패 기록 저장 성공만 뜻한다. 모델 평가 상태 FAILED이며 품질 PASS가 아니다. 자동 재호출하지 않았다. 키·원문 prompt·원문 응답·상세 예외는 저장하지 않았다.
- 증거: [평가 시도 기록](2026-09-26_review-harness-paid-eval.json).
- 후속: API 연결 경로 확인 후 별도 실행에서 재평가 필요. 기존 구현 검증 결과는 유효하며 실제 모델 품질은 아직 미검증이다.

### 평가 연결 오류 진단 (2026-09-26)

사용자의 원인 확인 요청에 따라 유료 모델 호출 없이 api.deepseek.com:443 TCP/TLS 연결을 비교했다. 기본 제한 실행에서는 DNS 성공 후 socket 연결이 PermissionError [WinError 10013]으로 거부됐다. 승인된 제한 밖 실행에서는 TCP 연결 및 TLSv1.3 협상 모두 성공했다. 현재 재현 증거는 실행 샌드박스의 네트워크 제한을 원인으로 지목한다. 최초 Provider 예외의 내부 원인은 저장하지 않아 최초 오류와의 동일성을 직접 추적한 것은 아니다. API 키 유효성/모델 응답은 이번 진단에서 검증하지 않았다. 추가 모델 호출 0회. 후속 평가 시 승인된 네트워크 실행 경로를 사용한다.

### 승인된 네트워크 경로에서 유료 평가 완료 (2026-09-26 20:31 KST)

- 사용자 재실행 승인 후 DeepSeekProvider 1회 호출, 자동 재시도 0. deepseek-flash / rh1-d9133f8d1cc6f1c1 / python-mutable-default. 제품 코드·설정·DB 변경 없음.
- 결과 COMPLETED, 2.547초. 입력 1,158 / 출력 333 / 합계 1,491토큰. 실제 청구 금액은 조회하지 않았다.
- 서버 schema/anchor 검증 및 기존 scorer PASS: 기대 sample.py 1줄 SUPPORTED 지적 1건, 누락0·예상 외 위치0. 원문 응답 대신 검증된 결과와 메타데이터만 저장했다.
- 의미 검수 PASS: 함수 정의 시 생성된 기본 리스트가 인자 생략 호출 간 공유되고 append 결과가 누적된다는 근거가 제공된 코드와 일치한다. None 기본값 및 함수 내부 새 리스트 생성 제안도 타당하다. 근거의 '모든 호출' 표현은 정확히는 items를 생략한 호출이며, 이어지는 설명과 limitations에서 조건을 명시했다. ERROR 심각도는 실제 호출 의도/영향 정보가 없어 적정성을 별도로 확정하지 않았다.
- 범위 한계: 합성 사례 1개 1회 평가이며 전체 7개 corpus 또는 제품 전체 정확도·오탐률·반복 일관성 검증은 아니다. 앱 PR 리뷰 이력/일일 한도를 사용하지 않는 별도 평가다.
- 증거: [실제 평가 결과](2026-09-26_review-harness-paid-eval-network-approved.json). 이전 연결 실패 기록은 보존. 실행 exit0 및 결과 COMPLETED 확인. 추가 API 호출·커밋·푸시 없음.

### 시니어 리뷰어 페르소나·전체 현황 (2026-09-26)

사용자 승인으로 core.md에 근거 중심 시니어 역할, 환경 추정 금지, 정중한 최소 개선안, 작성자 의도 존중을 반영했다. docs/REVIEW_HARNESS.md와 [전체 현황](../docs/PROJECT_STATUS.md)에 계약·진행률 산정·근거·남은 작업을 기록했다. 새 버전 rh1-3255b8329435eda1. 관련 pytest27개 PASS/1.05초, cache 쓰기 권한 경고1개. 진행 Job0 확인 후 API 재시작 및 ready200. 추가 유료 호출0이며 이전 유료 평가 성공을 새 버전 품질 검증으로 재사용하지 않는다. Git 게시 없음.
