"""Bounded predeployment semantic regression on authored fixtures; no project code execution."""

import argparse
import asyncio
import json
import os
from pathlib import Path

from scripts.claim_repair_evaluation import Evaluation
from scripts.final_quality_cases import cases as final_cases
from scripts.quality_lab_runner import stamp
from scripts.stabilize_review_quality import save

BATCH = "predeployment-hardening-20260929"


async def run(args):
    lock = args.root / "running.lock"
    with lock.open("x", encoding="utf-8") as file:
        file.write(json.dumps({"pid": os.getpid(), "batch": BATCH, "at": stamp()}))
    try:
        exp = Evaluation(args.root, args.arm, batch=BATCH, cap=640,
                         additional_cases=[(c, False) for c in final_cases()])
        selected = exp.cases if args.phase == "regression" else [
            (c, old) for c, old in exp.cases if c.get("family") in {"path-boundary", "nested-copy"}
        ]
        if args.phase == "focused" and len(selected) != 4:
            raise ValueError("FOCUS_SELECTION_MISMATCH")
        queue = asyncio.Queue()
        for case, old in selected:
            for repeat in range(1, 4) if args.phase == "focused" else [1]:
                queue.put_nowait((case, old, repeat))
        async def worker():
            while not queue.empty():
                await exp.task(*queue.get_nowait())
        await asyncio.gather(*(worker() for _ in range(4)))
        rows = [json.loads(p.read_text(encoding="utf-8"))
                for p in (exp.root / "results").glob(args.arm + "-*.json")]
        summary = {
            "arm": args.arm, "phase": args.phase, "calls": exp.count,
            "evaluations": len(rows), "valid": sum(r["metrics"]["valid"] for r in rows),
            "miss": sum(r["metrics"]["miss"] for r in rows),
            "false_positive": sum(r["metrics"]["normal_false_positive"] for r in rows),
            "evidence_miss": sum(r["metrics"].get("evidence_miss", r["metrics"]["miss"]) for r in rows),
            "errors": [r["error"] for r in rows if r["error"]],
        }
        save(exp.root / f"{args.arm}-{args.phase}-summary.json", summary)
        print(json.dumps(summary), flush=True)
    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--arm", required=True)
    parser.add_argument("--phase", choices=["focused", "regression"], required=True)
    parser.add_argument("--execute", action="store_true", required=True)
    asyncio.run(run(parser.parse_args()))
