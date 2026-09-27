import asyncio
import json

import pytest

from app.domain.review.policy import prepare
from scripts import evaluate_context_retrieval as evaluation


def test_paid_comparison_has_twenty_four_call_ceiling_and_no_retry(tmp_path, monkeypatch):
    calls = []

    class FakeProvider:
        def __init__(self, settings):
            pass

        async def review(self, payload):
            calls.append(payload)
            raise ValueError("do-not-record-private-code")

    async def fake_build(case, model=False):
        return prepare([{"filename": case["path"], "patch": case["patch"]}], [], []), {
            "candidate_digest": "fixed",
            "selected_hit": True,
            "ranking": {"mode": "local_reranker" if model else "rules", "duration_ms": 10},
        }

    monkeypatch.setattr(evaluation, "DeepSeekProvider", FakeProvider)
    monkeypatch.setattr(evaluation, "Settings", lambda: None)
    monkeypatch.setattr(evaluation, "build", fake_build)
    output = tmp_path / "evaluation.json"
    asyncio.run(evaluation.run(output, paid=True))
    record = json.loads(output.read_text(encoding="utf-8"))
    assert len(calls) == record["max_paid_calls"] == 24
    assert all(a["review"]["attempts"] == 1 for c in record["cases"] for a in c["arms"].values())
    assert "do-not-record-private-code" not in output.read_text(encoding="utf-8")
    with pytest.raises(FileExistsError):
        asyncio.run(evaluation.run(output, paid=True))
    assert len(calls) == 24


def test_candidate_mismatch_aborts_comparison(tmp_path, monkeypatch):
    class NoCallProvider:
        def __init__(self, settings):
            pass

        async def review(self, payload):
            pytest.fail("candidate mismatch must be detected before a paid call")

    async def fake_build(case, model=False):
        return None, {"candidate_digest": str(model), "ranking": {"mode": "local_reranker"}}

    monkeypatch.setattr(evaluation, "build", fake_build)
    monkeypatch.setattr(evaluation, "DeepSeekProvider", NoCallProvider)
    monkeypatch.setattr(evaluation, "Settings", lambda: None)
    with pytest.raises(ValueError, match="CANDIDATE_SET_CHANGED"):
        asyncio.run(evaluation.run(tmp_path / "evaluation.json", paid=True))


def test_error_diagnostics_keep_guardrail_code_but_not_private_exception_text():
    assert evaluation.error_details(ValueError("INVALID_EVIDENCE_LINES"), "validation") == {
        "error_type": "ValueError",
        "error_code": "INVALID_EVIDENCE_LINES",
        "error_stage": "validation",
    }
    private = evaluation.error_details(ValueError("private-source"), "provider")
    assert private["error_code"] == "UNCLASSIFIED_ERROR"
    assert "private-source" not in json.dumps(private)
