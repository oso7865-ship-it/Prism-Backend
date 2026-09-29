"""Check current two-call production review path without diagnostic probe scaffolding."""

import argparse
import asyncio
import json
import os

from app.domain.review.empty_review import EmptyReviewOutput, validate_empty_review
from app.domain.review.harness import compose, compose_empty_review, compose_verification
from app.domain.review.policy import ReviewOutput, prepare, validate_result
from app.domain.review.verification import (
    VerificationOutput,
    apply_verification,
    verification_payload,
)
from scripts.quality_lab_protocol import GUIDANCE, bundle_for, digest, grade
from scripts.quality_lab_runner import CAMPAIGN, Experiment, stamp
from scripts.stabilize_review_quality import save


def old_cases():
    from pathlib import Path

    path = Path("evals/recall-repair/core-v2.json")
    cases = json.loads(path.read_text(encoding="utf-8"))
    for case in cases:
        case["legacy_id"] = case["id"]
        case["id"] = digest(case["id"])[:12]
        case["fixed"] = not case["expected_locations"]
        case["oracle"] = []
        case["expected_lines"] = [n for a, b in case["expected_locations"] for n in range(a, b + 1)]
    return cases


def legacy_bundle(case):
    bundle = prepare([{"filename": case["path"], "patch": case["patch"]}], [], [], 1)
    data = json.loads(bundle.payload)
    data["behavior_contract"] = case["contract"]
    bundle.payload = json.dumps(data, ensure_ascii=False)
    return bundle


async def task(exp, case, arm, repeat, legacy=False):
    key = f"bridge-{arm}-{case['id']}-r{repeat}"
    path = exp.root / "results" / (key + ".json")
    if path.exists():
        return
    bundle = legacy_bundle(case) if legacy else bundle_for(case, arm, probes=False)
    system, _ = compose(bundle.payload, ReviewOutput.model_json_schema())
    if arm != "C0":
        system += "\n" + GUIDANCE.get(arm, "")
    first = await exp.call(
        key + "-draft", arm, "product_draft", system, bundle.payload, ReviewOutput, case, bundle
    )
    records = [first]
    final = None
    draft = None
    normalized = None
    verification = None
    error = None
    try:
        if first.get("output") is not None:
            raw = json.dumps(first["output"], ensure_ascii=False)
            checked = validate_result(raw, bundle)
            draft = first["output"]
            if checked["issues"] or checked["questions"]:
                payload = verification_payload(bundle.payload, raw)
                second = await exp.call(
                    key + "-verify",
                    arm,
                    "product_verify",
                    compose_verification(payload),
                    payload,
                    VerificationOutput,
                    case,
                    bundle,
                )
                records.append(second)
                if second.get("output") is not None:
                    revised, verification = apply_verification(
                        json.dumps(second["output"], ensure_ascii=False), raw
                    )
                    normalized = validate_result(revised, bundle)
                    final = json.loads(revised)
            else:
                second = await exp.call(
                    key + "-empty",
                    arm,
                    "product_empty",
                    compose_empty_review(bundle.payload, EmptyReviewOutput.model_json_schema()),
                    bundle.payload,
                    EmptyReviewOutput,
                    case,
                    bundle,
                )
                records.append(second)
                if second.get("output") is not None:
                    normalized = validate_empty_review(
                        json.dumps(second["output"], ensure_ascii=False), bundle
                    )
                    final = {k: v for k, v in second["output"].items() if k != "file_checks"}
                    verification = normalized["verification"]
    except Exception as exc:
        error = type(exc).__name__
    metrics = grade(case, final)
    metrics.update(probe_total=0, probe_correct=0)
    before = grade(case, draft)
    save(
        path,
        {
            "key": key,
            "case": case["id"],
            "arm": arm,
            "split": "bridge",
            "repeat": repeat,
            "legacy_id": case.get("legacy_id"),
            "legacy_seen_before": legacy,
            "metrics": metrics,
            "draft_metrics": before,
            "verifier_induced_miss": before["location_hit"] and not metrics["location_hit"],
            "output": final,
            "normalized": normalized,
            "verification": verification,
            "validation_error": error,
            "stages": len(records),
            "pipeline_complete": final is not None
            and all(r["status"] == "COMPLETED" for r in records),
            "input_tokens": sum(r.get("input_tokens", 0) for r in records),
            "output_tokens": sum(r.get("output_tokens", 0) for r in records),
            "elapsed_seconds": sum(r.get("elapsed_seconds", 0) for r in records),
        },
    )


async def run(args):
    lock = args.root / "running.lock"
    with lock.open("x", encoding="utf-8") as file:
        file.write(json.dumps({"campaign": CAMPAIGN, "pid": os.getpid(), "at": stamp()}))
    try:
        exp = Experiment(args.root)
        # A product-compatible one-call draft candidate, selected on development only.
        selection_path = exp.root / "bridge-selection.json"
        if selection_path.exists():
            arms = json.loads(selection_path.read_text(encoding="utf-8"))["arms"]
        else:
            table = exp.aggregate("development")
            eligible = [
                a for a in ("E03", "E04", "E05", "E12") if table.get(a, {}).get("cases") == 40
            ]

            def score(arm):
                t = table[arm]
                return (
                    t["miss"],
                    t["normal_false_positive"],
                    t["invalid"] + t["incomplete"],
                    t["probe_total"] - t["probe_correct"],
                    t["calls"],
                    arm,
                )

            arms = ["C0", min(eligible, key=score)]
            save(
                selection_path,
                {
                    "arms": arms,
                    "at": stamp(),
                    "development_digest": digest(table),
                    "rule": "Development only; single draft call candidates.",
                },
            )
        jobs = [(c, a, 1, False) for c in exp.cases for a in arms]
        # Previously exposed minimal public reproductions: regression, NOT held-out evidence.
        jobs += [(c, "C0", r, True) for c in old_cases() for r in (1, 2)]
        queue = asyncio.Queue()
        for job in jobs:
            queue.put_nowait(job)

        async def worker():
            while not queue.empty() and not exp.stop:
                await task(exp, *queue.get_nowait())
                queue.task_done()

        await asyncio.gather(*(worker() for _ in range(4)))
        exp.aggregate("bridge")
        print(json.dumps({"campaign_calls": exp.ledger.count, "bridge_arms": arms}), flush=True)
    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--execute", action="store_true", required=True)
    asyncio.run(run(parser.parse_args()))
