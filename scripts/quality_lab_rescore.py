"""Auditable scoring erratum: fully qualified standard exceptions equal short names."""

import argparse
import copy
import json
from pathlib import Path

from scripts.quality_lab_protocol import grade
from scripts.quality_lab_runner import CAMPAIGN
from scripts.stabilize_review_quality import save

ALIASES = {
    "java.lang.NullPointerException": "NullPointerException",
    "builtins.ValueError": "ValueError",
    "builtins.ZeroDivisionError": "ZeroDivisionError",
}


def rescore(root):
    cases = {
        c["id"]: c
        for c in json.loads(
            Path("evals/quality-lab-20260929/corpus.json").read_text(encoding="utf-8")
        )
    }
    changed = []
    for path in sorted((root / CAMPAIGN / "results").glob("*.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        if row["split"] == "bridge" or row["case"] not in cases:
            continue
        output = copy.deepcopy(row["output"])
        if output:
            for probe in output["probes"]:
                probe["exception_type"] = ALIASES.get(
                    probe["exception_type"], probe["exception_type"]
                )
        new_metrics = grade(cases[row["case"]], output)
        row.setdefault("original_strict_metrics", row["metrics"])
        if new_metrics != row["original_strict_metrics"]:
            changed.append(row["key"])
        row["metrics"] = new_metrics
        row["scoring_revision"] = "standard-exception-aliases-1"
        save(path, row)
    save(
        root / CAMPAIGN / "scoring-erratum.json",
        {
            "revision": "standard-exception-aliases-1",
            "aliases": ALIASES,
            "reason": (
                "Fully qualified Java/Python built-in exception names are semantically identical."
            ),
            "preservation": (
                "Original raw outputs and strict metrics retained. No model calls or input edits."
            ),
            "changed_rows": changed,
        },
    )
    print(json.dumps({"rescored_alias_rows": len(changed)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    rescore(args.root)
