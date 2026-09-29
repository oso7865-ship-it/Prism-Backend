import json

import pytest
from test_review_harness import output

from app.domain.review.empty_review import EmptyReviewOutput
from app.domain.review.harness import compose, compose_empty_review, compose_verification
from app.domain.review.output_schema import ReviewOutput
from app.domain.review.path_observations import Projection, Unsupported, path_facts
from app.domain.review.policy import prepare, validate_result
from app.domain.review.verification import verification_payload


def source_bundle(source, path="sample.py"):
    return prepare(
        [
            {
                "filename": path,
                "patch": f"@@ -0,0 +1,{len(source.splitlines())} @@\n"
                + "\n".join("+" + line for line in source.splitlines()),
            }
        ],
        [],
        [],
    )


def test_projection_uses_supplied_default_and_actual_helper_branch():
    source = (
        "def merge(value, fallback):\n"
        "    if fallback is None:\n        return value\n"
        "    if value is None:\n        return fallback\n"
        "    return value\n"
        "def resolve(env, value=True, fallback=True):\n"
        "    value = env.get('PRIMARY') or env.get('SECONDARY')\n"
        "    return merge(value, fallback)\n"
        "def test_resolve():\n"
        "    assert resolve({'SECONDARY': ''}) is True\n"
        "    assert resolve({}) is True\n"
    )
    facts = path_facts(source_bundle(source).payload)[0]
    first, second = facts["observations"]
    assert first["value"] == "" and first["asserted_value"] is True
    assert [b["condition"] for b in first["branches"]] == [False, False]
    assert second["value"] is True


@pytest.mark.parametrize(
    "body",
    [
        "return open('file')",
        "return __import__('os')",
        "while True: pass",
        "return helper(x)",
        "return x.run()",
    ],
)
def test_projection_rejects_effects_unknown_calls_and_recursion(body):
    import ast

    tree = ast.parse("def helper(x):\n    " + body)
    with pytest.raises((Unsupported, ValueError)):
        Projection({"helper": tree.body[0]}).call("helper", [1], {}, 1)


def test_java_projection_distinguishes_operand_cast_from_return_widening():
    for cast, expected, width in [("", 1410065408, 32), ("(long) ", 10000000000, 64)]:
        source = f"class Price {{\nlong total(int x, int y) {{\nreturn {cast}x * y;\n}}\n}}"
        values = path_facts(source_bundle(source, "Price.java").payload)[0]["observations"]
        assert values[-1]["returned_long"] == expected
        assert values[-1]["operation_bits"] == width
    guarded = "class Price { long total(int x, int y) { if (x == 0) return 0; return x * y; } }"
    assert path_facts(source_bundle(guarded, "Price.java").payload) == []


def example():
    bundle = prepare(
        [
            {
                "filename": "indices.py",
                "patch": "@@ -0,0 +1,2 @@\n+def indices(n):\n+    return list(range(0,n,n))",
            }
        ],
        [],
        [],
    )
    draft = output([2])
    draft["issues"][0]["suggestion"] = "n=0은 별도 처리하고 양수에서는 range(n)을 사용하세요."
    return bundle, draft


def test_counterexample_reaches_verifier_without_source_or_draft_loss():
    bundle, draft = example()
    data = json.loads(verification_payload(bundle.payload, json.dumps(draft)))
    assert data["context"] == json.loads(bundle.payload)
    assert data["draft"] == draft
    check = data["review_checks"][0]
    assert check["index"] == 0
    assert check["suggestion_check"]["status"] == "CHANGES_SUCCESSFUL_SAMPLES"
    assert any(c["inputs"] == {"n": 3} for c in check["suggestion_check"]["counterexamples"])


def test_disproved_recommendation_is_withheld_but_finding_and_counterexample_survive():
    bundle, draft = example()
    result = validate_result(json.dumps(draft), bundle)
    finding = result["issues"][0]
    assert "range(n)" not in finding["suggestion"]
    assert finding["suggestion_check"]["withheld"] is True
    assert finding["evidence"] == draft["issues"][0]["evidence"]
    assert finding["suggestion_check"]["counterexamples"]
    assert len(result["issues"]) == 1 and result["questions"] == []


def test_known_conditions_are_not_silently_removed_from_invalid_output():
    bundle, draft = example()
    draft["issues"][0]["assumptions"] = ["n은 계약에 명시된 정수입니다."]
    with pytest.raises(ValueError, match="INCONSISTENT_EVIDENCE_BASIS"):
        validate_result(json.dumps(draft), bundle)


def test_invented_contract_quote_is_rejected_and_source_quote_is_not_stored():
    bundle, draft = example()
    draft["issues"][0]["contract_quote"] = "Invented requirement"
    with pytest.raises(ValueError, match="INVALID_CONTRACT_QUOTE"):
        validate_result(json.dumps(draft), bundle)
    draft["issues"][0]["contract_quote"] = "def indices(n):"
    assert "contract_quote" not in validate_result(json.dumps(draft), bundle)["issues"][0]


@pytest.mark.parametrize("fixed", [False, True])
def test_assertion_grounding_preserves_a_difference_after_an_empty_model_result(fixed):
    from app.domain.review.grounded_claims import ground_assertions
    from scripts.quality_lab_bridge import legacy_bundle, old_cases

    name = "ca-after" if fixed else "ca-before"
    bundle = legacy_bundle(next(c for c in old_cases() if c["legacy_id"] == name))
    raw = {"summary": "검토", "issues": [], "limitations": "범위"}
    result = ground_assertions(validate_result(json.dumps(raw), bundle), bundle)
    assert len(result["issues"]) == (0 if fixed else 1)
    if not fixed:
        issue = result["issues"][0]
        assert issue["line"] == 10 and issue["origin"] == "STATIC_PROJECTION"
        assert "빈 문자열" in issue["consequence"] and "True" in issue["consequence"]
        assert "2줄 조건 거짓" in issue["evidence"] and "4줄 조건 거짓" in issue["evidence"]
        assert "구체적 수정 코드는 아직 검증하지 않았어요" in issue["suggestion"]
        assert "CURL_CA_BUNDLE" not in json.dumps(issue)


def test_schema_expresses_basis_constraints_in_all_output_paths_and_fits_budget():
    schema = ReviewOutput.model_json_schema()
    assert schema["$defs"]["Issue"]["allOf"]
    for purpose in ["CODE", "SECURITY", "STANDARDS"]:
        payload = json.dumps(
            {
                "purpose": purpose,
                "files": [{"language": language} for language in ["java", "py", "js", "ts"]],
            }
        )
        for system in [
            compose(payload, schema)[0],
            compose_empty_review(payload, EmptyReviewOutput.model_json_schema()),
            compose_verification(json.dumps({"context": json.loads(payload), "draft": {}})),
        ]:
            assert '"allOf"' in system and len(system.encode()) <= 24576
