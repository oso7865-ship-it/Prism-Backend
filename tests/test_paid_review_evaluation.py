import asyncio
import json

import pytest

from scripts import run_paid_review_evaluation as evaluation


def test_fixed_corpora_and_call_budgets():
    baseline = evaluation.load_cases(7)
    extended = evaluation.load_cases(10)
    assert len(baseline) == 7 and len(extended) == 10
    assert extended[:7] == baseline
    assert len({case["id"] for case in extended}) == 10
    with pytest.raises(ValueError):
        evaluation.load_cases(11)


def test_failures_are_not_retried_and_existing_record_blocks_new_calls(tmp_path, monkeypatch):
    calls = []

    class FakeProvider:
        model = "offline-test"

        def __init__(self, settings):
            pass

        async def review(self, payload):
            calls.append(payload)
            raise RuntimeError("sensitive-provider-error-not-to-be-persisted")

    monkeypatch.setattr(evaluation, "Settings", lambda: None)
    monkeypatch.setattr(evaluation, "DeepSeekProvider", FakeProvider)
    output = tmp_path / "evaluation.json"
    assert not asyncio.run(evaluation.run(output, 10))
    record = json.loads(output.read_text(encoding="utf-8"))
    assert len(calls) == record["max_calls"] == len(record["cases"]) == 10
    assert all(case["attempts"] == 1 and case["status"] == "FAILED" for case in record["cases"])
    assert "sensitive-provider-error" not in output.read_text(encoding="utf-8")
    before = output.read_bytes()
    with pytest.raises(FileExistsError):
        asyncio.run(evaluation.run(output, 10))
    assert len(calls) == 10 and output.read_bytes() == before


def test_schema_diagnostics_do_not_store_model_values_or_unknown_field_names(tmp_path, monkeypatch):
    class FakeProvider:
        model = "offline-test"

        def __init__(self, settings):
            pass

        async def review(self, payload):
            return json.dumps({"summary": "private-value", "private-field": "private-value"}), 1, 1

    monkeypatch.setattr(evaluation, "Settings", lambda: None)
    monkeypatch.setattr(evaluation, "DeepSeekProvider", FakeProvider)
    output = tmp_path / "invalid.json"
    assert not asyncio.run(evaluation.run(output, 7))
    text = output.read_text(encoding="utf-8")
    assert "private-value" not in text and "private-field" not in text
    record = json.loads(text)
    assert len(record["cases"]) == 7
    for case in record["cases"]:
        errors = case["validation_errors"]
        assert {"type": "missing", "location": ["issues"]} in errors
        assert {"type": "extra_forbidden", "location": ["<unknown-field>"]} in errors
