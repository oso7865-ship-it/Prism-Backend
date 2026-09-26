# 작업 리포트: 품질 재평가·Windows 진단·Git 게시

> 작성일: 2026-09-26
> 작업 브랜치: dev
> 커밋/PR: 게시 준비 중
> 작업 범위: M
> 적용 스킬: git-workflow, terminal-ops, troubleshooting-report
> 적용 Gate: Security Gate, Document Gate
> 위험도: 일반 (승인된 합성 유료 평가·기존 변경 게시; 기능 경계 유지)

## 0. 작업 범위 확인

[작업 계약](../docs/work-plans/2026-09-26_recheck-publish.md)에 따라 사용자가 승인한1~3단계를 진행한다. 실제 호출은 기존 synthetic corpus7개 각1회. 소스·키·DB 백업·로컬 환경은 Git 게시하지 않는다. backend/frontend dev는 공유 진행 상태이며 main 병합/배포와 구분한다. 아키텍처 main을 먼저 게시하고 소비 저장소 revision을 연결한다.

## 1. 재평가

deepseek-flash, rh1-3b9b53482a3791ef. 응답7/7 및 schema/anchor7/7 정상. 자동 기대치6/7 PASS, java-missing-lock-context는 추측성 NEEDS_CONTEXT2건으로 FAIL 유지. Python 심각도는 ERROR→WARNING으로 완화됐으나 호출자 기대를 가정하는 표현이 남아 있다. 이번 표본으로 품질 개선 완료/반복 일관성/실제품 정확도를 주장하지 않는다. 입력9,809/출력2,257, 합계12,066토큰. 호출시간 합계15.125초, 금액 미조회. 추가 재시도0.

[재평가 원자료](2026-09-26_quality-seven-cases-recheck.json). CLI exit1은 전송 실패가 아니라 평가 기대치 실패를 뜻한다. 원래 평가와 정답 기준을 보존했다. 이 실패를 숨기거나 점수 기준을 완화하지 않고 개발 브랜치의 알려진 품질 한계로 게시한다. 공개 출시 품질 게이트는 통과한 것으로 표시하지 않는다.

## 2. Windows 원인 조사

- 어디서: Windows PRism 테스트/로컬 API 프로세스, Psycopg 비동기 연결 중 native access violation 진단.
- 무엇: 진단2회 후 테스트는 계속되어8개 PASS/exit0. 이전 통합검증도170개 PASS였지만 간헐적 진단이 있었다.
- 어떻게: 격리 테스트 프로세스에 일시적인 vectored exception 관찰기를 등록했다. 예외는 계속 원래 처리기에 전달했고 관찰 후 제거했다. pytest는 성공 테스트의 stdout/stderr를 숨기므로 `-s`로 캡처만 해제해 주소·모듈을 확인했다.
- 왜: 두 예외 모두 **npggNT64.des+0x2769**에서 발생했다. 실행 중인 API의 로드 모듈 메타데이터도 **INCA Internet / nProtect GameGuard / x64 Rev222 / 2025,6,10,1**로 확인했다. Psycopg 코드에서 보인 traceback은 촉발 경로이며 실제 fault instruction은 외부 GameGuard 모듈에 있었다. 그 모듈 내부 결함의 상세 원인까지는 미확인이다.
- 해결/한계: 발생 모듈을 특정했다. GameGuard 우회·제거·게임 강제 종료·TLS 약화·faulthandler 숨김을 하지 않았다. 현재 PC에서 근본적으로 해결된 것으로 선언하지 않는다. GSS 옵션 변경도 효과 없었으므로 영구 적용하지 않았다.
- 앞으로: 사용자가 해당 게임을 정상 종료한 깨끗한 세션/재부팅 후 PRism을 실행하여 같은 테스트를 비교하거나, GameGuard 공급업체의 정상 업데이트/지원 경로로 해결한다. 진행 중인 게임 상태에 영향이 있어 임의 종료하지 않았다. CI Linux의 결과는 별도 환경 검증이며 Windows 해결 증명은 아니다.

[모듈·offset 관측](2026-09-26_windows-native-origin-uncaptured.json). DLL 절대 설치 경로와 다른 실행 앱 정보는 공개 기록에 넣지 않았다.

## 3. 문서·코드 정리

기존 README/OPEN_ITEMS의 App 등록/AI 미구현 문구를 최근 연동 기록에 맞게 정리했다. 과거 Report의 누락 헤더와 결합된 상태 필드를 형식 정정하되 수행 사실/한계는 보존했다. 과거 스킬 근거가 부족한 것은 미확인으로 남긴다. 0005 migration의 불필요한 괄호8개만 Ruff 기준으로 제거했고 SQL/스키마 의도는 변경하지 않았다. 아키텍처 문서 CI를 추가했다. 원본 하네스 동기화 없음.

## 4. 검증·게시

로컬/원격 확인 결과는 다음 절에 사건별로 기록한다. 아직 확인하지 않은 push/CI/main 병합/배포를 완료로 간주하지 않는다.

## 5. 남은 한계

AI 문맥 부족 오탐은 재평가에서도 남았다. 후속은 NEEDS_CONTEXT 허용 기준의 구조적 보강과 독립 corpus 검증이며 현재7개 표본에 맞춰 억지로 지적을 제거하지 않는다. Windows 외부 모듈 문제는 발생 지점 확인까지 완료했으며 깨끗한 Windows 세션 재검증이 필요하다. 공개 Webhook·배포·운영 준비는 이번 범위 밖이다.

## 6. 게시 전 확인 (2026-09-26)

- backend170 tests PASS/50.84초, Windows GameGuard 진단2회 재현. 합성 키 표식의 scanner 오탐을 런타임 문자열 조합으로 정리한 뒤 관련53 tests PASS/0.66초. 실제 키가 아니라 비밀 탐지 테스트용 가짜 입력이며 검사 규칙/테스트 의미를 완화하지 않았다.
- Ruff app/tests/migrations/scripts PASS, 전체137 Python 파일 format PASS, mypy110파일 PASS(이전 동일 앱 코드 검증).
- frontend build/typecheck PASS,38 tests PASS. 아키텍처 문서71개/ADR19개 및 helper90조합 검증 PASS, 기존 문서 길이 경고1개.
- 원격 fetch 결과 세 저장소 모두 게시 전 ahead0/behind0. 사용자와 sandbox 소유자가 다른 환경이라 global 설정 대신 해당 명령/하위 프로세스에만 정확한 safe.directory를 전달했다.
- 아키텍처 main cac51a07516cd2e36b3bf4cc45c9a17fad050002 게시 완료. [architecture CI](https://github.com/oso7865-ship-it/Prism-Architecture/actions/runs/36245178791) success 확인. backend/frontend architecture.json 연결 완료.
- 과거 Report의 실제 적용 스킬 근거가 없는 항목은 legacy로 명시하고 기존 기록을 보존했다. 정식 새 Report의 적용 스킬·Gate는 이번 실행 근거로 기록했다.
