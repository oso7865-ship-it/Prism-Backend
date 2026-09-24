# AGENTS.md

> 목적: 이 저장소에서 작업하는 AI 에이전트를 위한 짧은 진입 지도다. 세부 규칙의 Source of Truth는 `GENERAL_HARNESS/`다.

## 읽기 표면 (2층 모델)

기본은 **1층(상시 표면)만 읽는다**: 이 문서 + `GENERAL_HARNESS/00.QUICK_REF.md` + (수정 작업 시) `GENERAL_HARNESS/04.GATEGUARD.md` §6-1 + 발동 스킬 1~2개. 나머지 문서는 트리거가 발생했을 때만 읽는다 — 트리거 목록과 소유 규칙은 `GENERAL_HARNESS/03.CONTEXT_BUDGET.md` §2-2-1이 소유한다. 문서를 많이 읽는 것이 준수가 아니라, 발동 조건에 맞는 문서를 정확히 읽는 것이 준수다.

## 시작 순서

프로젝트 루트에 PROJECT_HARNESS가 있으면 작업 시작 시 해당 context와 작업별 문서 경로를 확인한다. 연결·버전·출처 계약은 [Project Adapter](GENERAL_HARNESS/PROJECT_ADAPTER.md)를 따른다. 어댑터가 없으면 기존 시작 순서를 유지한다.

1. 실제 파일 상태와 사용자의 최신 요청을 확인한다.
2. 작업 규모를 S/M/L/XL로 판단한다. M 이상 또는 이전 작업을 잇는 경우 `GENERAL_HARNESS/00.QUICK_REF.md`, `reports/_LATEST.md`, `GENERAL_HARNESS/05.WORKING_CONTEXT.md`를 확인한다.
3. 작업 계약에 목표, 수정/제외 대상, 근거, 적용 Skill/Gate, 위험도, 검증 방법을 적는다. Context Pack이 필요하면 이 작업 계약 안에만 넣고 별도 상시 파일을 만들지 않는다.
4. `GENERAL_HARNESS/04.GATEGUARD.md`로 위험도를 판정한 뒤 관련 Skill, Gate, Checklist를 적용한다.

## 우선순위와 안전

충돌 시 `GENERAL_HARNESS/00.HARNESS_RULES.md §3`을 따른다. 안전·보안·데이터 손상·파일 삭제 방지 규칙, 사용자의 최신 명시 요청, 하네스, 작업 계약/GateGuard 순으로 판단한다.

- 요청을 해결하는 최소 변경만 한다. 기존 사용자 변경과 무관한 정리·리팩터링·삭제는 하지 않는다.
- 삭제, 대량 이동, 덮어쓰기, 외부 설치/스크립트 실행은 현재 사용자의 확인 없이는 진행하지 않는다.
- FAIL은 수정 후 같은 검증을 다시 통과해야 한다. 구조·위험 WARN은 근거나 사용자 확인 전 진행하지 않는다.
- UI/UX 구현 작업일 때만 `skills/ui-ux-design/SKILL.md`와 관련 Gate·Checklist를 읽는다. Vue 3 프로젝트의 UI 다듬기·모션 작업이면 `skills/vue-ui-polish/SKILL.md`(스택 한정 — 다른 스택에서는 존재 무시)도 함께 읽는다. 일반 문서·백엔드 작업에 디자인 규칙을 불필요하게 적용하지 않는다.

## Git과 기록

- Git은 변경 이력의 기준이다. 작업 브랜치 push는 공유 진행 상태이며, 공식 반영은 프로젝트 루트 harness.config.json의 명시된 기준 브랜치 병합으로 판단한다. 이 저장소는 origin/main이다. 배포·실제 연동 확인은 별도 증거가 필요하다. 설정이 없으면 기준 브랜치를 추측하지 않는다.
- 커밋, push, 브랜치 생성, PR 생성은 사용자가 명시적으로 요청한 범위에서만 한다.
- 여러 파일 수정, Gate 적용, 자동 검증, WARN/FAIL, 중단·재개가 있으면 `GENERAL_HARNESS/06.REPORT_TEMPLATE.md`에 따라 Report 필요 여부를 판단한다. L/XL 작업은 Working Context도 갱신한다. 중단 시 Handoff Note를 남긴다.
- `CLAUDE.md`와 이 `AGENTS.md`는 사람과 에이전트의 진입 안내 문서다. 자동 검증 범위에는 넣지 않으며, 내용 품질은 변경 시 수동 검수한다.

## 추가 읽기

- 하네스 자체를 바꾸면: `00.HARNESS_RULES.md`, `03.CONTEXT_BUDGET.md`, `04.GATEGUARD.md`, `08.QUALITY_GATE.md`, `09.AGENT_WORKFLOW.md`, 관련 ADR을 먼저 읽는다.
- 명령 실행은 `GENERAL_HARNESS/skills/terminal-ops/SKILL.md`, Git 작업은 `GENERAL_HARNESS/skills/git-workflow/SKILL.md`를 따른다.

## PRism 저장소 진입

PROJECT_HARNESS/00.PROJECT_CONTEXT.md와 README.md에서 현재 구현 범위와 실행 명령을 확인한다. 제품 아키텍처의 기준 커밋은 architecture.json이다. GENERAL_HARNESS의 과거 유지보수 Report를 제품 진행 상태로 간주하지 않는다.
