"""Summarize paired regression measurements; do not infer semantic validity from location hits."""

import argparse
import json
import math
import statistics
from pathlib import Path

from scripts.compare_review_models import BATCH, MODELS
from scripts.quality_lab_runner import CAMPAIGN, MAXIMUM, stamp
from scripts.stabilize_review_quality import save

# Official 2026-09-29 rates, USD per million tokens; off-peak and peak (2x).
RATES = {"F0": (0.003, 0.15, 0.6), "P0": (0.022, 0.66, 1.98)}


def percentile(values, p):
    return sorted(values)[max(0, math.ceil(p * len(values)) - 1)] if values else None


def summarize(root):
    folder = root / BATCH
    rows = [json.loads(p.read_text(encoding="utf-8")) for p in (folder / "results").glob("*.json")]
    calls = [json.loads(p.read_text(encoding="utf-8")) for p in (folder / "calls").glob("*.json")]
    ledger = json.loads((root / "usage.json").read_text(encoding="utf-8"))
    attempts = [r for r in ledger["attempts"] if r.get("key", "").startswith(BATCH + ":")]
    summary = {
        "at": stamp(),
        "rows": len(rows),
        "requests_reserved": len(attempts),
        "calls_recorded": len(calls),
        "campaign_requests": sum(a["run"] == CAMPAIGN for a in ledger["attempts"]),
        "all_requests": len(ledger["attempts"]),
        "models": {},
        "results": {},
        "input_pairs_checked": 0,
        "input_pair_mismatches": [],
        "automatic_anomalies": [],
        "semantic_explanations_verified": False,
    }
    summary["campaign_remaining"] = MAXIMUM - summary["campaign_requests"]
    summary["unfinished_calls"] = [
        c["key"] for c in calls if c["status"] in ("STARTED", "INTERRUPTED_UNKNOWN")
    ]
    for arm, model in MODELS.items():
        cc = [c for c in calls if c["arm"] == arm]
        input_tokens = sum(c.get("input_tokens", 0) for c in cc)
        output_tokens = sum(c.get("output_tokens", 0) for c in cc)
        hit_tokens = sum(c.get("cached_input_tokens", 0) for c in cc)
        cached_rate, miss_rate, output_rate = RATES[arm]
        known = [c for c in cc if "cached_input_tokens" in c]
        unknown_input = sum(c.get("input_tokens", 0) for c in cc if c not in known)
        # Unknown cache uses both bounds; missing response usage doesn't mean zero billing.
        cheapest = (
            (hit_tokens + unknown_input) * cached_rate
            + (input_tokens - hit_tokens - unknown_input) * miss_rate
            + output_tokens * output_rate
        )
        highest = 2 * (
            hit_tokens * cached_rate
            + (input_tokens - hit_tokens) * miss_rate
            + output_tokens * output_rate
        )
        summary["models"][arm] = {
            "model": model,
            "calls": len(cc),
            "completed": sum(c["status"] == "COMPLETED" for c in cc),
            "failed": sum(c["status"] == "FAILED" for c in cc),
            "response_models": sorted({c["response_model"] for c in cc if c.get("response_model")}),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cached_input_tokens": hit_tokens,
            "missing_usage_calls": sum("input_tokens" not in c for c in cc),
            "cache_known_calls": len(known),
            "usd_lower_bound_known_usage": round(cheapest / 1_000_000, 6),
            "usd_upper_bound_known_usage": round(highest / 1_000_000, 6),
        }
        for section in ("diagnostic", "bridge", "bridge_new", "bridge_legacy"):
            rr = [
                r
                for r in rows
                if r["arm"] == arm
                and (
                    r["split"] == section
                    or (
                        section.startswith("bridge_")
                        and r["split"] == "bridge"
                        and r["legacy_seen_before"] == (section == "bridge_legacy")
                    )
                )
            ]
            timings = [r["elapsed_seconds"] for r in rr if r["pipeline_complete"]]
            metrics = {
                field: sum(int(r["metrics"][field]) for r in rr)
                for field in (
                    "expected_bug",
                    "miss",
                    "normal_false_positive",
                    "questions",
                    "probe_correct",
                    "probe_total",
                    "valid",
                    "location_hit",
                )
            }
            if section != "diagnostic":
                metrics.update(probe_correct=0, probe_total=0)
            metrics.update(
                cases=len(rr),
                expected_normal=len(rr) - metrics["expected_bug"],
                incomplete=sum(not r["pipeline_complete"] for r in rr),
                p50_seconds=round(statistics.median(timings), 3) if timings else None,
                p95_seconds=percentile(timings, 0.95),
            )
            summary["results"][section + "-" + arm] = metrics
    by_key = {c["key"]: c for c in calls}
    for call in calls:
        if call["arm"] != "F0" or call["phase"] not in ("diagnostic", "product_draft"):
            continue
        pair = by_key.get(call["key"].replace("-F0-", "-P0-"))
        if pair and "system_sha256" in call and "system_sha256" in pair:
            summary["input_pairs_checked"] += 1
            if any(call[k] != pair[k] for k in ("system_sha256", "payload_sha256")):
                summary["input_pair_mismatches"].append(call["key"])
    for row in rows:
        metrics = row["metrics"]
        if (
            metrics["miss"]
            or metrics["normal_false_positive"]
            or metrics["questions"]
            or not row["pipeline_complete"]
            or (row["split"] == "diagnostic" and metrics["probe_correct"] != metrics["probe_total"])
        ):
            summary["automatic_anomalies"].append({"key": row["key"], "metrics": metrics})
    summary["failed_calls"] = [
        {
            k: c[k]
            for k in ("key", "error_class", "error_code", "http_status", "schema_errors")
            if k in c
        }
        for c in calls
        if c["status"] == "FAILED"
    ]
    save(folder / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    summarize(parser.parse_args().root)
