# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

> 언어 안내: §1~§4는 외부 원문(영어)을 그대로 반입한 것이라 영어로 유지하고, 하단 "Project Harness" 섹션은 이 저장소의 운영 언어(한국어)로 작성한다. 의도된 혼용이다.

Repository entry policy: `AGENTS.md` is the standard agent instruction file. This `CLAUDE.md` is Claude-specific supplemental guidance; neither entry document is included in automated harness validation, so a change to either requires manual review against `GENERAL_HARNESS/00.HARNESS_RULES.md`.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

---

## Project Harness

이 프로젝트는 `GENERAL_HARNESS/`에 별도의 작업 거버넌스 규칙(Skill, Gate, Report, 위험 작업 처리 등)을 두고 있다. 위 4가지 원칙은 이 하네스와 충돌하지 않는다 — 서로 다른 층을 다룬다(이 문서: 코드를 어떻게 잘 짤지 / 하네스: 여러 세션에 걸친 프로젝트를 어떻게 안전하게 관리할지).

작업 규모에 따라 아래를 확인한다:

- **간단한 질문, 오타 수정, 단순 설명**: 이 파일(CLAUDE.md)만으로 충분하다. 하네스를 추가로 읽지 않는다.
- **여러 파일에 걸친 구현, 구조 변경, DB/보안/결제/인증 관련 작업**: 먼저 `GENERAL_HARNESS/00.QUICK_REF.md`를 확인한다.
- **새 스킬을 만들거나 하네스 자체를 고치는 작업**: `GENERAL_HARNESS/00.HARNESS_RULES.md`부터 확인한다.

충돌 시 우선순위는 `GENERAL_HARNESS/00.HARNESS_RULES.md §3`이 유일한 기준(SoT)이며, 이 문서는 그 순서를 다시 정의하지 않고 그대로 참조한다:

```text
1. 안전/보안/데이터 손상/파일 삭제 방지 규칙
2. 사용자의 최신 명시 요청
3. GENERAL_HARNESS/00.HARNESS_RULES.md
4. 현재 작업 계약과 04.GATEGUARD.md 결과
5. 관련 Gate와 Checklist
6. 관련 skills/*/SKILL.md
7. 05.WORKING_CONTEXT.md, 이전 Report, 오래된 결정
```

**이 문서(CLAUDE.md)의 4가지 코딩 원칙은 위 순서 중 어디에도 새로운 층을 추가하지 않는다.** 이 원칙들은 하네스가 이미 요구하는 검증·예외 처리·Gate 판정을 대체하거나 낮추는 근거로 쓰이지 않는다 — 예를 들어 "Simplicity First"를 이유로 Gate가 요구하는 예외 처리를 생략하거나, "Surgical Changes"를 이유로 구조 WARN 해제에 필요한 연동 문서 수정을 거부하지 않는다. 이 문서의 원칙은 어디까지나 3~6번 층위 **안에서** 코드를 어떻게 잘 짤지에 대한 지침일 뿐이다.
