# 작업 리포트: harness-deployment-model-decision

> Superseded note:
> 이 보고서의 다음 작업 판단은 `reports/_LATEST.md`가 가리키는 최신 Report로 대체되었다.
> 과거 의사결정 근거로는 유효하지만, 현재 Next Work 판단은 최신 Report와 `05.WORKING_CONTEXT.md`를 우선한다.

> 작성일: 2026-07-12
> 작업 범위: M (배포 모델 문서화, ADR/D-log 기록)
> 적용 스킬: 해당 없음(정책 문서화)
> 적용 Gate: Document Gate
> 위험 작업 여부: 예 (구조적 결정 문서화. 사용자가 "각 프로젝트에 부착하고 그건 거기서만 쓰는거고 다른 프로젝트에서는 원본 템플릿을 다시넣어서 사용"으로 명시적 확인함)

이 Report에는 "게시 상태" 필드를 두지 않는다(D-028) — 게시 여부는 `reports/_LATEST.md`와 archive 위치로 판단한다.

---

## 0. 작업 범위 확인

| 항목 | 내용 |
|---|---|
| 요청 요약 | §12에 남아있던 결정 사항 2건 중 1건("GENERAL_HARNESS.zip을 프로젝트 인스턴스와 공유할지")을 사용자와 논의해 "템플릿 복제 모델"로 확정하고 문서화 |
| 수정 대상 | `09.AGENT_WORKFLOW.md §7-2`(배포 모델 명시), `06.REPORT_TEMPLATE.md §8-2`(배포 모델 참조 추가), `10.ADR.md`(ADR-030), `_WORKING_CONTEXT_HISTORY.md`(D-029) |
| 제외 대상 | archive Report 16개의 옛 경로 처리(§12 나머지 1건)는 이번에도 다루지 않음 — 별도 결정 필요 |
| 검증 방법 | 게시 전 6개 스크립트 실행 |
| 한계 | 이 결정은 아직 실제 프로젝트 부착 사례 없이 내려진 것이라, 실제로 부착해보면 세부 절차(복제 방법, 이름 규칙 등)를 더 다듬어야 할 수 있다 |

---

## 1. 결정 내용

**배포 모델: 템플릿 복제.** `GENERAL_HARNESS.zip`은 원본 템플릿 전용 이름으로 유지한다. 각 프로젝트는 부착 시점에 이 템플릿을 각자 복제해서 그 프로젝트만의 사본으로 관리하며, 하네스 자체 개선사항은 이미 부착된 프로젝트 사본에 자동 반영되지 않는다(그때그때 수동 판단). 다른 프로젝트를 새로 시작할 때는 항상 원본 템플릿에서 새로 복제한다.

이 방식은 cookiecutter류 스캐폴딩 도구, `.cursorrules`/`AGENTS.md`류 AI 코딩 규칙 파일의 배포 방식과 동일하며, `05.WORKING_CONTEXT.md`를 프로젝트 전용 템플릿으로 전환한 이전 결정(ADR-027)과도 자연스럽게 맞아떨어진다.

---

## 2. 수정 내역

- `09.AGENT_WORKFLOW.md §7-2`에 "배포 모델: 템플릿 복제" 절을 신설하고, 4가지 구체 규칙(zip 이름은 템플릿 전용, 부착 시 사본 전환, 자동 동기화 없음, 새 프로젝트는 원본에서 복제)을 명시했다.
- `06.REPORT_TEMPLATE.md §8-2`가 이 배포 모델을 참조하도록 한 줄 추가했다(중복 정의 방지).
- `10.ADR.md`에 ADR-030을 추가해 결정 배경·이유·결과를 기록했다.
- `_WORKING_CONTEXT_HISTORY.md`에 D-029를 이어서 추가했다.

---

## 3. 게시 전 검증 (6개, validate-package 제외)

```txt
PASS validate-harness
PASS validate-docs (71 markdown files checked)
PASS validate-skills (12 skills checked)
PASS validate-no-personal-paths
PASS validate-references (path + section references resolve)
PASS validate-report-consistency (archive digest complete, no orphan rows)
```

전부 PASS이므로 게시를 진행한다.

---

## 4. 남은 §12 결정 사항

- **archive Report 16개의 옛 literal 경로**: 역사적 원문으로 그대로 둘지, 경로만 기계적으로 보정할지 — 아직 미결.

---

## 5. 다음 작업

§12 마지막 1건(archive 경로 처리) 결정 대기. 그 외에는 다섯 번째 검수까지의 모든 지적사항이 처리 완료된 상태.
