import asyncio
import json

import httpx
import pytest
from pydantic import SecretStr
from test_review_harness import output
from test_review_verification import decision

from app.domain.review.dependency_evidence import Dependency, from_lockfile, query_osv
from app.domain.review.dictionary_observations import dictionary_facts
from app.domain.review.harness import compose, schema_text
from app.domain.review.output_schema import ContextRequest, ExpressionRepair
from app.domain.review.policy import ReviewOutput, prepare, validate_result
from app.domain.review.refinement import add_observations, independent_result, verified_result
from app.domain.review.security_evidence import scan
from app.domain.review.semantics import interpret, parse, repair_check
from app.domain.review.supplement import supplement
from app.domain.review.verification import verification_payload
from app.shared.config.settings import Settings
from scripts.quality_repair_provider import ConditionalCandidate, ResponsesCandidate


def source_bundle(text):
    lines = text.splitlines()
    return prepare(
        [
            {
                "filename": "a.py",
                "patch": f"@@ -0,0 +1,{len(lines)} @@\n" + "\n".join("+" + line for line in lines),
            }
        ],
        [],
        [],
    )


def test_verifier_can_drop_wrong_cause_and_add_a_different_supported_cause():
    bundle = source_bundle("x=1\ny=2")
    raw = {
        "decisions": [decision("DROP", "WRONG_CONSEQUENCE")],
        "new_findings": output([2])["issues"],
        "file_checks": [{"file_id": "f1", "outcome": "FINDING", "observation": "경계 확인"}],
    }
    result = verified_result(json.dumps(raw), json.dumps(output([1])), bundle)
    assert len(result["issues"]) == 1 and result["issues"][0]["line"] == 2
    assert result["verification"]["added"] == result["verification"]["dropped"] == 1
    assert result["verification"]["file_checks"][0]["line"] == 1
    raw["new_findings"][0]["evidence_lines"] = [999]
    with pytest.raises(ValueError, match="INVALID_EVIDENCE_LINES"):
        verified_result(json.dumps(raw), json.dumps(output([1])), bundle)


def test_incomplete_coverage_does_not_become_a_clean_review():
    with pytest.raises(ValueError, match="INCOMPLETE_FILE_CHECKS"):
        verified_result(
            json.dumps({"decisions": [decision("DROP", "UNSUPPORTED")]}),
            json.dumps(output([1])),
            source_bundle("x=1"),
        )


def test_duplicate_new_findings_are_not_counted_twice():
    draft = output([1])
    data = {
        "decisions": [decision()],
        "new_findings": draft["issues"],
        "file_checks": [{"file_id": "f1", "outcome": "FINDING", "observation": "검토"}],
    }
    result = verified_result(json.dumps(data), json.dumps(draft), source_bundle("x=1"))
    assert len(result["issues"]) == 1 and result["verification"]["added"] == 0


@pytest.mark.parametrize(
    "expression",
    [
        "__import__('os').system('bad')",
        "x.attr",
        "[v for v in x]",
        "range(99999999)",
        "'x'*9999999",
    ],
)
def test_narrow_interpreter_rejects_execution_and_unbounded_operations(expression):
    with pytest.raises(ValueError):
        interpret(parse(expression), {})


def test_actual_empty_value_and_zero_step_semantics():
    assert interpret(parse("None or ''"), {}) == ""
    assert interpret(parse("'' or None"), {}) is None
    with pytest.raises(ValueError):
        interpret(parse("list(range(0,n,n))"), {"n": 0})
    assert interpret(parse("list(range(0,n,n))"), {"n": 3}) == [0]


def test_fix_does_not_hide_successful_behavior_change_or_delete_the_defect():
    file = json.loads(source_bundle("def f(n):\n    return list(range(0,n,n))").payload)["files"][0]
    bad = ExpressionRepair(line=2, before="list(range(0,n,n))", after="list(range(0,n,1))")
    check = repair_check(bad, file)
    assert check["status"] == "CHANGES_SUCCESSFUL_SAMPLES"
    assert any(c["inputs"] == {"n": 3} for c in check["counterexamples"])
    good = bad.model_copy(update={"after": "list(range(0,n,n or 1))"})
    assert repair_check(good, file)["status"] == "PRESERVES_SAMPLES"
    assert repair_check(bad.model_copy(update={"line": 1}), file)["status"] == "SOURCE_MISMATCH"


