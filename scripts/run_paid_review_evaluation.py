"""Explicitly authorized, bounded synthetic evaluation; never retry paid calls."""

import argparse
import asyncio
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from app.domain.review.harness import compose
from app.domain.review.harness.evaluation import score
from app.domain.review.policy import POLICY, PROMPT, Issue, ReviewOutput, prepare, validate_result
from app.domain.review.provider import DeepSeekProvider
from app.shared.config.settings import Settings


def load_cases(max_calls: int) -> list[dict]:
    if max_calls not in (7, 10):
        raise ValueError("Only the fixed seven or ten case evaluation is supported")
    cases = json.loads(Path("evals/review-harness/cases.json").read_text(encoding="utf-8"))
    if max_calls == 10:
        cases += json.loads(
            Path("evals/review-harness/experience-cases.json").read_text(encoding="utf-8")
        )
    if len(cases) != max_calls or len({case["id"] for case in cases}) != max_calls:
        raise ValueError("Unexpected number of unique synthetic cases")
    return cases


async def run(output: Path, max_calls: int = 7) -> bool:
    cases = load_cases(max_calls)
    settings = Settings()
    provider = DeepSeekProvider(settings)
    record = {
        "started_at": datetime.now(UTC).isoformat(),
        "model": provider.model,
        "max_calls": max_calls,
        "prompt_version": PROMPT,
        "policy_version": POLICY,
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
        except ValidationError as error:
            fields = set(ReviewOutput.model_fields) | set(Issue.model_fields) | {"questions"}
            item["status"], item["error_type"] = "FAILED", "ValidationError"
            # Keep only schema identifiers/types, never raw values or exception messages.
            item["validation_errors"] = [
                {
                    "type": problem["type"],
                    "location": [
                        part if isinstance(part, int) or part in fields else "<unknown-field>"
                        for part in problem["loc"]
                    ],
                }
                for problem in error.errors(include_input=False, include_context=False)[:10]
            ]
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
    budget = parser.add_mutually_exclusive_group(required=True)
    budget.add_argument("--allow-seven-paid-calls", action="store_true")
    budget.add_argument("--allow-ten-paid-calls", action="store_true")
    args = parser.parse_args()
    raise SystemExit(
        0 if asyncio.run(run(args.output, 10 if args.allow_ten_paid_calls else 7)) else 1
    )
