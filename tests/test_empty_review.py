import copy
import json

import pytest
from test_review_harness import output

from app.domain.review.empty_review import EmptyReviewOutput, validate_empty_review
from app.domain.review.harness import compose_empty_review
from app.domain.review.policy import prepare


def bundle():
    return prepare(
        [
            {"filename": "a.py", "patch": "@@ -1,2 +1,2 @@\n def f(a):\n+    return a[len(a)]"},
            {"filename": "b.py", "patch": "@@ -1 +1 @@\n+value = 1"},
        ],
        [],
        [],
    )


def response():
    return {
        "summary": "검토",
        "issues": [],
        "limitations": "실행 미검증",
        "file_checks": [
            {"file_id": "f1", "line": 2, "outcome": "NO_FINDING", "observation": "인덱스 검사"},
            {"file_id": "f2", "line": 1, "outcome": "LIMITED", "observation": "상수 선언만 제공됨"},
        ],
    }


def test_recheck_can_recover_an_item_without_labeling_it_verifier_checked():
    data = response()
    data["issues"] = output([2])["issues"]
    data["file_checks"][0]["outcome"] = "FINDING"
    result = validate_empty_review(json.dumps(data), bundle())
    assert len(result["issues"]) == 1
    assert result["verification"]["status"] == "EMPTY_RECHECKED"
    assert result["verification"]["file_checks"][0]["file_path"] == "a.py"


def test_legitimate_empty_result_remains_empty_with_visible_scope():
    result = validate_empty_review(json.dumps(response()), bundle())
    assert not result["issues"] and not result["questions"]
    assert len(result["verification"]["file_checks"]) == 2
    system = compose_empty_review(bundle().payload, EmptyReviewOutput.model_json_schema())
    assert "EVERY" in system and "file_checks" in system and "untrusted" in system
    assert "return a[len(a)]" not in system


def test_removal_only_context_is_a_visible_limit_not_an_impossible_check():
    context = prepare(
        [{"filename": "a.py", "patch": "@@ -1,2 +1 @@\n value = 1\n-old = 2"}], [], []
    )
    data = response()
    data["file_checks"] = [
        {
            "file_id": "f1",
            "line": 1,
            "outcome": "LIMITED",
            "observation": "삭제된 코드는 제공되지 않았습니다.",
        }
    ]
    assert (
        validate_empty_review(json.dumps(data), context)["verification"]["status"]
        == "EMPTY_RECHECKED"
    )
    data["file_checks"][0]["outcome"] = "NO_FINDING"
    with pytest.raises(ValueError, match="REMOVAL_ONLY_CONTEXT"):
        validate_empty_review(json.dumps(data), context)


@pytest.mark.parametrize(
    "mode",
    [
        "missing",
        "duplicate",
        "unknown",
        "wrong_line",
        "context_line",
        "blank",
        "secret",
        "contradiction",
        "bad_item",
    ],
)
def test_empty_recheck_cannot_complete_with_missing_or_invalid_evidence(mode):
    data = copy.deepcopy(response())
    checks = data["file_checks"]
    if mode == "missing":
        checks.pop()
    elif mode == "duplicate":
        checks[1] = checks[0]
    elif mode == "unknown":
        checks[0]["file_id"] = "c1"
    elif mode == "wrong_line":
        checks[0]["line"] = 999
    elif mode == "context_line":
        checks[0]["line"] = 1
    elif mode == "blank":
        checks[0]["observation"] = "  "
    elif mode == "secret":
        checks[0]["observation"] = "password='private_value'"
    elif mode == "contradiction":
        checks[0]["outcome"] = "FINDING"
    else:
        data["issues"] = output([999])["issues"]
        checks[0]["outcome"] = "FINDING"
    with pytest.raises(ValueError):
        validate_empty_review(json.dumps(data), bundle())
