import asyncio
import json
from pathlib import Path

import pytest

from scripts import review_accuracy_runner as runner

CORPUS = Path("evals/review-accuracy-v1/cases-holdout.json")


def ledger_file(tmp_path, attempts=5):
    path = tmp_path / "usage.json"
    path.write_text(
        json.dumps(
            {
                "limit": 100,
                "attempts": [{"run": "old", "key": f"k{i}"} for i in range(attempts)],
                "authorizations": [],
            }
        ),
        encoding="utf-8",
    )
    return path


class Provider:
    model = "fake"

    def __init__(self, ledger_path, fail_with=None):
        self.ledger_path, self.fail_with, self.calls = ledger_path, fail_with, 0

    async def review(self, payload):
        # The reservation must already be durable when the provider is invoked.
        data = json.loads(self.ledger_path.read_text(encoding="utf-8"))
        drafts = [
            a for a in data["attempts"] if a["run"] == runner.CAMPAIGN and a["phase"] == "draft"
        ]
        assert len(drafts) == self.calls + 1
        self.calls += 1
        if self.fail_with:
            raise self.fail_with
        return json.dumps({"summary": "x", "issues": [], "limitations": "y"}), 1, 1

    async def verify(self, payload):
        raise AssertionError("not reached")

    async def recheck_empty(self, payload):
        raise ValueError("RECHECK_FAILED")


def go(tmp_path, provider, ledger, **kw):
    kw.setdefault("max_calls", 24)
    kw.setdefault("repeats", 1)
    return asyncio.run(
        runner.run(
            CORPUS,
            kw.pop("name", "t1"),
            kw["repeats"],
            kw["max_calls"],
            ledger,
            provider,
            tmp_path / "results",
        )
    )


def test_authorization_recorded_once_and_cap_cannot_exceed_user_limit(tmp_path):
    ledger = ledger_file(tmp_path)
    with pytest.raises(ValueError, match="CAP_EXCEEDS_AUTHORIZATION"):
        runner.Ledger(ledger, runner.AUTHORIZED_MAXIMUM + 1)
    runner.Ledger(ledger, 10)
    runner.Ledger(ledger, 10)
    data = json.loads(ledger.read_text(encoding="utf-8"))
    entries = [a for a in data["authorizations"] if a["campaign"] == runner.CAMPAIGN]
    assert len(entries) == 1
    assert entries[0]["maximum_new_attempts"] == 3000
    assert data["limit"] >= 5 + 3000


def test_reservation_is_durable_before_call_and_failures_still_count(tmp_path):
    ledger = ledger_file(tmp_path)
    provider = Provider(ledger, fail_with=ValueError("INVALID_OUTPUT"))
    record = go(tmp_path, provider, ledger)
    assert provider.calls == 12
    assert all(i["status"] == "FAILED" for i in record["cases"])
    data = json.loads(ledger.read_text(encoding="utf-8"))
    assert sum(a["run"] == runner.CAMPAIGN for a in data["attempts"]) == 12
    assert "draft_raw" not in json.dumps(record)  # no raw content stored for failed drafts


def test_run_limit_must_cover_worst_case_and_is_enforced(tmp_path):
    ledger = ledger_file(tmp_path)
    with pytest.raises(ValueError, match="MAX_CALLS_BELOW_WORST_CASE"):
        go(tmp_path, Provider(ledger), ledger, max_calls=23)


def test_empty_draft_uses_exactly_one_recheck_and_recheck_failure_is_not_success(tmp_path):
    ledger = ledger_file(tmp_path)
    provider = Provider(ledger)
    record = go(tmp_path, provider, ledger)
    assert all(i["status"] == "FAILED" for i in record["cases"])
    data = json.loads(ledger.read_text(encoding="utf-8"))
    phases = [a["phase"] for a in data["attempts"] if a["run"] == runner.CAMPAIGN]
    assert phases.count("draft") == 12
    assert phases.count("recheck") == 12  # a failed recheck is never retried or hidden


def test_existing_output_and_reserved_key_are_refused(tmp_path):
    ledger = ledger_file(tmp_path)
    go(tmp_path, Provider(ledger, fail_with=ValueError("x")), ledger)
    with pytest.raises(FileExistsError):
        go(tmp_path, Provider(ledger), ledger)
    data = json.loads(ledger.read_text(encoding="utf-8"))
    guard = runner.Ledger(ledger, 100)
    key = next(a["key"] for a in data["attempts"] if a["run"] == runner.CAMPAIGN)
    with pytest.raises(RuntimeError, match="ALREADY_RESERVED_WITHOUT_RESULT"):
        guard.reserve(key, "c", "draft")


def test_each_campaign_has_its_own_authorization_and_count(tmp_path):
    ledger = ledger_file(tmp_path)
    modes = "review-modes-20261005"
    with pytest.raises(ValueError, match="CAP_EXCEEDS_AUTHORIZATION"):
        runner.Ledger(ledger, 601, modes)
    first = runner.Ledger(ledger, 600, modes)
    first.reserve("m1", "case", "draft")
    other = runner.Ledger(ledger, 100, runner.CAMPAIGN)
    assert other.count == 0 and first.count == 1  # one campaign never uses another's allowance
    data = json.loads(ledger.read_text(encoding="utf-8"))
    entry = next(a for a in data["authorizations"] if a["campaign"] == modes)
    assert entry["maximum_new_attempts"] == 600
    assert [a["run"] for a in data["attempts"] if a.get("key") == "m1"] == [modes]
