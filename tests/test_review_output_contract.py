"""Executable prompt examples and strict rejection checks, not semantic model evaluations."""

import copy
import json
import re
from itertools import combinations
from pathlib import Path

import pytest

from app.domain.review import harness
from app.domain.review.policy import ReviewOutput, prepare, validate_result


def examples():
    return [
        json.loads(block)
        for block in re.findall(
            r"```json\n(.*?)\n```",
            Path("evals/recall-repair/output-contract-examples.prompt").read_text(encoding="utf-8"),
            re.DOTALL,
        )
    ]


INPUTS = [
    ("last.py", "@@ -0,0 +1,2 @@\n+def last(values):\n+    return values[len(values)]"),
    (
        "render.js",
        "@@ -0,0 +1,3 @@\n+function render(panel, message) {\n+  panel.innerHTML = message;\n+}",
    ),
    ("Store.java", "@@ -0,0 +1,3 @@\n+interface Store {\n+  void reserve(long id);\n+}"),
    (
        "average.py",
        "@@ -0,0 +1,4 @@\n+from counts import count\n+\n+def average(n):\n"
        "+    return 10 / count(n)",
    ),
    (
        "caption.py",
        "@@ -0,0 +1,3 @@\n+from catalog import caption\n+def label(key):\n"
        "+    return caption(key).strip()",
    ),
    ("Text.java", "@@ -0,0 +1,3 @@\n+int length(String text) {\n+  return text.length();\n+}"),
]


@pytest.mark.parametrize(
    "index,counts",
    [
        (0, (1, 0)),
        (1, (0, 1)),
        (2, (0, 0)),
        (3, (1, 0)),
        (4, (0, 0)),
        (5, (0, 0)),
    ],
)
def test_reference_examples_follow_contract_and_preserve_questions(index, counts):
    outputs = examples()
    assert len(outputs) == len(INPUTS)
    raw = outputs[index]
    path, patch = INPUTS[index]
    bundle = prepare([{"filename": path, "patch": patch}], [], [])
    result = validate_result(json.dumps(raw), bundle)
    assert set(raw) == {"summary", "issues", "limitations"}
    assert (len(result["issues"]), len(result["questions"])) == counts
    assert result["summary"] != raw["summary"]
    if raw["issues"]:
        assert raw["issues"][0]["title"] in result["summary"]
    else:
        assert "제공된 코드 범위" in result["summary"]
    assert result["limitations"] == raw["limitations"]
    for item in result["issues"] + result["questions"]:
        assert item["file_path"] == path
        assert item["basis"] == raw["issues"][0]["basis"]


@pytest.mark.parametrize(
    "mutation",
    [
        "display_shape",
        "missing_assumptions",
        "string_line",
        "list_limitations",
        "unknown_file",
        "unprovided_evidence",
        "invented_field",
        "unsupported_certainty",
        "context_without_premise",
        "context_error",
    ],
)
def test_malformed_examples_are_rejected_instead_of_coerced_or_silently_dropped(mutation):
    path, patch = INPUTS[0]
    bundle = prepare([{"filename": path, "patch": patch}], [], [])
    raw = copy.deepcopy(examples()[0])
    item = raw["issues"][0]
    if mutation == "display_shape":
        raw["questions"] = raw.pop("issues")
    elif mutation == "missing_assumptions":
        del item["assumptions"]
    elif mutation == "string_line":
        item["line"] = "2"
    elif mutation == "list_limitations":
        raw["limitations"] = [raw["limitations"]]
    elif mutation == "unknown_file":
        item["file_id"] = "f99"
    elif mutation == "unprovided_evidence":
        item["evidence_lines"] = [2, 99]
    elif mutation == "invented_field":
        item["confidence"] = 1
    elif mutation == "unsupported_certainty":
        item["assumptions"] = ["미확인 전제"]
    elif mutation == "context_without_premise":
        item["basis"] = "NEEDS_CONTEXT"
    elif mutation == "context_error":
        item.update(basis="NEEDS_CONTEXT", severity="ERROR", assumptions=["미확인 전제"])
    with pytest.raises(ValueError):
        validate_result(json.dumps(raw), bundle)


def test_examples_fit_system_budget_for_every_language_combination():
    languages = ("java", "py", "js", "ts")
    for size in range(5):
        for selected in combinations(languages, size):
            payload = json.dumps({"files": [{"language": lang} for lang in selected]})
            system, _ = harness.compose(payload, ReviewOutput.model_json_schema())
            assert len(system.encode()) <= harness.MAX_SYSTEM_BYTES
            assert harness.documents()["output"] in system


def test_related_file_proof_does_not_make_cross_file_numeric_anchors_valid():
    path, patch = INPUTS[3]
    bundle = prepare([{"filename": path, "patch": patch}], [], [])
    payload = json.loads(bundle.payload)
    payload["files"].append(
        {
            "file_id": "c2",
            "role": "related",
            "language": "py",
            "lines": [
                {"line": 101, "code": "def count(n):", "changed": False},
                {"line": 102, "code": "    return 0 if n == 0 else 1", "changed": False},
            ],
        }
    )
    bundle.payload = json.dumps(payload)
    bundle.anchors["c2"] = ("counts.py", {101, 102})
    output = examples()[3]
    assert len(validate_result(json.dumps(output), bundle)["issues"]) == 1
    output["issues"][0]["evidence_lines"] = [4, 102]
    with pytest.raises(ValueError, match="INVALID_EVIDENCE_LINES"):
        validate_result(json.dumps(output), bundle)


def test_runtime_format_example_validates_against_the_unchanged_output_schema():
    blocks = re.findall(r"```json\n(.*?)\n```", harness.documents()["output"], re.DOTALL)
    # One conditional, one empty and one supported runtime format example remain.
    inputs = [INPUTS[i] for i in (1, 2, 3)]
    assert len(blocks) == len(inputs)
    for block, (path, patch) in zip(blocks, inputs, strict=True):
        validate_result(block, prepare([{"filename": path, "patch": patch}], [], []))
