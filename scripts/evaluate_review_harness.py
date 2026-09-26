"""Offline only: python scripts/evaluate_review_harness.py responses.json."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.domain.review.harness.evaluation import score  # noqa: E402

parser = argparse.ArgumentParser(description="Offline scorer; never calls DeepSeek")
parser.add_argument("responses", type=Path, help="JSON object: case id -> output object")
args = parser.parse_args()
cases = json.loads((ROOT / "evals/review-harness/cases.json").read_text(encoding="utf-8"))
responses = json.loads(args.responses.read_text(encoding="utf-8"))
results = [
    score(case, responses[case["id"]])
    if case["id"] in responses
    else {"id": case["id"], "valid": False, "passed": False, "missing": True}
    for case in cases
]
print(
    json.dumps(
        {"scope": "structural_and_expected_anchor_checks_only", "results": results},
        ensure_ascii=False,
        indent=2,
    )
)
raise SystemExit(0 if all(row["passed"] for row in results) else 1)
