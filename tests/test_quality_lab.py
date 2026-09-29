"""Offline protocol/oracle checks; never execute fixture/model source strings."""

import json

import pytest

from app.domain.analysis.analyzer import parser_for
from app.domain.analysis.contracts import language_for
from scripts.quality_lab_cases import generate
from scripts.quality_lab_protocol import (
    ARMS,
    STAGES,
    LabOutput,
    bundle_for,
    digest,
    grade,
    same_value,
    validate,
)
from scripts.quality_lab_runner import CAMPAIGN, MAXIMUM, START, Ledger, StopCampaign


def test_frozen_corpus_and_payloads_do_not_expose_labels():
    from pathlib import Path

    root = Path("evals/quality-lab-20260929")
    raw = (root / "corpus.json").read_text(encoding="utf-8")
    assert digest(raw) == json.loads((root / "manifest.json").read_text())["sha256"]
    assert json.loads(raw) == generate()
    assert sum(STAGES.values()) * 40 == 960
    for case in generate():
        parser = parser_for(language_for(case["path"]), case["path"])
        assert not parser.parse(case["source"].encode()).root_node.has_error
        for arm in ARMS:
            payload = json.loads(bundle_for(case, arm).payload)
            assert (
                not {"oracle", "fixed", "family", "expected_lines", "id", "split"} & payload.keys()
            )
            assert case["id"] not in json.dumps(payload)


def test_boolean_type_is_not_numeric_equality():
    assert not same_value(False, 0)
    assert not same_value([True], [1])
    assert same_value(3, 3.0)


def test_budget_reservation_is_durable_unique_and_capped(tmp_path):
    path = tmp_path / "usage.json"
    path.write_text(json.dumps({"limit": 3000, "attempts": [{"run": "prior"}] * START}))
    ledger = Ledger(tmp_path)
    assert ledger.data["limit"] == START + MAXIMUM
    assert ledger.reserve("request-1", "C0", "final")
    assert not ledger.reserve("request-1", "C0", "final")
    reread = Ledger(tmp_path)
    assert reread.count == 1
    assert json.loads(path.read_text(encoding="utf-8"))["attempts"][-1]["run"] == CAMPAIGN
    reread.count = MAXIMUM
    with pytest.raises(StopCampaign):
        reread.reserve("request-2", "C0", "final")


def test_probe_ids_types_and_anchors_are_validated():
    case = generate()[0]
    output = {"summary": "test", "issues": [], "limitations": "test", "probes": case["oracle"]}
    bundle = bundle_for(case)
    parsed = validate(json.dumps(output), LabOutput, case, bundle)
    assert grade(case, parsed)["probe_correct"] == 3
    assert grade(case, parsed)["miss"]
    output["probes"] = [output["probes"][0]] * 3
    with pytest.raises(ValueError, match="PROBE_IDS"):
        validate(json.dumps(output), LabOutput, case, bundle)


def test_trusted_python_reference_observations():
    # Handwritten reference operations, independent of fixture strings; no eval/exec.
    assert ("" or "default") == "default"
    assert (False or True) is True
    assert len("한글") == 2 and len("한글".encode()) == 6
    with pytest.raises(ValueError):
        list(range(0, 0, 0))
    assert list(range(0, 0, max(0, 1))) == []

    def append(item, bucket=[]):
        bucket.append(item)
        return bucket

    first, second = list(append(1)), list(append(2))
    assert [first, second] == [[1], [1, 2]]
    assert "/srv/application/key".startswith("/srv/app")
    assert not "/srv/application/key".startswith("/srv/app/")
    with pytest.raises(ZeroDivisionError):
        sum([]) / len([])
    assert sum([2, 4]) / len([2, 4]) == 3.0
    assert [f() for f in [lambda: i for i in range(3)]] == [2, 2, 2]
    assert [f() for f in [lambda i=i: i for i in range(3)]] == [0, 1, 2]
    base = {"nested": {"limit": 1}}
    other = base.copy()
    other["nested"]["limit"] = 9
    assert base["nested"]["limit"] == 9


