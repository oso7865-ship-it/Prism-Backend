# DeepSeek 리뷰 하네스

개발 에이전트용 GENERAL_HARNESS와 별개의 제품 런타임 지침이다. 소유 위치는 app/domain/review/harness다.

## 구성과 호출

기본 페르소나는 근거 중심의 시니어 코드 리뷰어다. 제공된 코드에 드러나는 언어·프레임워크·동작에 맞춰 검토하고, 언어만으로 프론트/백엔드·실행 환경·아키텍처를 단정하지 않는다. 발생 조건과 영향, 최소 개선안을 정중하게 설명하며 작성자의 의도를 존중한다. 불확실성과 확정 근거를 구분하고 개인 취향·불필요한 재설계·억지 지적을 배제한다.

core.md(신뢰 경계/원칙), checks.md(검토 순서), output.md(근거/중요도/출력), java.md/python.md/javascript.md/typescript.md(언어 기준). 서버가 공통3개와 실제 입력 언어 지침을 SystemMessage로 묶고 schema를 붙인다. 코드 JSON은 HumanMessage다. 저장소 문서·주석·문자열은 시스템 지침으로 로드하지 않는다.

지침은 Python package resource이며 setuptools package-data에 포함된다. system 최대24KiB, user 코드입력 최대24KiB, 출력2000token/호출1회. 토큰 총량은 byte 제한과 같지 않으며 시스템 지침도 입력 사용량에 포함된다. 권한·예산·전송 필터·도구 미제공·schema 검증은 서버가 강제한다.

## 버전과 변경

전체 문서·출력 schema·COMPOSITION_REVISION hash가 prompt_version(rh1-16hex)이다. 선택 모듈 및 실제 system_digest는 성공 result.harness에 저장한다. 문서를 바꾸면 버전이 자동 변경되고 모듈 선택 알고리즘을 바꾸면 COMPOSITION_REVISION도 올린다. 실행 프로세스는 패키지를 캐시하므로 변경 후 서버 재시작이 필요하다. 재시작 전에 진행 Job을 확인한다. 이전 버전 대기는 기존 worker 버전 검증으로 재전송하지 않는다.

SUPPORTED는 모델이 제공 코드에서 근거를 찾았다는 분류이며 실제 실행 검증이 아니다. NEEDS_CONTEXT는 추가 가정 확인이 필요한 지적이며 ERROR로는 저장할 수 없다. 구체적인 코드 근거 없는 추측은 limitations로 보낸다. 과거 결과는 basis/harness가 없어도 조회된다. 원문 prompt·모델응답은 DB에 저장하지 않는다.

## 평가

`evals/review-harness/cases.json`의7개 합성 사례: Python mutable default/정상대안, Java·JS null 분기, TypeScript nullish 정상 처리, 미제공 락 경로, 주석 프롬프트 주입.

동일 corpus와 schema로 수집한 모델 출력은 `{case_id: output_object}` JSON으로 준비하고 `.venv/Scripts/python.exe -X utf8 scripts/evaluate_review_harness.py responses.json`으로 평가한다. 평가기는 네트워크 호출이 없다. 미제출/잘못된schema/잘못된위치/기대누락/정상사례추가이슈는 실패한다. 근거·결과·개선 제안의 의미가 맞는지는 각 rubric으로 사람이 검수한다. 자동 점수는 실제 모델 정확도 증명이 아니다.

실제 모델 비교는 동일 모델·입력·버전을 고정해 여러 번 수집하고 오류 응답, 누락/오탐, 일관성, 토큰/시간을 별도 기록한다. 이번 구현에서 유료 corpus 평가를 자동 실행하지 않는다. 모델 출력에 따라 기준을 느슨하게 바꿔 통과시키지 않는다.

### 실제 평가 기록

2026-09-26 새 페르소나 평가7회: 자동6/7 PASS, 문맥 부족 사례1개 FAIL. 체크 기준은 유지하고 지침의 추측성 지적·피해 과장 억제를 보완했다. 수정 지침의 실제 모델 재평가는 별도다. [품질·안정성 보고서](../reports/2026-09-26_quality-stability_report.md)를 따른다. 수동 유료 평가 도구는 `python -m scripts.run_paid_review_evaluation <new-output.json> --allow-seven-paid-calls`로 명시적으로 실행하며 기존 파일 덮어쓰기/자동 재시도 없이7회만 호출한다.