def test_facts_are_scoped_and_do_not_change_mandatory_source():
    bundle = source_bundle("def f(n):\n    return list(range(0,n,n))")
    original = json.loads(bundle.payload)["files"]
    add_observations(bundle)
    data = json.loads(bundle.payload)
    assert data["files"] == original and data["semantic_observations"]
    assert data["semantic_observations"][0]["scope"] == "EXPRESSION_ONLY_ASSUMING_BUILTINS"


def test_dictionary_expression_uses_actual_operand_order_without_running_calls():
    bundle = source_bundle("value = env.get('PRIMARY') or env.get('SECONDARY')")
    facts = dictionary_facts(bundle.payload)
    assert len(facts) == 1
    assert any(
        p["inputs"] == {"env": {"SECONDARY": ""}} and p["value"] == ""
        for p in facts[0]["observations"]
    )
    add_observations(bundle)
    assert json.loads(bundle.payload)["semantic_observations"] == facts
    assert not dictionary_facts(source_bundle("value = evil().get('A') or env.get('B')").payload)


def test_boolean_and_integer_replacement_are_distinct_values():
    file = json.loads(source_bundle("return x or 0").payload)["files"][0]
    repair = ExpressionRepair(line=1, before="x or 0", after="x or False")
    assert repair_check(repair, file)["status"] == "CHANGES_SUCCESSFUL_SAMPLES"


def test_textual_range_recommendation_gets_a_scoped_counterexample_without_losing_issue():
    bundle = source_bundle("def indices(n):\n    return list(range(0,n,n))")
    draft = output([2])
    draft["issues"][0]["suggestion"] = "n=0은 먼저 처리하고, 나머지는 range(n)을 사용하세요."
    result = validate_result(json.dumps(draft), bundle)
    assert len(result["issues"]) == 1
    check = result["issues"][0]["suggestion_check"]
    assert check["status"] == "CHANGES_SUCCESSFUL_SAMPLES" and check["inferred_from_text"]
    assert any(c["inputs"] == {"n": 3} for c in check["counterexamples"])


def test_schema_compaction_preserves_property_named_title_and_all_language_budgets():
    schema = ReviewOutput.model_json_schema()
    compact = json.loads(schema_text(schema))
    assert "title" in compact["$defs"]["Issue"]["properties"]
    for purpose in ["CODE", "SECURITY", "STANDARDS"]:
        text, _ = compose(
            json.dumps(
                {
                    "purpose": purpose,
                    "files": [{"language": language} for language in ["java", "py", "js", "ts"]],
                }
            ),
            schema,
        )
        assert len(text.encode()) <= 24576


def test_independent_findings_are_preserved_when_ai_cannot_complete():
    bundle = source_bundle("x=1")
    result = independent_result(bundle, [{"file_id": "f1", "line": 1, "rule_id": "test"}])
    assert result["issues"] == [] and result["security_evidence"][0]["file_path"] == "a.py"
    assert "완료하지 못했어요" in result["summary"]
    assert independent_result(bundle, []) is None


def test_context_uses_only_provided_file_ids_symbols_and_exact_sha(monkeypatch):
    calls = []
    bundle = prepare([{"filename": "a.py", "patch": "@@ -1 +1 @@\n+print(helper())"}], [], [])

    async def read(github, token, prefix, sha, path):
        calls.append((prefix, sha, path))
        return ["print(helper())", "def helper():", "    return 1"]

    monkeypatch.setattr("app.domain.review.supplement.source", read)
    requests = [
        ContextRequest(file_id="f1", symbol="helper", need="구현"),
        ContextRequest(file_id="f1", symbol="unseen", need="없는 식별자"),
    ]
    result = asyncio.run(supplement(bundle, requests, None, "token", "/repos/o/r", "a" * 40, []))
    assert calls == [("/repos/o/r", "a" * 40, "a.py")]
    assert result.anchors["f1"][1] == {1, 2, 3}
    assert bundle.anchors["f1"][1] == {1}
    assert result.coverage["context_supplement"][1]["status"] == "SYMBOL_NOT_PROVIDED"
    assert result.coverage["files"][0]["provided_lines"] == 3
    for symbol in ["../private", "https://evil", "a.b", "x();"]:
        with pytest.raises(ValueError):
            ContextRequest(file_id="f1", symbol=symbol, need="invalid")