def test_trusted_integer_overflow_and_foreign_language_gold():
    def int32(value):
        return ((value + 2**31) % 2**32) - 2**31

    assert int32(50000 * 50000) == -1794967296
    assert int32(-(2**31) - 1) == 2147483647
    cases = {(c["family"], c["fixed"]): c for c in generate()}

    def gold(family, fixed, index=0):
        return cases[family, fixed]["oracle"][index]

    assert gold("int-overflow", False)["value_json"] == "-1794967296"
    assert gold("int-overflow", True)["value_json"] == "2500000000"
    assert gold("null-branch", False)["exception_type"] == "NullPointerException"
    assert gold("zero-count", False)["value_json"] == "10"
    assert gold("zero-count", True)["value_json"] == "0"
    assert gold("ownership", False)["value_json"] == "40"
    assert gold("ownership", True)["exception_type"] == "Error"
    assert gold("async-guard", False)["value_json"] == '"allowed"'
    assert gold("async-guard", True)["value_json"] == '"denied"'
    assert gold("optional-chain", False)["exception_type"] == "TypeError"
    assert gold("optional-chain", True)["value_json"] == '"Unknown"'


def test_product_path_does_not_send_evaluation_probes():
    for case in generate():
        payload = json.loads(bundle_for(case, probes=False).payload)
        assert "probe_calls" not in payload
        assert "oracle" not in payload


def test_exception_alias_erratum_does_not_treat_arbitrary_types_as_equal():
    from scripts.quality_lab_rescore import ALIASES

    assert ALIASES["java.lang.NullPointerException"] == "NullPointerException"
    assert "custom.NullPointerException" not in ALIASES
    assert "TypeError" not in ALIASES


def test_paid_call_checkpoint_and_auth_circuit_prevent_extra_requests(tmp_path):
    import asyncio

    from app.domain.review.policy import ReviewOutput
    from scripts.quality_lab_runner import Experiment

    class FakeProvider:
        model = "offline-test"
        count = 0

        async def invoke(self, system, payload):
            self.count += 1
            return json.dumps({"summary": "ok", "issues": [], "limitations": "test"}), 1, 1

    class Unauthorized(Exception):
        status_code = 401

    class BadProvider(FakeProvider):
        async def invoke(self, system, payload):
            self.count += 1
            raise Unauthorized("Never persist this simulated secret-bearing provider body")

    async def scenario():
        (tmp_path / "usage.json").write_text(
            json.dumps({"limit": 3000, "attempts": [{"run": "prior"}] * START})
        )
        folder = tmp_path / "artifacts"
        (folder / "calls").mkdir(parents=True)
        exp = Experiment.__new__(Experiment)
        exp.root, exp.ledger = folder, Ledger(tmp_path)
        exp.provider, exp.semaphore = FakeProvider(), asyncio.Semaphore(4)
        exp.stop, exp.failures = False, 0
        case = generate()[0]
        bundle = bundle_for(case)
        first = await exp.call(
            "one", "C0", "test", "system", bundle.payload, ReviewOutput, case, bundle
        )
        second = await exp.call(
            "one", "C0", "test", "system", bundle.payload, ReviewOutput, case, bundle
        )
        assert first == second and exp.provider.count == 1 and exp.ledger.count == 1
        exp.provider = BadProvider()
        failed = await exp.call(
            "two", "C0", "test", "system", bundle.payload, ReviewOutput, case, bundle
        )
        assert failed["http_status"] == 401 and exp.stop
        assert "simulated secret" not in (folder / "calls/two.json").read_text()
        with pytest.raises(StopCampaign):
            await exp.call(
                "three", "C0", "test", "system", bundle.payload, ReviewOutput, case, bundle
            )
        assert exp.ledger.count == 2
        # A reservation without a response cannot safely be repeated after interruption.
        exp.stop = False
        exp.ledger.reserve("lost", "C0", "test")
        lost = await exp.call(
            "lost", "C0", "test", "system", bundle.payload, ReviewOutput, case, bundle
        )
        assert lost["status"] == "INTERRUPTED_UNKNOWN" and exp.provider.count == 1

    asyncio.run(scenario())
