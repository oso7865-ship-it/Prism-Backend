"""Predeclared second-wave tests of documentation grounding and issue-emission consistency."""

import argparse
import asyncio
import json
import os
from pathlib import Path

from scripts.quality_lab_protocol import LabOutput, bundle_for, digest, grade, review_system
from scripts.quality_lab_runner import CAMPAIGN, Experiment, stamp
from scripts.stabilize_review_quality import save

REFERENCE = {
    "language": "Python",
    "scope": "built-in operations, not overloaded user objects",
    "facts": [
        "range(start, stop, step) uses the supplied step, not an implicit replacement. "
        "With positive step, terms are start + step*i for nonnegative i while below stop. "
        "A zero step raises ValueError, even if the interval would be empty.",
        "max(a, b) selects the larger argument. It is not min(a, b).",
        "Default argument objects are created when the function is defined and reused "
        "when that argument is omitted in later calls.",
        "A copied list is a separate container. Appending later to the original list "
        "does not append to an earlier list copy; a shallow copy still shares nested objects.",
        "Boolean or returns its left operand when truthy, otherwise its right operand. "
        "Falsy values and None are not interchangeable under an explicit None-only contract.",
    ],
    "sources": [
        "https://docs.python.org/3/library/stdtypes.html#ranges",
        "https://docs.python.org/3/library/functions.html#max",
        "https://docs.python.org/3/tutorial/controlflow.html#default-argument-values",
    ],
    "provenance": "Official references checked 2026-09-29; manually paraphrased generic facts.",
}
CONSISTENCY = (
    "Before emitting an issue, distinguish actual source behavior from required behavior. "
    "An issue needs a concrete reachable condition where they differ, or a cited rule violation. "
    "Do not emit an issue that says the code satisfies its contract or requires no change. "
    "Do not turn an absence of a test into proof of a bug. Preserve every source-supported defect, "
    "including defects whose fix is not yet known. Check that summary, consequence, suggestion "
    "and probe predictions do not contradict each other. Return only the requested schema; "
    "this does not ask for hidden reasoning or extra explanation fields."
)


async def task(exp, case, arm, repeat):
    split = "adaptive_" + case["split"]
    key = f"{split}-{arm}-{case['id']}-r{repeat}"
    path = exp.root / "results" / (key + ".json")
    if path.exists():
        return
    bundle = bundle_for(case)
    if arm == "E14" and case["path"].endswith(".py"):
        payload = json.loads(bundle.payload)
        payload["supporting_language_reference"] = REFERENCE
        bundle.payload = json.dumps(payload, ensure_ascii=False)
    system = review_system(bundle, "C0")
    if arm == "E15":
        system += "\n" + CONSISTENCY
    record = await exp.call(
        key + "-final", arm, "adaptive_final", system, bundle.payload, LabOutput, case, bundle
    )
    output = record.get("output")
    save(
        path,
        {
            "key": key,
            "case": case["id"],
            "arm": arm,
            "split": split,
            "repeat": repeat,
            "metrics": grade(case, output),
            "output": output,
            "stages": 1,
            "pipeline_complete": record["status"] == "COMPLETED",
            "input_tokens": record.get("input_tokens", 0),
            "output_tokens": record.get("output_tokens", 0),
            "elapsed_seconds": record.get("elapsed_seconds", 0),
        },
    )


async def run(args):
    lock = args.root / "running.lock"
    with lock.open("x", encoding="utf-8") as file:
        file.write(json.dumps({"campaign": CAMPAIGN, "pid": os.getpid(), "at": stamp()}))
    try:
        exp = Experiment(args.root)
        protocol = {
            "source_digest": digest(Path(__file__).read_text(encoding="utf-8")),
            "reference": REFERENCE,
            "consistency": CONSISTENCY,
            "arms": ["E14", "E15"],
            "repeats": 2,
            "calls": 144,
            "hypothesis": (
                "Generic operator facts may improve observations; "
                "consistency may reduce non-issues."
            ),
            "selection": (
                "Both arms frozen before first held-out model response; "
                "no adaptive winner selection."
            ),
        }
        path = exp.root / "adaptive-configuration.json"
        if path.exists() and json.loads(path.read_text(encoding="utf-8")) != protocol:
            raise ValueError("ADAPTIVE_CONFIGURATION_CHANGED")
        save(path, protocol)
        for split in ("development", "holdout"):
            queue = asyncio.Queue()
            for case in exp.cases:
                if case["split"] == split:
                    for arm in ("E14", "E15"):
                        for repeat in (1, 2):
                            queue.put_nowait((case, arm, repeat))

            async def worker():
                while not queue.empty() and not exp.stop:
                    await task(exp, *queue.get_nowait())
                    queue.task_done()

            await asyncio.gather(*(worker() for _ in range(4)))
            exp.aggregate("adaptive_" + split)
        print(json.dumps({"campaign_calls": exp.ledger.count}), flush=True)
    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--execute", action="store_true", required=True)
    asyncio.run(run(parser.parse_args()))
