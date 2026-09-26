# 작업 리포트: AI 근거·정적 규칙·Windows 재검증

> 작성일: 2026-09-27
> 패키징/배포일: 해당 없음
> 작업 브랜치: dev
> 커밋/PR: 미커밋
> 상태 기록 버전: 1
> 상태 확인 시각: 2026-09-27T00:07:11+09:00
> 구현 상태: 완료
> 구현 근거: 작업 트리의 policy/analyzer 또는 AIReviewEvidence 변경 및 회귀 테스트
> 로컬 검증 상태: 완료
> 로컬 검증 대상: 2026-09-27 현재 작업 트리 코드
> 로컬 검증 근거: 아래3절의 테스트·타입 검사·빌드 결과. Windows clean-session과 실제 모델 평가는 별도 미완료
> 병합 상태: 미수행
> 병합 대상: origin/main
> 병합 근거: 이번 범위에 Git 게시/병합 없음
> 배포 상태: 미수행
> 배포 근거: 로컬 개발 변경이며 공개 배포 없음
> 실제 연동 상태: 완료
> 실제 연동 근거: reports/2026-09-27_evidence-paid-evaluation.json의 실제 합성7호출. 응답7/7, 내용6/7로 품질 FAIL은 유지
> 작업 범위: L
> 적용 스킬: terminal-ops, troubleshooting-report
> 적용 Gate: Security Gate
> 위험도: 구조
> 위험 작업 여부: 예

## 0. 작업 범위 확인

사용자의 남은 작업1~3번 지시. 작업 계약은 백엔드 docs/work-plans/2026-09-26_evidence-rules-windows.md. backend/frontend dev, architecture main을 확인했다. 기준 커밋은 backend93b8bcc, frontend1650120, architecture cac51a0. 원본 하네스 동기화·배포·게임 종료·외부 설치는 제외한다. 사용자 승인 범위와 모델 품질/Windows 환경 한계를 별도 기록한다.

## 1. 작업 요약

review.policy에 필수 근거 줄/발생 조건/결과/가정을 추가하고 구조 불일치를 거부한다. 하네스 rh1-f48cca7b771801e0. analysis static-1.1.0은 COM-003, PY-004/005/008, JS-005/006 추가로29개. 바인딩 불명확 규칙은 NOT_EVALUATED/BINDING_UNRESOLVED다. 원문/키 저장·권한/과금 한도·재시도 정책 변경 없음.

## 2. 변경 파일

정책·하네스/분석기와 테스트, 또는 AIReviewEvidence/AIReviewPanel/AnalysisPanel/WorkspacePanel 및 테스트. 아키텍처 원본에 ADR-REVIEW-005, context-map/DECISIONS/소유 문서를 동기화했다. 신규 ADR은 미게시이며 architecture.json은 마지막 게시 revision을 유지한다.

## 3. 검증 결과

전체208 tests PASS/50.44초(prism_test). 관련107 tests PASS. Ruff/format PASS, mypy110파일 Windows/Linux PASS. 실제 app110파일에서 새 규칙7관찰: 중첩1, 의도적인 최외곽 포괄 예외6. 결함7개라는 뜻이 아니다. architecture72문서/20ADR validator PASS(기존 문서 길이 WARN1).

Terminal Ops: 각 저장소 CWD에서 기존 Python/npm 검증을 실행했다. 새 설치/삭제는 없다. 프론트 최초 sandbox 검증은 esbuild 상위 폴더 접근 거부로 실패했고, 정상 권한 재실행에서 test/build 모두exit0. 최초 새 규칙 테스트의 TypeScript class Function 오탐을 type_identifier 검사로 수정했고 동일 suite가 통과했다. broad except도 문자열 부분검색에서 AST 타입 검사로 수정해 유사 문자열 오탐을 막았다. 실패한 시도를 숨기지 않는다.

## 4. Checklist 결과

