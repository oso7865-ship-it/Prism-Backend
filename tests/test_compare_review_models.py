"""Offline checks for paid comparison isolation, cap, recovery and metadata privacy."""

import asyncio
import json
from types import SimpleNamespace

import pytest

from scripts.compare_review_models import BATCH, LIMIT, MODELS, Comparison, response_metadata, score
from scripts.quality_lab_protocol import LabOutput, bundle_for, review_system
from scripts.quality_lab_runner import MAXIMUM, START, StopCampaign


class FakeProvider:
    def __init__(self):
        self.calls = []

    async def invoke(self, model_id, system, payload):
        self.calls.append((model_id, system, payload))
        return (
            json.dumps({"summary": "검토", "issues": [], "limitations": "제공 범위", "probes": []}),
            {
                "input_tokens": 10,
                "output_tokens": 5,
                "finish_reason": "stop",
                "response_model": model_id,
            },
        )


def experiment(tmp_path, provider=None):
    (tmp_path / "usage.json").write_text(
        json.dumps(
            {
                "limit": START + MAXIMUM,
                "attempts": [{"run": "prior"}] * START,
            }
        )
    )
    return Comparison(tmp_path, provider or FakeProvider())


def test_paired_inputs_and_planned_maximum(tmp_path):
    exp = experiment(tmp_path)
    jobs = exp.jobs()
    assert len(jobs) == 312
    assert sum(1 if j[0] == "diagnostic" else 2 for j in jobs) == LIMIT
    assert len({(kind, c["id"], arm, r) for kind, c, arm, r, _ in jobs}) == 312
    for case in exp.cases:
        flash = bundle_for(case, "F0", probes=False)
        pro = bundle_for(case, "P0", probes=False)
        assert flash.payload == pro.payload
        assert review_system(flash, "F0") == review_system(pro, "P0")


def test_model_dispatch_resume_and_reservation(tmp_path):
    asyncio.run(check_model_dispatch_resume_and_reservation(tmp_path))


async def check_model_dispatch_resume_and_reservation(tmp_path):
    provider = FakeProvider()
    exp = experiment(tmp_path, provider)
    for arm in MODELS:
        await exp.diagnostic(exp.cases[0], arm, 1)
        await exp.diagnostic(exp.cases[0], arm, 1)
    assert len(provider.calls) == 2
    assert {row[0] for row in provider.calls} == set(MODELS.values())
    assert provider.calls[0][1:] == provider.calls[1][1:]
    assert exp.count == 2
    # Deliberately invalid probe IDs still consume budget, without automatic retry.
    assert all(
        json.loads(p.read_text())["status"] == "FAILED" for p in (exp.root / "calls").glob("*.json")
    )
    case = exp.cases[0]
    bundle = bundle_for(case)
    exp.ledger.reserve(BATCH + ":lost", "P0", "diagnostic")
    lost = await exp.call(
        "lost", "P0", "diagnostic", "system", bundle.payload, LabOutput, case, bundle
    )
    assert lost["status"] == "INTERRUPTED_UNKNOWN"
    assert len(provider.calls) == 2
    exp.ledger.data["attempts"].extend({"key": BATCH + ":cap", "run": "test"} for _ in range(LIMIT))
    with pytest.raises(StopCampaign):
        await exp.call(
            "over", "P0", "diagnostic", "system", bundle.payload, LabOutput, case, bundle
        )
    assert len(provider.calls) == 2


def test_response_metadata_excludes_reasoning_and_arbitrary_fields():
    response = SimpleNamespace(
        usage_metadata={"input_tokens": 100, "output_tokens": 20},
        response_metadata={
            "model_name": "deepseek-v4-pro",
            "finish_reason": "stop",
            "token_usage": {"prompt_cache_hit_tokens": 64},
            "reasoning_content": "private",
            "headers": {"Authorization": "private"},
        },
    )
    observed = response_metadata(response)
    assert observed["cached_input_tokens"] == 64
    assert "private" not in json.dumps(observed)
    response.response_metadata["token_usage"]["prompt_cache_hit_tokens"] = 1000
    assert "cached_input_tokens" not in response_metadata(response)


def test_alias_grade_preserves_original():
    case = {
        "fixed": False,
        "expected_lines": [],
        "oracle": [{"probe_id": "p", "outcome": "RAISE", "exception_type": "NullPointerException"}],
    }
    output = {
        "issues": [],
        "probes": [
            {
                "probe_id": "p",
                "outcome": "RAISE",
                "exception_type": "java.lang.NullPointerException",
                "value_json": None,
            }
        ],
    }
    assert score(case, output)["probe_correct"] == 1
    assert output["probes"][0]["exception_type"].startswith("java.lang.")


def test_auth_failure_stops_without_saving_error_body(tmp_path):
    asyncio.run(check_auth_failure_stops_without_saving_error_body(tmp_path))


async def check_auth_failure_stops_without_saving_error_body(tmp_path):
    class Denied(Exception):
        status_code = 401

    class DeniedProvider:
        async def invoke(self, *args):
            raise Denied("credential-and-private-error-body")

    exp = experiment(tmp_path, DeniedProvider())
    await exp.diagnostic(exp.cases[0], "P0", 1)
    assert exp.stop
    record = next((exp.root / "calls").glob("*.json")).read_text()
    assert "credential-and-private" not in record
    assert json.loads(record)["http_status"] == 401
