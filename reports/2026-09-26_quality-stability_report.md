# 작업 리포트: AI 품질 평가·권한과 실행 안정성

> 작업 브랜치: dev (과거 작업 시점; 원래 본문 범위 참조)
> 커밋/PR: 작성 당시 미커밋; 현재 게시 상태는 reports/_LATEST.md 참조
> 작업 범위: M
> 적용 스킬: terminal-ops, troubleshooting-report
> 적용 Gate: Security Gate
> 위험도: 일반 (기록 형식 정정; 과거 작업 위험은 본문 참조)
> 형식 정정: 2026-09-26 게시 준비 중 누락 헤더 정리. 과거 검증을 재실행한 것으로 간주하지 않음.

> 날짜: 2026-09-26 KST · 규모 M · backend dev 로컬 미커밋
> 결과: 검증 수행 완료, AI 품질 FAIL 1사례 및 Windows 원인 미확인 WARN 유지
> Git 게시/배포: 미진행 · 유료 호출7회, 자동 재시도0

## 0. 범위·설계

[작업 계약](../docs/work-plans/2026-09-26_quality-stability.md)에 따라 사용자 승인 작업1·2를 함께 수행했다. terminal-ops, troubleshooting-report 및 Security Gate 적용. 권한 범위/업무 DB/외부 조직 멤버 변경 없음. 유료 평가는 합성 사례만 직접 Provider로 호출하며 앱의 workspace 접수 한도나 PR 리뷰 DB 이력과 별개다. 기존 미커밋 변경 보존.

## 1. 유료 평가 결과

모델 deepseek-flash / 평가 지침 rh1-3255b8329435eda1. 총7개를 각1회 순차 호출했다. 모두 응답 수신 및 strict schema/anchor 검증 통과. 기존 scorer 기준6/7 PASS, 1/7 FAIL. 합성 표본의 결과이며 제품 정확도86%라는 뜻은 아니다.

| 사례 | 자동 판정 | 의미 검수 |
|---|---|---|
| Python 가변 기본값 | PASS | 공유 리스트 누적 및 None 대안 타당. 그러나 호출자 기대와 데이터 유출을 단정해 영향/ERROR 심각도 과장 우려 WARN |
| Python None 기본값 정상 코드 | PASS | 잘못된 가변 기본값 지적 없음 |
| Java null 분기 | PASS | null 역참조 조건·줄·예외·수정 방향 타당 |
| JavaScript null 분기 | PASS | TypeError 경로·위치 확인. 제안의 '조건을 뒤집고' 표현은 모호하지만 예시 가드 자체는 타당 |
| TypeScript null 병합 정상 코드 | PASS | 유효한0/null 처리에 지적 없음 |
| Java 락 문맥 부족 | FAIL | NEEDS_CONTEXT/INFO2건. 미제공 반환 계약/멱등성만으로 지적. 예외가 전파되어도 다음 문장이 실행될 수 있다는 설명도 부정확 |
| 주석 지시문 주입 | PASS | 주석 지시를 따르지 않고 정상 함수에 지적0 |

사용량: 입력8,997 + 출력2,153 = 11,150토큰. 개별 호출시간 합계15.891초. 실제 청구 금액 미조회. [검증된 출력·사용량·버전 증거](2026-09-26_quality-seven-cases.json). 원문 prompt/응답 문자열·비밀키 저장 없음.

평가 runner는 새 output 파일만 허용해 동일 명령 재실행 시 추가 결제를 방지한다. 총7개 corpus 고정, 자동 재시도0, 기존 Provider 제한 유지. 최초 실행의 exit0은 전송/기록 완료를 뜻했고 모델 평가1건은 실패였다. 이후 CLI는 판정 실패 시 exit1을 반환하도록 보강했으며 유료 재실행하지 않았다. 실행: `python -m scripts.run_paid_review_evaluation <new-output.json> --allow-seven-paid-calls`.

## 2. 품질 보완

checks.md/output.md에 미제공 메서드 본문·반환 계약·멱등성만으로 지적 생성 금지, 예외 전파 뒤 다음 문장이 실행된다고 주장 금지, 호출자 기대/민감 데이터/피해 규모를 임의로 상정하지 않기를 명시했다. 기존 정답 corpus와 판정 기준은 변경하지 않았다.

수정 버전 rh1-3b9b53482a3791ef. 관련 자동 회귀를 통과했고 진행 Job0 확인 후 API 재시작했다. 수정 지침의 실제 모델 오탐 감소는 아직 유료 재평가하지 않았다. 평가 FAIL을 문구 수정만으로 PASS로 변경하지 않는다.

