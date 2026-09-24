# 작업 리포트: 집행층 도입 — CI·시크릿 검사·브랜치 보호·PR 템플릿·2층 읽기 표면

> Superseded note:  
> 이 보고서의 다음 작업 판단은 `reports/_LATEST.md`가 가리키는 최신 Report로 대체되었다.  
> 과거 의사결정 근거로는 유효하지만, 현재 Next Work 판단은 최신 Report와 `05.WORKING_CONTEXT.md`를 우선한다.

> 작성일: 2026-08-03  
> 패키징/배포일: 해당 없음  
> 작업 브랜치: `enforcement-260803`  
> 커밋/PR: `38db27a`(본 작업), 헤더 갱신 후속 커밋 1건  
> 작업 범위: L  
> 적용 스킬: `planning`, `git-workflow`, `terminal-ops`, `verification-loop`, `report-consistency`  
> 적용 Gate: `gates/document-gate.md`  
> 위험도: 구조 + 환경 변경(비파괴적: 저장소 브랜치 보호 설정)  
> 위험 작업 여부: 예(사용자의 명시 요청 "그 4개들 전부 다 진행해줘"가 근거)

---

## 0. 작업 범위 확인

| 항목 | 내용 |
|---|---|
| 요청 요약 | "현업 수준" 평가에서 제시한 4개 항목 — CI 강제 검증, PR 템플릿, main 브랜치 보호, 읽기 표면 압축 — 을 전부 구현한다 |
| 수정 대상 | 저장소 루트 .github 폴더의 워크플로우 `harness-ci.yml`(신규)과 PR 템플릿 `pull_request_template.md`(신규), `scripts/validate-no-secrets.mjs`(신규), `scripts/validate-harness.mjs`, `08.QUALITY_GATE.md §10-1`, `03.CONTEXT_BUDGET.md §2-2-1`(신규 절), 루트 `AGENTS.md`(읽기 표면 절), `README.md`(Git 운영·자동 검증), `10.ADR.md`(ADR-044), `_PENDING_IMPORT_LIST.md §6-1`, GitHub 저장소 브랜치 보호 설정 |
| 제외 대상 | 기존 규칙 문서의 내용 삭제·완화(규칙층은 유지, 집행 장치만 추가), required review 강제(1인 운영에서 자기 승인 불가로 교착됨) |
| 근거 | 실사용 준수율 실측(planning 0/7, Git 기록 10/10 누락)과 실제 유출 사고 2건 — 상세는 ADR-044 배경 |
| 적용 스킬/Gate | 헤더와 동일 |
| 위험도 | 구조 + 환경 변경(비파괴적) |
| 검증 방법 | 검증 스크립트 7종 전체 실행(신규 no-secrets 포함), no-secrets 네거티브 테스트(가짜 AWS 키 스테이징 → FAIL 확인), PR에서 CI 실제 실행 확인, 브랜치 보호 설정 후 API 조회로 확인 |
| 한계 | CI는 GitHub Actions 환경에 종속(다른 호스팅으로 이전 시 워크플로우 재작성 필요). 시크릿 검사는 알려진 토큰 패턴만 탐지 |

## 1. 작업 요약

- **CI(harness-ci)**: push(main)·PR마다 검증 스크립트 7종을 ubuntu + Node 20에서 강제 실행. job 이름 `validate`가 브랜치 보호의 required status check.
- **`validate-no-secrets.mjs` 신설**: Git 추적 파일에서 금지 파일 패턴(`.claude/`, `*.zip`, `.env*`, 키/인증서, SSH 개인키)과 토큰 패턴(AWS/GitHub/Slack/sk-/Google/개인키 블록/JWT) 검사. 가짜 AWS 키로 탐지 능력 검증 완료(FAIL exit 1).
- **PR 템플릿**: 작업 범위·위험도·적용 Skill/Gate·검증 체크박스·Report 경로·미해결 항목.
- **브랜치 보호(main)**: required status check(validate), force-push 금지, 삭제 금지. 1인 운영 특성상 required review는 제외.
- **2층 읽기 모델**(`03.CONTEXT_BUDGET.md §2-2-1`): 상시 표면 4개+α(AGENTS/QUICK_REF/GateGuard §6-1/발동 스킬)와 트리거 기반 심층 문서로 분리. "혹시 몰라서 미리 읽기"는 WARN, "트리거 발생했는데 안 읽기"는 FAIL. `AGENTS.md`에 요약 절 추가.

