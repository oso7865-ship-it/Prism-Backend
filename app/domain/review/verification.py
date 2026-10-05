"""A second fallible reviewer with bounded independent missed-defect recovery."""

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.review.empty_schema import FileCheck
from app.domain.review.model_output import strip_api_metadata
from app.domain.review.output_schema import Issue, ReviewOutput


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
    revised: Issue | None
    checked_consequence: str | None = Field(min_length=1, max_length=400)


class VerificationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    decisions: list[Decision] = Field(max_length=10)
    new_findings: list[Issue] = Field(default_factory=list, max_length=10)
    file_checks: list[FileCheck] = Field(default_factory=list, max_length=8)


def verification_payload(payload: str, raw: str) -> str:
    # Called only after the draft passes validate_result. Payload has no repository paths.
    from app.domain.review.semantics import suggestion_check

    raw = strip_api_metadata(raw)
    context, draft = json.loads(payload), json.loads(raw)
    files = {f["file_id"]: f for f in context["files"]}
    checks = []
    for index, issue in enumerate(ReviewOutput.model_validate_json(raw).issues):
        check = suggestion_check(issue, files[issue.file_id])
        if check["status"] == "CHANGES_SUCCESSFUL_SAMPLES":
            checks.append({"index": index, "suggestion_check": check})
    value = {"context": context, "draft": draft}
    # Diagnostics share the existing 24KB draft allowance, never displace code/premises.
    if (
        checks
        and len(json.dumps({"draft": draft, "review_checks": checks}, ensure_ascii=False).encode())
        <= 24000
    ):
        value["review_checks"] = checks
    return json.dumps(value, ensure_ascii=False)


def apply_verification(raw: str, draft: str) -> tuple[str, dict[str, object]]:
    from app.domain.review.policy import SECRET

    if len(raw.encode()) > 24000 or SECRET.search(raw):
        raise ValueError("INVALID_VERIFICATION")
    output = VerificationOutput.model_validate_json(strip_api_metadata(raw))
    decisions = output.decisions
    original = ReviewOutput.model_validate_json(strip_api_metadata(draft))
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
            revised = d.revised
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
    added = 0
    for issue in output.new_findings:
        # Exact causal duplicate only: similar locations alone must not erase distinct bugs.
        identity = (issue.file_id, issue.line, issue.trigger.strip(), issue.consequence.strip())
        if any(
            identity == (i.file_id, i.line, i.trigger.strip(), i.consequence.strip())
            for i in accepted
        ):
            continue
        accepted.append(issue)
        added += 1
    if len(accepted) > 10:
        raise ValueError("TOO_MANY_VERIFIED_FINDINGS")
    original.issues = accepted
    original.context_requests = []
    # Free draft limitations can repeat rejected claims; retain a server-owned scope notice.
    original.limitations = (
        "제공된 변경·관련 코드 범위에서 AI가 근거를 다시 검토했어요. "
        "전체 호출 경로와 실행 결과는 확인하지 않았으며 잘못된 판단이나 누락이 있을 수 있어요."
    )
    meta: dict[str, object] = {"status": "CHECKED", **counts}
    if output.new_findings or output.file_checks:
        meta["added"] = added
        meta["file_checks"] = [c.model_dump() for c in output.file_checks]
    return original.model_dump_json(), meta
