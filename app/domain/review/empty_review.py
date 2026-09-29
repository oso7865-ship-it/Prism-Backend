import json

from pydantic import Field

from app.domain.review.empty_schema import FileCheck
from app.domain.review.grounded_claims import ground_assertions
from app.domain.review.policy import SECRET, InputBundle, ReviewOutput, validate_result


class EmptyReviewOutput(ReviewOutput):
    file_checks: list[FileCheck] = Field(min_length=1, max_length=8)


def validate_empty_review(raw: str, bundle: InputBundle) -> dict[str, object]:
    if len(raw.encode()) > 24000 or SECRET.search(raw):
        raise ValueError("INVALID_OUTPUT")
    output = EmptyReviewOutput.model_validate_json(raw)
    result = validate_result(output.model_dump_json(exclude={"file_checks"}), bundle)
    result["verification"] = {
        "status": "EMPTY_RECHECKED",
        "file_checks": validate_file_checks(output.file_checks, output, bundle),
    }
    return ground_assertions(result, bundle)


def validate_file_checks(
    checks: list[FileCheck],
    output: ReviewOutput,
    bundle: InputBundle,
) -> list[dict[str, object]]:
    files = {
        f["file_id"]: f
        for f in json.loads(bundle.payload)["files"]
        if f.get("role", "changed") == "changed"
    }
    ids = [c.file_id for c in checks]
    if len(ids) != len(set(ids)) or set(ids) != set(files):
        raise ValueError("INCOMPLETE_FILE_CHECKS")
    finding_ids = {i.file_id for i in output.issues}
    result: list[dict[str, object]] = []
    for check in checks:
        changed = {n["line"] for n in files[check.file_id]["lines"] if n["changed"]}
        allowed = changed or bundle.anchors[check.file_id][1]
        if (
            not allowed
            or not check.observation.strip()
            or (check.line is not None and check.line not in bundle.anchors[check.file_id][1])
        ):
            raise ValueError("INVALID_FILE_CHECK")
        if not changed and check.outcome != "LIMITED":
            raise ValueError("REMOVAL_ONLY_CONTEXT")
        if (check.outcome == "FINDING") != (check.file_id in finding_ids):
            raise ValueError("INCONSISTENT_FILE_CHECK")
        result.append(
            {
                **check.model_dump(),
                "line": min(allowed),
                "file_path": bundle.anchors[check.file_id][0],
            }
        )
    return result