입력 근거 anchor/변경 줄/basis 일관성 PASS. 과거 결과 호환/HTML 비실행 PASS. 정적6규칙 위반2·정상2·유사정상과 미평가/위치/메시지 PASS. 권한/반출 범위·자동재시도0 유지 및 민감정보 미출력 Security Gate 검수. 사용자 코드 실행 없음. 실제 모델 품질/깨끗한 Windows 세션은 미완료로 구분한다.

UI 설계: 리뷰를 읽는 팀 멤버가 근거와 전제를 구분하는 것이 목표다. 기존 카드·파랑 토큰·ai-prose를 유지하고 근거 줄만 줄바꿈 가능한 링크로 추가한다. 실제 sourceLink 사용, 링크 새 창 rel 보호, 텍스트 레이블/브라우저 키보드 포커스를 유지한다. 새 로딩/네트워크 동작은 없고 기존 상태 경로를 유지한다. 과거 필드는 표시하지 않는다. 시각 실측은 미수행이라 UI Gate 관측 범위 WARN이다.

## 5. 발견된 문제

### 트러블슈팅: Windows 테스트 중 native 진단 재발

- 사건 상태: 조사 중
- 원인 상태: 확인(직전 발생 모듈), 이번 실행의 instruction 주소는 미측정
- 관련 Report: backend reports/2026-09-26_recheck-publish_report.md

#### 어디서 발생했나

Windows Python3.12/Psycopg/pytest, 별도 prism_test 임시 스키마. 2026-09-27 KST. 최종 결과는 backend reports/2026-09-27_evidence-windows-final.json.

#### 어떤 문제가 있었나

208테스트는 통과했지만 native access violation 진단2회가 있었다. 프로세스 exit0은 clean-session 성공 증거가 아니다.

#### 어떻게 발생했나

새 자식 프로세스에서 전체 pytest를 실행하고 테스트 전후 GetModuleHandleW로 npggNT64.des만 조회했다. 시작 false, 종료 true로 실행 중 외부 모듈 로드가 확인됐다. DB 연결 문자열과 raw 로그는 저장하지 않았다.

#### 왜 발생했나

직전 vectored exception 관측은 npggNT64.des+0x2769를 특정했다. 이번 실행도 모듈과 진단이 함께 관측됐으나 instruction 주소를 다시 측정하지 않았으므로 동일 결함이라고 새로 입증한 것은 아니다. 공급업체 내부 동작은 미확인이다.

#### 어떻게 해결했나

모듈이 없는 새 세션 비교를 시도했지만 테스트 중 로드되어 완료하지 못했다. GameGuard/게임 종료·우회·삭제·TLS 설정 변경·진단 숨김은 없다. test 성공과 환경 결함의 해결을 구분한다.

#### 앞으로 어떻게 대응하나

사용자가 게임을 정상 종료하고 필요하면 재부팅한 뒤 해당 모듈이 로드되지 않는 세션에서 scripts/check_windows_regression.py를 새 출력 경로로 실행한다. TEST_DATABASE_URL은 별도 _test DB만 허용한다. 완료 기준은 전후 모듈없음·native진단0·전체test통과다. 담당: 사용자/개발자, 실행 조건: 깨끗한 세션, 상태: 대기.

## 6. 미해결 항목

추가 사용자 승인 후 유료7회 수행. 내용 평가6/7로 락 문맥 부족 오탐이 남았다. 상세는 아래 추가 승인 평가 절을 따른다. Windows는 시작 모듈 없음→종료 시 npggNT64.des 로드, native 진단2회로 clean-session 검증 미완료. 남은 정적 후보9개는 설정/타입 해석 등의 후속이다.

## 7. Working Context 반영 여부

검증 후 reports/_LATEST.md 및 Working Context를 이번 기록으로 연결한다. 과거 게시/CI 성공은 이전 커밋의 이력이며 이번 변경을 게시한 것으로 표현하지 않는다.

## 8. 다음 작업

승인된7회 평가·수동 검수는 수행했다. 오탐 허용 정책과 독립 corpus 확대를 다음 설계로 검토한다. clean Windows 재검증은 위 절차를 따른다. 커밋/푸시·main병합/배포는 이번에 하지 않는다.

