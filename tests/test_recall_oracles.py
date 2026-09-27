"""Trusted hand-authored reference behavior; never eval/exec/import corpus source strings."""

import hashlib
import json
from pathlib import Path

import pytest

from scripts.build_recall_cases import core_cases, holdout_cases


def resolved(env, verify=True, session=True, *, fixed=False):
    if verify is True or verify is None:
        configured = env.get("REQUESTS_CA_BUNDLE") or env.get("CURL_CA_BUNDLE")
        verify = (configured or verify) if fixed else configured
    if session is None:
        return verify
    return session if verify is None else verify


@pytest.mark.parametrize(
    "env,broken,expected",
    [
        ({}, True, True),
        ({"REQUESTS_CA_BUNDLE": ""}, True, True),
        ({"CURL_CA_BUNDLE": ""}, "", True),
        ({"REQUESTS_CA_BUNDLE": "", "CURL_CA_BUNDLE": ""}, "", True),
        ({"REQUESTS_CA_BUNDLE": "/ca.pem"}, "/ca.pem", "/ca.pem"),
    ],
)
def test_original_none_fallback_is_distinct_from_empty_string(env, broken, expected):
    assert resolved(env) == broken
    assert resolved(env, fixed=True) == expected
    assert resolved(env, False, fixed=True) is False


@pytest.mark.parametrize(
    "body,wire_length,character_length",
    [("", 0, 0), ("abc", 3, 3), ("한글", 6, 2), (b"abc", 3, 3), ("한글".encode(), 6, 6)],
)
def test_wire_byte_contract_and_normal_counterexamples(body, wire_length, character_length):
    wire = body.encode("utf-8") if isinstance(body, str) else body
    assert len(wire) == wire_length
    assert len(body) == character_length


@pytest.mark.parametrize("session", [True, False, None])
def test_empty_bundle_repair_preserves_explicit_true_instead_of_session_default(session):
    assert resolved({"CURL_CA_BUNDLE": ""}, True, session, fixed=True) is True
    assert resolved({"CURL_CA_BUNDLE": ""}, False, session, fixed=True) is False


def test_holdout_v2_anchor_was_frozen_before_any_model_results():
    root = Path("evals/recall-repair")
    data = (root / "holdout-v2.json").read_bytes()
    manifest = json.loads((root / "holdout-v2-manifest.json").read_text(encoding="utf-8"))
    assert hashlib.sha256(data).hexdigest() == manifest["sha256"]
    cases = json.loads(data)
    assert "+    return sum" in cases[0]["patch"]
    assert "+    pass" not in cases[0]["patch"]
    # Trusted handwritten reference, never load/execute the corpus code strings.
    assert sum(p * n for p, n in zip([3, 4], [2])) == 6
    with pytest.raises(ValueError):
        sum(p * n for p, n in zip([3, 4], [2], strict=True))


def test_manifests_and_generators_preserve_frozen_inputs():
    root = Path("evals/recall-repair")
    manifest = json.loads((root / "corpus-manifest.json").read_text(encoding="utf-8"))
    for name, generated in [("core-v2", core_cases()), ("holdout-v1", holdout_cases())]:
        raw = (root / (name + ".json")).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == manifest["corpora"][name]["sha256"]
        assert json.loads(raw) == generated
    assert len(core_cases()) == 6
    assert sum(bool(c["expected_locations"]) for c in core_cases()) == 2
