"""Offline replay: re-validate stored model outputs with the current validators. No API calls."""

import argparse
import json
from pathlib import Path
from typing import Any

from app.domain.review.empty_review import validate_empty_review
from app.domain.review.policy import prepare
from app.domain.review.refinement import add_observations
from scripts.review_accuracy_evaluation import load, score


def replay(cases: list[dict[str, Any]], records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return records where failed empty-recheck outputs are validated by the current code."""
    by_id = {c["id"]: c for c in cases}
    out: list[dict[str, Any]] = []
    for item in records:
        if (
            item["status"] == "FAILED"
            and item.get("error_stage") == "empty_recheck"
            and item.get("checked_raw")
        ):
            case = by_id[item["id"]]
            bundle = prepare([{"filename": case["path"], "patch": case["patch"]}], [], [], 1)
            add_observations(bundle)
            try:
                result = validate_empty_review(item["checked_raw"], bundle)
            except ValueError as error:
                out.append({**item, "replay_error": str(error)[:80]})
                continue
            out.append({**item, "status": "COMPLETED", "result": result, "replayed": True})
        else:
            out.append(item)
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus", type=Path)
    parser.add_argument("runs", nargs="+", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    cases, records = load(args.corpus, args.runs)
    replayed = replay(cases, records)
    report = {
        "recorded": score(cases, records),
        "after_current_validators": score(cases, replayed),
        "replayed_items": sum(bool(i.get("replayed")) for i in replayed),
        "still_invalid": sum("replay_error" in i for i in replayed),
    }
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
