"""Read-only paid results aggregation plus local post-processing replay; no network."""

import argparse
import json
import math
import statistics
from collections import Counter
from pathlib import Path

from app.domain.review.empty_review import validate_empty_review
from app.domain.review.harness import compose
from app.domain.review.policy import ReviewOutput
from app.domain.review.refinement import add_observations, verified_result
from scripts.quality_lab_bridge import legacy_bundle, old_cases
from scripts.quality_lab_protocol import bundle_for, digest
from scripts.quality_repair_fresh import cases as fresh_cases
from scripts.stabilize_review_quality import save


def report(root):
    batch = root / "quality-repair-20260929"
    rows = [json.loads(p.read_text(encoding="utf-8")) for p in (batch / "results").glob("*.json")]
    calls = {
        p.stem: json.loads(p.read_text(encoding="utf-8")) for p in (batch / "calls").glob("*.json")
    }
    fresh = {c["id"] for c in fresh_cases()}
    comparisons = []
    for subset in ("regression", "fresh"):
        for arm in sorted({row["arm"] for row in rows}):
            chosen = [
                r for r in rows if r["arm"] == arm and ((r["case"] in fresh) == (subset == "fresh"))
            ]
            if not chosen:
                continue
            durations = sorted(
                sum(
                    c["seconds"]
                    for key, c in calls.items()
                    if key.startswith(f"{arm}-{r['case']}-r1-")
                )
                for r in chosen
            )
            comparisons.append(
                {
                    "subset": subset,
                    "arm": arm,
                    "cases": len(chosen),
                    "bugs": sum(r["metrics"]["expected_bug"] for r in chosen),
                    **{
                        key: sum(r["metrics"][key] for r in chosen)
                        for key in ("valid", "miss", "normal_false_positive", "questions")
                    },
                    "median_seconds": round(statistics.median(durations), 3),
                    "p95_seconds": durations[math.ceil(len(durations) * 0.95) - 1],
                    "errors": dict(Counter(r["error"] for r in chosen if r["error"])),
                }
            )
    cases = json.loads(Path("evals/quality-lab-20260929/corpus.json").read_text(encoding="utf-8"))
    mapped = {c["id"]: (c, False) for c in cases}
    mapped.update({c["id"]: (c, True) for c in old_cases() + fresh_cases()})
    replay = []
    for row in rows:
        if row["arm"] != "R3":
            continue
        case, legacy = mapped[row["case"]]
        bundle = legacy_bundle(case) if legacy else bundle_for(case, "C0", probes=False)
        add_observations(bundle)
        prefix = f"R3-{row['case']}-r1-"
        first = calls[prefix + "review"]
        second = calls.get(prefix + "verify") or calls.get(prefix + "empty")
        try:
            result = (
                verified_result(second["raw"], first["raw"], bundle)
                if second["phase"] == "verify"
                else validate_empty_review(second["raw"], bundle)
            )
            replay.append(
                {
                    "case": row["case"],
                    "valid": True,
                    "issue_count": len(result["issues"]),
                    "checks": [i["suggestion_check"] for i in result["issues"]],
                    "current_input_matches": digest(bundle.payload) == first["input_hash"],
                    "current_system_matches": digest(
                        compose(bundle.payload, ReviewOutput.model_json_schema())[0]
                    )
                    == first["system_hash"],
                }
            )
        except ValueError:
            replay.append({"case": row["case"], "valid": False})
    ledger = json.loads((root / "usage.json").read_text(encoding="utf-8"))
    used = sum(a["run"] == "quality-lab-20260929" for a in ledger["attempts"])
    batch_count = sum(
        str(a.get("key", "")).startswith("quality-repair-20260929:") for a in ledger["attempts"]
    )
    summary = {
        "batch_calls": batch_count,
        "campaign_used": used,
        "campaign_remaining": 5000 - used,
        "total_used": len(ledger["attempts"]),
        "results": len(rows),
        "comparisons": comparisons,
        "failed_provider_calls": sum(c["status"] != "RECEIVED" for c in calls.values()),
        "observed_input_tokens": sum(c.get("input_tokens", 0) for c in calls.values()),
        "observed_output_tokens": sum(c.get("output_tokens", 0) for c in calls.values()),
        "ledger_sha256": digest(ledger),
    }
    save(batch / "summary.json", summary)
    save(batch / "postprocessing-replay.json", replay)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    report(parser.parse_args().root)
