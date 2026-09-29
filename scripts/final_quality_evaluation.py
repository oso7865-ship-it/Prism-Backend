"""Paired contract checks plus existing regressions, sharing the authorized call ledger."""

import argparse
import asyncio
import json
import os
from pathlib import Path

from scripts.claim_repair_evaluation import Evaluation
from scripts.final_quality_cases import cases
from scripts.quality_lab_runner import StopCampaign, stamp
from scripts.stabilize_review_quality import save

BATCH = "final-validation-20260929"
CAP = 388  # Reserve another 12 of the planned 400 for product end-to-end requests.


async def run(args):
    lock = args.root / "running.lock"
    with lock.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps({"pid": os.getpid(), "batch": BATCH, "at": stamp()}))
    try:
        authored = cases()
        exp = Evaluation(
            args.root,
            args.arm,
            batch=BATCH,
            cap=CAP,
            additional_cases=[(c, False) for c in authored],
        )
        save(exp.root / "authored-cases.json", authored)
        if args.phase == "focus":
            selected = [
                (c, old)
                for c, old in exp.cases
                if c.get("family") == "nested-copy" or c.get("family", "").startswith("contract-")
            ]
            repeats = range(1, 3)
        elif args.phase == "fresh":
            selected = [(c, False) for c in authored]
            repeats = [1]
        else:
            selected = exp.cases[:54]
            repeats = [1]
        queue = asyncio.Queue()
        for case, old in selected:
            for repeat in repeats:
                queue.put_nowait((case, old, repeat))

        async def worker():
            while not queue.empty():
                try:
                    await exp.task(*queue.get_nowait())
                except StopCampaign:
                    return

        await asyncio.gather(*(worker() for _ in range(4)))
        rows = [
            json.loads(p.read_text(encoding="utf-8"))
            for p in (exp.root / "results").glob(args.arm + "-*.json")
        ]
        summary = {
            "arm": args.arm,
            "calls": exp.count,
            "evaluations": len(rows),
            "valid": sum(r["metrics"]["valid"] for r in rows),
            "bugs": sum(r["metrics"]["expected_bug"] for r in rows),
            "miss": sum(r["metrics"]["miss"] for r in rows),
            "false_positive": sum(r["metrics"]["normal_false_positive"] for r in rows),
            "questions": sum(r["metrics"]["questions"] for r in rows),
            "errors": [r["error"] for r in rows if r["error"]],
        }
        save(exp.root / f"{args.arm}-summary.json", summary)
        print(json.dumps(summary), flush=True)
    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--arm", choices=["F0", "F1", "F2", "F3"], required=True)
    parser.add_argument("--phase", choices=["focus", "fresh", "regression"], required=True)
    parser.add_argument("--execute", action="store_true", required=True)
    asyncio.run(run(parser.parse_args()))
