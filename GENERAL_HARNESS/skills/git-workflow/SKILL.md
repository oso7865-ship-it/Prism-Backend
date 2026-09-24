# Git Workflow

> 목적: 브랜치, 커밋, 병합, 충돌 해결 흐름을 안전하게 정리한다.  
> 사용 위치: `GENERAL_HARNESS` 공통 스킬  
> 출력물: Git 협업 절차

---

## 0. Harness Control Rule

- 이 스킬은 `00.HARNESS_RULES.md`의 하위 모듈이다.
- 충돌 시 이 스킬의 절차를 중단하고 `00.QUICK_REF.md`와 `00.HARNESS_RULES.md §3` 우선순위에 따라 상위 규칙을 따른다. 위험 작업 WARN은 사용자 확인 전 스킬 단독으로 진행하지 않는다.

---

## 1. Trigger

- 기준 브랜치 최신화
- feature 병합
- stash 복구
- 충돌 해결
- 작업 전 현재 변경사항 보호가 필요한 경우

---

## 2. Do Not Trigger

- Git과 무관한 문서 작성
- Git 명령을 실제로 실행하지 않는 개념 설명
- 사용자가 이미 안전한 명령 순서를 확정한 단순 안내

---

## 3. Required Inputs

| 입력물 | 필요 이유 |
|---|---|
| 작업 브랜치 상태 | 현재 위치와 변경사항 확인 |
| 프로젝트 루트 harness.config.json의 Git 설정과 원격 브랜치 증거 | 공식 반영 기준과 실제 관측을 구분 |
| 보존해야 할 변경사항 | 덮어쓰기 방지 |
| 실행할 명령 목적 | 명령 위험도 확인 |

---

## 4. Procedure

이 스킬은 **어떤 Git 전략을 쓸지 결정**하는 것을 담당한다. 명령을 실제로 실행하고 그 증거(stdout/stderr/종료 코드)를 남기는 것은 `skills/terminal-ops/SKILL.md`가 담당한다 — 이 둘을 같은 단계로 중복 수행하지 않는다.

1. 현재 브랜치·변경사항·프로젝트 Git 설정을 확인한다. 설정이 없거나 실제 대상과 충돌하면 공식 반영을 단정하지 않는다. 조사·Git 제외 문서 작업만 있으면 브랜치를 자동 생성하지 않고, 사용자가 요청한 준비용 브랜치는 구현 완료와 구분한다.
2. 보존해야 할 변경사항이 있으면 commit/stash/백업 중 하나를 결정한다.
3. fetch/pull/merge/rebase 중 목적에 맞는 흐름을 선택한다(결정만, 실행은 4번에서 `terminal-ops`로).
4. 결정한 명령을 `skills/terminal-ops/SKILL.md`로 넘겨 실행하고 증거를 받는다.
5. 충돌 발생 시 변경 의도를 보존하며 해결 방향을 결정하고, 실제 명령은 다시 `terminal-ops`로 넘긴다.
6. 빌드/테스트 등 필요한 검증은 `skills/verification-loop/SKILL.md` 또는 `terminal-ops`로 넘긴다.
7. commit, push, PR 생성, 병합의 각 실행 후 실제 결과를 확인하고 `06.REPORT_TEMPLATE.md §5-1`에 따라 현재 작업 기록·최신 포인터·작업 큐를 동기화한다. 미요청 Git 쓰기는 수행하지 않는다.
8. 작업 결과·단계별 상태·남은 충돌을 Report에 기록한다. Git 명령 성공만으로 배포 또는 실제 연동 성공을 기록하지 않는다.

---

## 5. Quality Gate

| 판정 | 기준 |
|---|---|
| PASS | 현재 브랜치, 변경사항 보호 방식, 병합/리베이스 전략, 검증 명령이 명확함 |
| WARN | 명령은 가능하지만 원격 기준, 충돌 영향, stash 복구 계획 중 일부가 불명확함 |
| FAIL | 현재 변경사항을 잃을 수 있거나, 브랜치/원격 기준 확인 없이 병합·리베이스·강제 명령을 진행하려 함 |

---

## 6. Output Format

```md
## Git Workflow 결과

- 사용 이유:
- 확인한 입력물:
- 시작 브랜치 / 대상 브랜치:
- 실행한 명령(fetch/merge/rebase 등):
- 충돌 발생 여부 및 해결 방법:
- 최종 커밋/브랜치 상태:
- 판단 결과:
- PASS/WARN/FAIL:
- 위험 WARN 여부:
- 다음 연결:
```

---

## 7. Handoff

다음 연결: 실제 명령 실행은 위 Procedure의 명령 실행·충돌 해결 단계에서 이미 `skills/terminal-ops/SKILL.md`로 위임해 마쳤다. Handoff은 그 실행 결과 이후 단계다 — 실행 결과가 Gate 대상 산출물에 영향을 줬다면 `skills/terminal-ops/SKILL.md`의 §7을 따라 필요한 Gate로 연결하고, 그렇지 않으면 바로 `06.REPORT_TEMPLATE.md`로.

---

## 8. Anti-Patterns

- 변경사항 확인 없이 pull/rebase 하기
- 충돌 해결 후 검증 없이 완료 처리하기
- force push 같은 위험 명령을 확인 없이 안내하기
- stash 내용을 확인하지 않고 drop 하기
