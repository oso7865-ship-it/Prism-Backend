import json
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from app.domain.review.policy import prepare, validate_result
from app.shared.config.settings import Settings
from scripts import evaluation_thinking_provider as thinking_provider
from scripts import stabilize_review_quality as evaluation
from scripts.quality_reasoning_provider import HybridQualityProvider, ReasoningQualityProvider


@pytest.mark.anyio
async def test_verification_attempts_have_their_own_durable_reservation(tmp_path, monkeypatch):
    from test_review_harness import output

    corpus = tmp_path / "cases.json"
    corpus.write_text(
        json.dumps(
            [{"id": "one", "path": "a.py", "patch": "@@ -0,0 +1 @@\n+x=1", "expected_lines": [1]}]
        )
    )
    calls = []

    class Provider:
        model = "test"

        def __init__(self, settings):
            pass

        async def review(self, payload):
            assert len(json.loads((tmp_path / "usage.json").read_text())["attempts"]) == 1
            calls.append("draft")
            return json.dumps(output([1])), 100, 30

        async def verify(self, payload):
            ledger = json.loads((tmp_path / "usage.json").read_text())["attempts"]
            assert len(ledger) == 2 and ledger[-1]["phase"] == "verification"
            calls.append("verify")
            raise TimeoutError("private verification failure")

    monkeypatch.setattr(evaluation, "DeepSeekProvider", Provider)
    record = await evaluation.run(corpus, "two-phases", 1, 2, tmp_path, verify=True)
    assert calls == ["draft", "verify"]
    assert record["summary"]["attempts"] == 2 and record["summary"]["validated"] == 0
    assert record["summary"]["input_tokens"] == 100
    assert "private verification failure" not in json.dumps(record)


def test_gold_location_score_uses_ranges_and_rejects_duplicates_without_claiming_semantics():
    case = {"path": "a.py", "expected_locations": [[3, 7]]}
    result = {"issues": [{"file_path": "a.py", "line": 5}], "questions": []}
    assert evaluation.grade(case, result) == {
        "passed": True,
        "missed": 0,
        "unexpected": 0,
        "scope": "location_only",
    }
    result["issues"] *= 2
    assert not evaluation.grade(case, result)["passed"]


@pytest.mark.anyio
@pytest.mark.parametrize("fails", [False, True])
async def test_empty_recheck_matches_product_and_reserves_before_second_call(
    tmp_path, monkeypatch, fails
):
    corpus = tmp_path / "cases.json"
    corpus.write_text(
        json.dumps(
            [{"id": "one", "path": "a.py", "patch": "@@ -0,0 +1 @@\n+x=1", "expected_lines": []}]
        )
    )

    class Provider:
        model = "test"

        def __init__(self, settings):
            pass

        async def review(self, payload):
            return json.dumps({"summary": "ok", "issues": [], "limitations": "scope"}), 10, 5

        async def recheck_empty(self, payload):
            attempts = json.loads((tmp_path / "usage.json").read_text())["attempts"]
            assert len(attempts) == 2 and attempts[-1]["phase"] == "empty_recheck"
            if fails:
                raise TimeoutError("private input")
            return (
                json.dumps(
                    {
                        "summary": "ok",
                        "issues": [],
                        "limitations": "scope",
                        "file_checks": [
                            {
                                "file_id": "f1",
                                "line": 1,
                                "outcome": "NO_FINDING",
                                "observation": "constant assignment",
                            }
                        ],
                    }
                ),
                20,
                10,
            )

    monkeypatch.setattr(evaluation, "DeepSeekProvider", Provider)
    record = await evaluation.run(corpus, "empty", 1, 2, tmp_path, verify=True, recheck_empty=True)
    assert record["summary"]["attempts"] == 2
    assert record["summary"]["validated"] == (0 if fails else 1)
    assert record["summary"]["input_tokens"] == (10 if fails else 30)
    assert "private input" not in json.dumps(record)
    if not fails:
        assert record["cases"][0]["result"]["verification"]["status"] == "EMPTY_RECHECKED"


