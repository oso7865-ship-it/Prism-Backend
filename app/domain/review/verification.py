"""A second fallible reviewer; strict decisions, no invented findings or silent fallback."""

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    index: int = Field(ge=0, le=9)
    action: Literal["KEEP", "REVISE", "DROP"]
    reason: Literal[
        "CONFIRMED",
        "WRONG_CONSEQUENCE",
        "GUARDED_PATH",
        "MISSING_CONTRACT",
        "DUPLICATE",
        "UNSUPPORTED",
        "OVERSTATED",
    ]
    revised: dict[str, object] | None
    checked_consequence: str | None = Field(min_length=1, max_length=400)


class VerificationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    decisions: list[Decision] = Field(max_length=10)


def verification_payload(payload: str, raw: str) -> str:
    # Called only after the draft passes validate_result. Payload has no repository paths.
    return json.dumps(
        {"context": json.loads(payload), "draft": json.loads(raw)}, ensure_ascii=False
    )


def apply_verification(raw: str, draft: str) -> tuple[str, dict[str, object]]:
    from app.domain.review.policy import SECRET, Issue, ReviewOutput

    if len(raw.encode()) > 24000 or SECRET.search(raw):
        raise ValueError("INVALID_VERIFICATION")
    decisions = VerificationOutput.model_validate_json(raw).decisions
    original = ReviewOutput.model_validate_json(draft)
    if len(decisions) != len(original.issues) or {d.index for d in decisions} != set(
        range(len(original.issues))
    ):
        raise ValueError("INCOMPLETE_VERIFICATION")
    accepted: list[Issue] = []
    counts = {"kept": 0, "revised": 0, "dropped": 0}
    for d in sorted(decisions, key=lambda d: d.index):
        issue = original.issues[d.index]
        if d.action == "REVISE":
            if d.revised is None:
                raise ValueError("MISSING_REVISION")
            revised = Issue.model_validate(d.revised)
            if (revised.file_id, revised.line) != (issue.file_id, issue.line):
                raise ValueError("VERIFICATION_MOVED_FINDING")
            # A verifier may narrow a finding; it must not promote an uncertain concern.
            if issue.basis == "NEEDS_CONTEXT" and revised.basis != "NEEDS_CONTEXT":
                raise ValueError("VERIFICATION_PROMOTED_FINDING")
            if not d.checked_consequence or not d.checked_consequence.strip():
                raise ValueError("MISSING_CHECKED_CONSEQUENCE")
            revised.consequence = d.checked_consequence
            accepted.append(revised)
            counts["revised"] += 1
        else:
            if d.revised is not None or (d.action == "KEEP") != (d.reason == "CONFIRMED"):
                raise ValueError("INCONSISTENT_VERIFICATION")
            if d.action == "KEEP":
                if not d.checked_consequence or not d.checked_consequence.strip():
                    raise ValueError("MISSING_CHECKED_CONSEQUENCE")
                changed = issue.consequence != d.checked_consequence
                issue.consequence = d.checked_consequence
                accepted.append(issue)
                counts["revised" if changed else "kept"] += 1
            else:
                if d.checked_consequence is not None:
                    raise ValueError("INCONSISTENT_VERIFICATION")
                counts["dropped"] += 1
    original.issues = accepted
    # Free draft limitations can repeat rejected claims; retain a server-owned scope notice.
    original.limitations = (
        "제공된 변경·관련 코드 범위에서 AI가 근거를 다시 검토했어요. "
        "전체 호출 경로와 실행 결과는 확인하지 않았으며 잘못된 판단이나 누락이 있을 수 있어요."
    )
    return original.model_dump_json(), {"status": "CHECKED", **counts}