## 2. 변경 파일

| 파일 | 변경 내용 | 이유 |
|---|---|---|
| 루트 .github: 워크플로우 `harness-ci.yml`(신규) | 검증 7종 CI | 실행 강제 |
| 루트 .github: PR 템플릿 `pull_request_template.md`(신규) | PR 확인 항목 | Report·GateGuard 가시화 |
| `scripts/validate-no-secrets.mjs`(신규) | 시크릿·민감 파일 검사 | 유출 사고 2건 재발 차단 |
| `scripts/validate-harness.mjs` | 필수 목록에 no-secrets 추가 | 구조 정합성 |
| `08.QUALITY_GATE.md §10-1` | no-secrets 보증 범위 행 | 스크립트 한계 문서화 |
| `03.CONTEXT_BUDGET.md §2-2-1` | 2층 읽기 모델 신설 | 준수율 역학 대응 |
| 루트 `AGENTS.md` | 읽기 표면 절 추가 | 진입점에서 1층 안내 |
| `README.md` | Git 운영·자동 검증 갱신 | 집행층 반영 |
| `10.ADR.md` | ADR-044 | 구조 결정 기록 |
| `_PENDING_IMPORT_LIST.md §6-1` | no-secrets 반영 완료 행 | 상태 추적 |

## 3. 검증 결과

| 검증 항목 | 결과 | 비고 |
|---|---|---|
| 검증 스크립트 7종 로컬 실행 | PASS | 이 Report 게시 후 재실행 기준 |
| no-secrets 네거티브 테스트 | PASS | 가짜 `AKIA...` 키 스테이징 시 FAIL exit 1, 제거 후 PASS 복귀 확인 |
| CI 실제 실행 | PR 생성 후 확인 | PR의 validate check 통과를 병합 전 확인한다 |
| 브랜치 보호 적용 | 설정 후 API 조회로 확인 | required check=validate, force-push/삭제 금지 |

## 4. Checklist 결과

| Checklist | 결과 | Report 반영 |
|---|---|---|
| 해당 없음 | — | 문서·스크립트·저장소 설정 작업. `gates/document-gate.md` 기준 판정 |

## 5. 발견된 문제

| 심각도 | 문제 | 처리 |
|---|---|---|
| — | 없음 | — |

## 6. 미해결 항목

- 브랜치 보호의 required review는 1인 운영에서 도입 불가(자기 승인 불가) — 협업자가 생기면 재검토
- 과거 커밋 이력에 이미 들어간 비밀값은 이 검사의 범위 밖(GitHub Support 캐시 삭제 여부는 사용자 판단 대기 — 이전 Report 이월)
- 챱챱 폴더 측 이월 작업(변동 없음)

## 7. Working Context 반영 여부

- 반영 필요: 예
- 반영 내용: 자동화가 "최소 검증 스크립트 7개(로컬)"에서 "8개 + CI 강제 실행"으로 변경됨 — §1 표의 자동화 행은 부착 프로젝트 기입 항목이라 템플릿 기본값 주석만 유지

## 8. 다음 작업

1. PR CI 통과 확인 → 브랜치 보호 설정 → `main` 병합
2. 다음 프로젝트 부착 시 2층 읽기 모델의 실효(스킬 발동률 개선 여부)를 환류 데이터로 확인
3. 협업자 추가 시 required review 도입 재검토