@pytest.mark.anyio
async def test_attempts_persist_before_call_failures_count_and_repeat_is_refused(
    tmp_path, monkeypatch
):
    corpus = tmp_path / "cases.json"
    corpus.write_text(
        json.dumps(
            [{"id": "one", "path": "a.py", "patch": "@@ -0,0 +1 @@\n+x = 1", "expected_lines": []}]
        )
    )
    root = tmp_path / "runs"
    calls = []

    class Provider:
        model = "test"

        def __init__(self, settings):
            pass

        async def review(self, payload):
            saved = json.loads((root / "usage.json").read_text())
            calls.append(payload)
            assert len(saved["attempts"]) == len(calls)
            raise RuntimeError("private source and key")

    monkeypatch.setattr(evaluation, "DeepSeekProvider", Provider)
    record = await evaluation.run(corpus, "baseline", 2, 2, root)
    assert record["summary"]["attempts"] == 2
    assert record["summary"]["validated"] == 0
    assert "private source" not in (root / "baseline.json").read_text()
    with pytest.raises(FileExistsError):
        await evaluation.run(corpus, "baseline", 2, 2, root)
    assert len(calls) == 2
    assert not (root / "running.lock").exists()
    monkeypatch.setattr(evaluation, "LIMIT", 2)
    (root / "usage.json").write_text(json.dumps({"limit": 2, "attempts": record["cases"]}))
    with pytest.raises(ValueError, match="AUTHORIZATION_EXHAUSTED"):
        await evaluation.run(corpus, "more", 1, 1, root)
    assert len(calls) == 2


def test_schema_diagnostics_strip_values_and_unknown_field_names():
    bundle = prepare([{"filename": "a.py", "patch": "@@ -0,0 +1 @@\n+x = 1"}], [], [])
    raw = json.dumps(
        {"summary": ["private"], "issues": [], "limitations": "ok", "private-key": "private"}
    )
    with pytest.raises(ValueError) as caught:
        validate_result(raw, bundle)
    detail = evaluation.diagnostics(caught.value, "validation", raw, bundle)
    assert detail["error_code"] == "SCHEMA_VALIDATION"
    assert "private" not in json.dumps(detail)
    assert any(i["location"] == ["<unknown-field>"] for i in detail["fields"])


@pytest.mark.anyio
async def test_experimental_profiles_keep_stage_models_and_do_not_read_reasoning(monkeypatch):
    captured = []

    class Response(SimpleNamespace):
        @property
        def additional_kwargs(self):
            raise AssertionError("Reasoning must not be accessed or persisted")

    class Chat:
        def __init__(self, **kwargs):
            self.settings = kwargs

        def bind(self, **kwargs):
            captured.append((self.settings, kwargs))
            return self

        async def ainvoke(self, messages, config):
            return Response(
                content="{}", usage_metadata={}, response_metadata={"finish_reason": "stop"}
            )

    monkeypatch.setattr("app.domain.review.provider.ChatDeepSeek", Chat)
    settings = Settings(_env_file=None, ai_enabled=False).model_copy(
        update={"ai_enabled": True, "deepseek_api_key": SecretStr("test-only-not-a-key")}
    )
    hybrid = HybridQualityProvider(settings)
    await hybrid.invoke("instructions", "data")
    await hybrid.checker().invoke("instructions", "data")
    assert captured[0][0]["model_name"] == "deepseek-flash"
    assert captured[0][1]["extra_body"]["thinking"]["type"] == "disabled"
    assert captured[1][0]["model_name"] == "deepseek-v4-pro"
    assert captured[1][1]["extra_body"]["reasoning_effort"] == "low"
    assert captured[1][0]["max_tokens"] == 8192
    assert all(s["max_retries"] == 0 and s["timeout"] == 60 for s, _ in captured)
    assert ReasoningQualityProvider.reasoning_effort == "high"


def test_anchor_diagnostics_distinguish_cross_file_lines_without_source():
    bundle = prepare([{"filename": "a.py", "patch": "@@ -0,0 +1 @@\n+x = 1"}], [], [])
    raw = json.dumps(
        {
            "issues": [
                {"file_id": "f1", "line": 1, "evidence_lines": [1, 104], "evidence": "private"}
            ]
        }
    )
    detail = evaluation.diagnostics(ValueError("INVALID_EVIDENCE_LINES"), "validation", raw, bundle)
    assert detail["anchors"][0]["unprovided"] == [104]
    assert detail["anchors"][0]["has_changed_evidence"]
    assert "private" not in json.dumps(detail)


