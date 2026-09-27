import json
from pathlib import Path

import pytest

from app.domain.review.policy import prepare
from scripts import recall_evaluation as recall
from scripts import stabilize_review_quality as runner


def bundle():
    return prepare([{"filename": "a.py", "patch": "@@ -0,0 +1 @@\n+x = 1"}], [], [])


def diagnostic(**changes):
    return json.dumps(
        {
            "candidates": [
                {
                    "file_id": "f1",
                    "line": 1,
                    "observed_effect": "A specific value violates the supplied contract",
                    "disposition": "REPORT",
                    "reason": "CONTRACT_MISMATCH",
                    "missing_contract": None,
                    **changes,
                }
            ]
        }
    )


@pytest.mark.parametrize(
    "change",
    [
        {"line": 2},
        {"file_id": "unknown"},
        {"observed_effect": " "},
        {"disposition": "DEFER"},
        {"reason": "GUARDED"},
        {"missing_contract": "unknown caller"},
        {"observed_effect": "sk-" + "a" * 24},
    ],
)
def test_diagnostic_rejects_unanchored_or_inconsistent_observations(change):
    with pytest.raises(ValueError):
        recall.validate_diagnostic(diagnostic(**change), bundle())


def test_diagnostic_uses_bounded_observations_not_freeform_reasoning():
    result = recall.validate_diagnostic(diagnostic(), bundle())
    assert len(result["candidates"]) == 1
    assert "reasoning" not in result
    deferred = diagnostic(
        disposition="DEFER",
        reason="MISSING_CONTRACT",
        missing_contract="whether returned length is a wire byte count",
    )
    assert recall.validate_diagnostic(deferred, bundle())["candidates"][0]["disposition"] == "DEFER"


def test_recall_separates_normals_failures_and_verifier_removal():
    cases = [
        {"id": "bug", "expected_locations": [[1, 1]]},
        {"id": "normal", "expected_locations": []},
    ]
    records = [
        {
            "id": "bug",
            "status": "COMPLETED",
            "draft_grade": {"missed": 0},
            "grade": {"missed": 1, "unexpected": 0},
            "result": {"questions": []},
        },
        {"id": "bug", "status": "FAILED"},
        {
            "id": "normal",
            "status": "COMPLETED",
            "grade": {"missed": 0, "unexpected": 1},
            "result": {"questions": [{}]},
        },
    ]
    result = recall.quality_metrics(cases, records)
    assert result["recall"] == 0
    assert result["missed_defects"] == 2
    assert result["normal_false_positives"] == 1
    assert result["invalid_reviews"] == 1
    assert result["verifier_removed_expected"] == 1


def test_frozen_corpus_does_not_send_labels_or_provenance():
    for name in ["core-v2", "holdout-v1", "holdout-v2"]:
        for case in json.loads(
            Path(f"evals/recall-repair/{name}.json").read_text(encoding="utf-8")
        ):
            prepared = prepare([{"filename": case["path"], "patch": case["patch"]}], [], [])
            assert not prepared.omitted
            assert set(json.loads(prepared.payload)) == {"files", "static_findings"}
            assert "expected_locations" not in prepared.payload
            assert "provenance" not in prepared.payload
            assert "label_review" not in prepared.payload


@pytest.mark.anyio
async def test_diagnostic_attempt_is_reserved_and_not_scored_as_review(tmp_path, monkeypatch):
    case = {"id": "one", "path": "a.py", "patch": "@@ -0,0 +1 @@\n+x = 1", "expected_lines": []}
    corpus = tmp_path / "corpus.json"
    corpus.write_text(json.dumps([case]))

    class Provider:
        model = "test"

        def __init__(self, settings):
            pass

        async def review(self, payload):
            assert len(json.loads((tmp_path / "usage.json").read_text())["attempts"]) == 1
            return diagnostic(), 10, 20

    monkeypatch.setattr(runner, "DiagnosticProvider", Provider)
    result = await runner.run(corpus, "diagnostic", 1, 1, tmp_path, diagnose=True)
    assert result["summary"]["attempts"] == 1
    assert result["summary"]["automatic_passed"] == 0
    assert "quality_metrics" not in result
    assert "result" not in result["cases"][0]
    assert "candidate_diagnostic" in result["cases"][0]


@pytest.mark.anyio
async def test_frozen_baseline_is_independent_of_runtime_prompt_and_rejects_tampering(
    tmp_path, monkeypatch
):
    import shutil

    from app.shared.config.settings import Settings

    captured = []

    async def invoke(self, system, payload):
        captured.append(system)
        return "{}", 1, 1

    snapshot = tmp_path / "baseline"
    shutil.copytree(recall.ROOT, snapshot)
    monkeypatch.setattr(recall, "ROOT", snapshot)
    monkeypatch.setattr(recall.FrozenBaselineProvider, "invoke", invoke)
    provider = recall.FrozenBaselineProvider(Settings(_env_file=None))
    await provider.review(bundle().payload)
    assert len(captured) == 1
    assert "short-circuit expressions (language semantics" not in captured[0]
    await provider.verify(json.dumps({"context": json.loads(bundle().payload), "draft": {}}))
    assert len(captured) == 2
    assert "short-circuit expressions (language semantics" not in captured[1]
    assert "Verification JSON schema:" in captured[1]
    (snapshot / "baseline-python.prompt").write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="BASELINE_CHANGED"):
        await provider.review(bundle().payload)
    assert len(captured) == 2


def test_adoption_requires_matching_semantic_review_even_with_perfect_location_score():
    record = {
        "id": "case",
        "repeat": 1,
        "status": "COMPLETED",
        "grade": {"passed": True},
        "result": {"issues": []},
    }
    assessment = {
        "id": "case",
        "repeat": 1,
        "status": "PASS",
        "result_sha256": recall.result_digest(record),
    }
    assert recall.adoption_gate([record], [assessment])["status"] == "PASS"
    assert recall.adoption_gate([record], [dict(assessment, status="FAIL")])["status"] == "FAIL"
    assert (
        recall.adoption_gate([record], [dict(assessment, result_sha256="stale")])["status"]
        == "FAIL"
    )
    assert recall.adoption_gate([record], [])["status"] == "FAIL"
    assert recall.adoption_gate([], [])["status"] == "FAIL"
