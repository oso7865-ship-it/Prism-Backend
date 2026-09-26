"""Offline scoring only. Passing structural checks is not a semantic quality guarantee."""

import json
from typing import Any

from app.domain.review.policy import prepare, validate_result


def score(case: dict[str, Any], response: dict[str, Any]) -> dict[str, object]:
    bundle = prepare([{"filename": case["path"], "patch": case["patch"]}], [], [], 1)
    try:
        result = validate_result(json.dumps(response), bundle)
    except ValueError:
        return {"id": case["id"], "valid": False, "passed": False}
    issues = result["issues"]
    assert isinstance(issues, list)
    expected = set(case["expected_lines"])
    supported = {i["line"] for i in issues if i["basis"] == "SUPPORTED"}
    missed = len(expected - supported)
    unexpected = sum(i["line"] not in expected for i in issues)
    return {
        "id": case["id"],
        "valid": True,
        "missed": missed,
        "unexpected": unexpected,
        "passed": missed == 0 and unexpected == 0,
    }