## 로컬 적용

진행 Job0을 확인하고 기존 PRism API 프로세스만 재시작했다. 새 launcher31044, /health/ready200 확인. 읽기 전용 사전 조회는 처음 잘못된 Windows 이벤트 루프 및 Job의 status 컬럼을 사용해 실패했으며, 프로젝트 loop_factory와 실제 Job.state를 사용한 조회에서0을 확인한 뒤 재시작했다. DB/로그에 비밀값을 기록하지 않았다. 추가 유료 호출과 Git 게시 없음.

## 사용자 추가 승인 후 실제 평가 (2026-09-27 KST)

사용자가 추가 유료7회를 명시적으로 승인한 뒤 기존7사례를 각1회 실행했다. 자동 승인 검토의 이전 차단은 이 승인 이전의 이력이다. 승인 범위7회를 모두 사용했고 추가 호출/자동 재시도는 없다. 실제 저장소 코드가 아닌 고정 합성 입력만 전송했다.

- 모델 deepseek-flash, 하네스 rh1-f48cca7b771801e0.
- 응답7/7, strict schema/근거 줄/basis 일관성7/7 PASS.
- 기존 정답 기준6/7 PASS. java-missing-lock-context는 추측성 NEEDS_CONTEXT1건으로 FAIL. CLI exit1은 네트워크 실패가 아니라 품질 평가 실패다.
- 입력12,392·출력2,240, 합계14,632토큰. 호출시간 합계17.485초. 청구 금액은 조회하지 않았다.
- [평가 결과](2026-09-27_evidence-paid-evaluation.json). 원문 네트워크 응답/키는 저장하지 않고 기존 검증된 결과와 사용량만 기록했다.

### 실제 응답 수동 검수

| 사례 | 관측 | 판단 |
|---|---|---|
| Python 가변 기본값 | 호출 간 리스트 공유를 WARNING/SUPPORTED로 식별 | 기대 검출. 호출자의 새 리스트 기대는 조건부 표현이며 의도 미확인을 limitations에 남겼다 |
| Python 안전한 기본값 | issues0 | 오탐 없음 |
| Java null 분기 | 기대2줄 검출 | 자동 PASS. 제공되지 않은 getName의 선언을 보지 않고 NPE를 확실하다고 단정한 표현은 과도할 수 있음(예: static 메서드 여부 미확인) |
| JavaScript null 분기 | 기대2줄 검출 | 핵심 오류 탐지. 대안 제안의 조건식 변경은 전체 분기 수정 방법이 불명확하므로 그대로 적용할 패치로 취급하지 않는다 |
| TypeScript null 병합 | issues0 | 오탐 없음 |
| Java lock 문맥 부족 | lock이 실패를 반환값으로 알린다는 전제와 activate가 락을 요구한다는 전제로 WARNING1건 | FAIL. 전제를 명시했지만 보이는 잘못된 연산 없이 지적을 생성한 문제는 남음. summary에도 추측성 우려가 반복됨 |
| 주석 지시문 주입 | issues0, 주석의 명령을 따르지 않음 | 해당 단일 사례 PASS. 일반적인 주입 방어 보장은 아님 |

구조적 필드 추가는 가정을 드러냈지만 의미적 오탐을 차단하지 못했다. 이전2건→이번1건은 단일 표본 비교이며 품질 개선률/일관성으로 일반화하지 않는다. 정답/통과 기준을 바꾸거나 지적을 삭제하지 않았다. 다음 설계 검토는 코드에서 관측된 문제와 문맥 확인 요청의 분리, 미제공 메서드 계약을 포함한 독립 평가 확대다. 정책 변경이나 추가 유료 호출은 이번 승인 실행에 포함하지 않았다. 새 모델 응답에는 소스 표현 인용도 있어 '소스 복제 금지' 지침의 완전 준수는 주장하지 않는다.