@pytest.mark.parametrize("safe", [False, True, "guard", "rebind", "shadow"])
def test_independent_shell_evidence_is_narrow_and_handles_visible_barriers(safe):
    text = (
        "from flask import request\nimport subprocess\ndef route():\n"
        "    value = request.args.get('cmd')\n"
    )
    if safe == "guard":
        text += "    validate(value)\n"
    elif safe == "rebind":
        text += "    value = 'constant'\n"
    elif safe == "shadow":
        text = text.replace("route()", "route(subprocess)")
    text += "    subprocess.run(value, shell=" + ("False" if safe is True else "True") + ")"
    result = scan(source_bundle(text).payload)
    assert bool(result) == (safe is False)
    if result:
        assert result[0]["source_line"] == 4


def test_osv_needs_separate_consent_and_sends_only_exact_metadata():
    dependency = Dependency(ecosystem="PyPI", name="example", version="1.2.3")
    seen = []

    def handler(request):
        seen.append(json.loads(request.content))
        assert str(request.url) == "https://api.osv.dev/v1/query"
        return httpx.Response(200, json={"vulns": [{"id": "OSV-1"}], "next_page_token": "next"})

    with pytest.raises(ValueError, match="CONSENT"):
        asyncio.run(query_osv(dependency, approved_metadata_transfer=False))
    result = asyncio.run(
        query_osv(
            dependency, approved_metadata_transfer=True, transport=httpx.MockTransport(handler)
        )
    )
    assert seen == [{"package": {"name": "example", "ecosystem": "PyPI"}, "version": "1.2.3"}]
    assert not result["complete"] and result["reachability"] == "NOT_CHECKED"
    for version in ["^1.2", "*", "latest", "https://evil", "1.2 || 2"]:
        with pytest.raises(ValueError):
            Dependency(ecosystem="npm", name="pkg", version=version)


def test_lockfile_ignores_private_registry_and_workspace_packages():
    items = from_lockfile(
        "package-lock.json",
        json.dumps(
            {
                "lockfileVersion": 3,
                "packages": {
                    "node_modules/example": {
                        "version": "1.2.3",
                        "resolved": "https://registry.npmjs.org/pkg",
                    },
                    "node_modules/private": {
                        "version": "1.2.3",
                        "resolved": "https://internal.test/pkg",
                    },
                },
            }
        ),
    )
    assert len(items) == 1 and items[0].name == "example"


def test_responses_adapter_excludes_reasoning_and_sends_schema():
    settings = Settings(_env_file=None).model_copy(
        update={
            "ai_enabled": True,
            "deepseek_api_key": SecretStr("test-only"),
        }
    )
    candidate = ResponsesCandidate(settings)

    def handler(request):
        data = json.loads(request.content)
        assert data["text"]["format"]["type"] == "json_schema"
        assert data["reasoning"]["effort"] == "none"
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {
                        "type": "reasoning",
                        "content": [{"type": "reasoning_text", "text": "private"}],
                    },
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": "{}"}],
                    },
                ],
                "usage": {"input_tokens": 1, "output_tokens": 2},
            },
        )

    result = asyncio.run(
        candidate.structured("system", "input", {}, transport=httpx.MockTransport(handler))
    )
    assert result == ("{}", 1, 2) and "private" not in str(result)


def test_conditional_candidate_is_per_call_and_does_not_mutate_defaults():
    candidate = ConditionalCandidate(Settings(_env_file=None))
    bundle = source_bundle("def f(n):\n    return list(range(0,n,n))")
    assert candidate.second(bundle.payload).reasoning_effort is None
    add_observations(bundle)
    assert (
        candidate.second(
            verification_payload(bundle.payload, json.dumps(output([])))
        ).reasoning_effort
        == "high"
    )
    assert candidate.reasoning_effort is None and candidate.max_output_tokens == 2000