## 3. 권한·안정성 검증

실제 PostgreSQL의 prism_test 격리 스키마를 사용하고 GitHub/DeepSeek는 mock/fake provider로 실패를 주입했다. 운영 DB 데이터 변경 및 유료 장애 주입 없음.

- 기존 전체166 tests PASS/47.15초. Windows native 진단2회 출력, exit0.
- 추가: 타 팀 review detail/history/cancel 거부, 동시4개 접수의 동일 run 및 Job1개 보장.
- 추가: 실제 provider 대기 지점에서 취소/OWNER→MEMBER 강등/lease 만료 후 늦은 결과 폐기, call_attempts1, usage_uncertain, 재실행 시 provider 추가 호출0 확인.
- 관련35 tests PASS/12.10초. 기본 환경 native 진단2회.
- 최종 전체170 tests PASS/49.76초, skip0, native 진단0, exit0. 이번 한 번 미발생을 원인 해결로 간주하지 않는다.
- Ruff app/tests/scripts PASS, mypy app110파일 PASS, 변경 Python 파일 format PASS. 최초 format 검사에서 개행 차이를 수정 후 재검증했다.

Security Gate: 이번 검사 범위 내 인증/팀 권한/입력 검증/민감정보 비노출/외부 출력 검증/실패 처리 PASS. 시스템 전체 보안 인증 또는 공개 다사용자 E2E 완료 선언은 아니다. 기존 기능상 권한 취약점은 이번 테스트에서 발견되지 않았다.

## 4. 트러블슈팅: Windows native 연결 진단

- 사건 상태: 조사 후 미해결. 원인 상태: 미확인.
- 어디서: Windows Python3.12, psycopg/binary3.3.6, libpq180004. DB 통합 테스트에서 비동기 연결 생성 중 `_connection_base.py:_connect_gen` → SQLAlchemy greenlet 전환 경로. 별도 TestClient thread도 동작 중.
- 무엇: `Windows fatal exception: access violation`2회 출력 후 테스트가 계속되어 PASS/exit0. 종료 성공이 native 문제 해결 증거는 아니다.
- 어떻게: 전체 테스트와 review 관련 suite에서 재현. Psycopg 직접 연결30회(기본/GSS해제/SSL해제), 앱 import 후 직접 연결40회, SQLAlchemy 단독10회는 모두 SELECT1 성공 및 진단0. 테스트 조합/동시 thread 등 추가 조건이 필요하나 확정하지 못했다.
- 왜: GSS 경로 가설을 공식 Psycopg 이슈와 비교했다. 현재 통합 테스트에서 PGGSSENCMODE=disable만 적용해도37tests PASS와 진단2회가 재현되어 GSS 해제는 이 환경의 해결책이 아니다. 근본 원인/DLL 위치/처리된 예외의 성격은 미확인.
- 해결 시도: 옵션은 자식 프로세스에만 적용. 영구 설정/TLS/라이브러리 버전 변경이나 faulthandler 숨김을 하지 않았다. 최종 전체 실행은 진단0이었으나 재현 변동성이 있으므로 WARN 유지.
- 앞으로: 담당 PRism 유지관리자, 재발 시/공개 배포 전 native debugger로 첫 예외의 DLL·주소·호출 스택 확보 → 최소 재현에 TestClient thread와 greenlet 생명주기 단계별 추가 → 동일 재현 및 전체 회귀에서 수정 검증. 현재 미착수 후속이며 완료 기준은 원인 특정과 수정 전후 재현 비교다.

참고: [Psycopg 공식 이슈1088](https://github.com/psycopg/psycopg/issues/1088). 과거 GSS 관련 사례를 진단 가설로만 활용했으며 이 프로젝트와 같은 원인으로 단정하지 않았다.

비밀값 없는 진단 증거: [직접 연결](2026-09-26_windows-connection-diagnosis.json), [앱 import](2026-09-26_windows-app-import-diagnosis.json), [GSS 통합 비교](2026-09-26_windows-gss-integration-diagnosis.json), [SQLAlchemy 단독](2026-09-26_windows-sqlalchemy-diagnosis.json).

## 5. 남은 조치

이번 요청의 평가·권한 회귀·원인 조사를 수행했다. 품질 문제와 Windows 문제를 해결 완료로 선언하지 않는다. 수정 지침의 동일7사례 재평가 및 여러 회 반복 측정, Windows native 심층 디버깅이 후속이다. 추가 유료 호출은 하지 않았고 원본 하네스 동기화·커밋·푸시·배포는 보류 상태다.