@pytest.mark.anyio
async def test_lock_and_exact_batch_limit_prevent_extra_calls(tmp_path):
    corpus = tmp_path / "cases.json"
    corpus.write_text(json.dumps([{"id": "one"}]))
    with pytest.raises(ValueError, match="EXACT_BATCH_LIMIT_REQUIRED"):
        await evaluation.run(corpus, "run", 1, 2, tmp_path)
    (tmp_path / "running.lock").write_text("another run")
    with pytest.raises(FileExistsError):
        await evaluation.run(corpus, "run", 1, 1, tmp_path)
    assert (tmp_path / "running.lock").read_text() == "another run"


@pytest.mark.anyio
async def test_connection_failure_stops_batch_after_one_reserved_attempt(tmp_path, monkeypatch):
    corpus = tmp_path / "cases.json"
    corpus.write_text(
        json.dumps(
            [
                {
                    "id": "one",
                    "path": "a.py",
                    "patch": "@@ -0,0 +1 @@\n+x = 1",
                    "expected_lines": [],
                }
            ]
        )
    )

    class OpenAIConnectionError(Exception):
        pass

    class Provider:
        model = "test"

        def __init__(self, settings):
            pass

        async def review(self, payload):
            raise OpenAIConnectionError("private endpoint")

    monkeypatch.setattr(evaluation, "DeepSeekProvider", Provider)
    result = await evaluation.run(corpus, "connection-failure", 3, 3, tmp_path)
    assert result["halted"] == "PROVIDER_UNAVAILABLE"
    assert result["summary"]["authorized_attempts_used"] == 1
    assert len(result["cases"]) == 1
    assert "private endpoint" not in json.dumps(result)


def test_quality_score_requires_useful_questions_without_accepting_them_as_proven_bugs():
    case = {"path": "a.js", "expected_lines": [], "expected_questions": [2]}
    item = {"file_path": "a.js", "line": 2}
    assert evaluation.grade(case, {"issues": [], "questions": [item]})["passed"]
    assert not evaluation.grade(case, {"issues": [item], "questions": []})["passed"]
    assert not evaluation.grade(case, {"issues": [], "questions": []})["passed"]
    case["expected_lines"], case["expected_questions"] = [2], []
    assert not evaluation.grade(case, {"issues": [], "questions": [item]})["passed"]


@pytest.mark.anyio
@pytest.mark.parametrize("finish", ["stop", "length"])
async def test_experimental_thinking_returns_only_final_content_and_rejects_truncation(
    monkeypatch, finish
):
    captured = {}

    class Response(SimpleNamespace):
        @property
        def additional_kwargs(self):
            raise AssertionError("Reasoning must never be accessed")

    class FakeChat:
        def __init__(self, **kwargs):
            captured["settings"] = kwargs

        def bind(self, **kwargs):
            captured["binding"] = kwargs
            return self

        async def ainvoke(self, messages, config):
            assert config == {"callbacks": []}
            return Response(
                content='{"final": true}',
                usage_metadata={"input_tokens": 10, "output_tokens": 20},
                response_metadata={"finish_reason": finish},
            )

    monkeypatch.setattr(thinking_provider, "ChatDeepSeek", FakeChat)
    settings = Settings(_env_file=None, ai_enabled=False).model_copy(
        update={"ai_enabled": True, "deepseek_api_key": SecretStr("test-only-not-a-key")}
    )
    bundle = prepare([{"filename": "a.py", "patch": "@@ -0,0 +1 @@\n+x = 1"}], [], [])
    provider = thinking_provider.EvaluationThinkingProvider(settings)
    if finish == "stop":
        assert await provider.review(bundle.payload) == ('{"final": true}', 10, 20)
    else:
        with pytest.raises(ValueError, match="OUTPUT_TRUNCATED"):
            await provider.review(bundle.payload)
    assert captured["settings"]["max_retries"] == 0
    assert captured["settings"]["max_tokens"] == 4096
    assert captured["binding"]["extra_body"] == {
        "thinking": {"type": "enabled"},
        "reasoning_effort": "low",
    }
