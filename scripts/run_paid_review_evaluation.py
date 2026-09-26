"""Explicitly authorized, bounded synthetic evaluation; never retry paid calls."""

import argparse
import asyncio
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from app.domain.review.harness import compose
from app.domain.review.harness.evaluation import score
from app.domain.review.policy import ReviewOutput, prepare, validate_result
from app.domain.review.provider import DeepSeekProvider
from app.shared.config.settings import Settings


async def run(output: Path) -> bool:
    cases = json.loads(Path("evals/review-harness/cases.json").read_text(encoding="utf-8"))
    if len(cases) != 7 or len({case["id"] for case in cases}) != 7:
        raise ValueError("Expected exactly seven unique synthetic cases")
    settings = Settings()
    provider = DeepSeekProvider(settings)
    record = {
        "started_at": datetime.now(UTC).isoformat(),
        "model": provider.model,
        "max_calls": 7,
        "scope": "standalone synthetic evaluation, no application DB writes",
        "cases": [],
    }
    # Refuse an existing output: rerunning this command cannot silently pay again.
    with output.open("x", encoding="utf-8") as file:
        json.dump(record, file, ensure_ascii=False, indent=2)
    for case in cases:
        bundle = prepare([{"filename": case["path"], "patch": case["patch"]}], [], [], 1)
        _, metadata = compose(bundle.payload, ReviewOutput.model_json_schema())
        item = {"id": case["id"], "harness": metadata, "status": "STARTED", "attempts": 1}
        record["cases"].append(item)
        output.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        start = time.monotonic()
        try:
            raw, incoming, outgoing = await provider.review(bundle.payload)
            item["usage"] = {"input_tokens": incoming, "output_tokens": outgoing}
            item["result"] = validate_result(raw, bundle)
            item["grade"] = score(case, json.loads(raw))
            item["status"] = "COMPLETED"
        except Exception as error:
            item["status"] = "FAILED"
            item["error_type"] = type(error).__name__
        item["duration_seconds"] = round(time.monotonic() - start, 3)
        output.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({k: v for k, v in item.items() if k != "result"}), flush=True)
    record["finished_at"] = datetime.now(UTC).isoformat()
    record["passed"] = all(item.get("grade", {}).get("passed") for item in record["cases"])
    output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return record["passed"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--allow-seven-paid-calls", action="store_true", required=True)
    args = parser.parse_args()
    raise SystemExit(0 if asyncio.run(run(args.output)) else 1)
