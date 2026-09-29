"""Capped follow-up of known claim failures with a locked public/synthetic corpus."""

import argparse
import asyncio
import json
import os
import time
from pathlib import Path

from app.domain.review.empty_review import EmptyReviewOutput, validate_empty_review
from app.domain.review.harness import compose, compose_empty_review, compose_verification, documents
from app.domain.review.policy import PROMPT, SECRET, ReviewOutput, validate_result
from app.domain.review.provider import DeepSeekProvider
from app.domain.review.refinement import add_observations, verified_result
from app.domain.review.verification import verification_payload
from app.shared.config.settings import Settings
from scripts.quality_lab_bridge import legacy_bundle, old_cases
from scripts.quality_lab_protocol import bundle_for, digest, grade
from scripts.quality_lab_runner import Ledger, StopCampaign, stamp
from scripts.quality_repair_fresh import cases as fresh_cases
from scripts.stabilize_review_quality import save

BATCH = "claim-repair-20260929"
CAP = 240


class Evaluation:
    def __init__(self, root, arm, *, batch=BATCH, cap=CAP, additional_cases=()):
        self.batch, self.cap = batch, cap
        self.root, self.arm = root / batch, arm
        self.ledger = Ledger(root)
        self.settings = Settings()
        self.provider = DeepSeekProvider(self.settings)
        self.failures = 0
        self.cases = (
            [
                (c, False)
                for c in json.loads(
                    Path("evals/quality-lab-20260929/corpus.json").read_text(encoding="utf-8")
                )
            ]
            + [(c, True) for c in old_cases() + fresh_cases()]
            + list(additional_cases)
        )
        for folder in ["calls", "results"]:
            (self.root / folder).mkdir(parents=True, exist_ok=True)
        config = {
            "harness": PROMPT,
            "documents": documents(),
            "case_hash": digest(self.cases),
            "model": self.provider.model,
            "budget": self.provider.max_output_tokens,
            "reasoning": self.provider.reasoning_effort,
            "cap": self.cap,
            "concurrency": 4,
            "implementation": {
                p: digest(Path(p).read_text(encoding="utf-8"))
                for p in [
                    "app/domain/review/output_schema.py",
                    "app/domain/review/verification.py",
                    "app/domain/review/policy.py",
                    "app/domain/review/refinement.py",
                    "app/domain/review/semantics.py",
                    "app/domain/review/path_observations.py",
                    "app/domain/review/grounded_claims.py",
                ]
            },
        }
        path = self.root / f"{arm}-config.json"
        if path.exists() and json.loads(path.read_text(encoding="utf-8")) != config:
            raise ValueError("CONFIG_CHANGED_USE_NEW_ARM")
        save(path, config)

    @property
    def count(self):
        return sum(
            str(a.get("key", "")).startswith(self.batch + ":") for a in self.ledger.data["attempts"]
        )

    async def call(self, key, phase, payload, system):
        path = self.root / "calls" / (key + ".json")
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        if self.count >= self.cap or self.failures >= 6:
            raise StopCampaign("CLAIM_REPAIR_LIMIT")
        record = {
            "key": key,
            "phase": phase,
            "at": stamp(),
            "input_hash": digest(payload),
            "system_hash": digest(system),
        }
        if not self.ledger.reserve(self.batch + ":" + key, self.arm, phase):
            return {**record, "status": "INTERRUPTED_UNKNOWN"}
        start = time.monotonic()
        try:
            raw, incoming, outgoing = await self.provider.invoke(system, payload)
            if len(raw.encode()) > 24000 or SECRET.search(raw):
                raise ValueError("UNSAFE_OUTPUT")
            record.update(status="RECEIVED", raw=raw, input_tokens=incoming, output_tokens=outgoing)
        except Exception as exc:
            record.update(status="FAILED", error=type(exc).__name__)
            self.failures += 1
        record["seconds"] = round(time.monotonic() - start, 3)
        save(path, record)
        print(
            json.dumps({"calls": self.count, "phase": phase, "status": record["status"]}),
            flush=True,
        )
        return record

    async def task(self, case, legacy, repeat):
        key = f"{self.arm}-{case['id']}-r{repeat}"
        path = self.root / "results" / (key + ".json")
        if path.exists():
            return
        bundle = legacy_bundle(case) if legacy else bundle_for(case, "C0", probes=False)
        source_hash = digest(bundle.payload)
        add_observations(bundle)
        first = await self.call(
            key + "-review",
            "review",
            bundle.payload,
            compose(bundle.payload, ReviewOutput.model_json_schema())[0],
        )
        result, error, recovered = None, None, False
        try:
            if first["status"] != "RECEIVED":
                raise ValueError("FIRST_PROVIDER_FAILED")
            raw = first["raw"]
            try:
                draft = validate_result(raw, bundle)
            except ValueError:
                draft, recovered = None, True
            phase = "verify" if draft and (draft["issues"] or draft["questions"]) else "empty"
            payload = (
                verification_payload(bundle.payload, raw) if phase == "verify" else bundle.payload
            )
            system = (
                compose_verification(payload)
                if phase == "verify"
                else compose_empty_review(payload, EmptyReviewOutput.model_json_schema())
            )
            second = await self.call(key + "-" + phase, phase, payload, system)
            if second["status"] != "RECEIVED":
                raise ValueError("SECOND_PROVIDER_FAILED")
            result = (
                verified_result(second["raw"], raw, bundle)
                if phase == "verify"
                else validate_empty_review(second["raw"], bundle)
            )
        except Exception as exc:
            error = (
                str(exc) if type(exc) is ValueError and str(exc).isupper() else type(exc).__name__
            )
        paths = {path: fid for fid, (path, _) in bundle.anchors.items()}
        normalized = (
            {
                "issues": [
                    {**i, "file_id": paths[i["file_path"]]}
                    for i in result["issues"] + result["questions"]
                ]
            }
            if result
            else None
        )
        metrics = grade(case, normalized)
        # Preserve the historical strict primary-line score, but also record causal
        # evidence anchors: the visible write can be primary while the alias is evidence.
        evidence_hit = bool(normalized) and any(
            item["basis"] == "SUPPORTED"
            and item["file_id"] == "f1"
            and bool(set(item.get("evidence_lines", [])) & set(case["expected_lines"]))
            for item in normalized["issues"]
        )
        metrics["evidence_location_hit"] = evidence_hit
        metrics["evidence_miss"] = not case["fixed"] and not evidence_hit
        save(
            path,
            {
                "case": case["id"],
                "repeat": repeat,
                "arm": self.arm,
                "metrics": metrics,
                "result": result,
                "error": error,
                "recovered": recovered,
                "source_hash": source_hash,
            },
        )


async def run(args):
    lock = args.root / "running.lock"
    with lock.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps({"pid": os.getpid(), "batch": BATCH, "at": stamp()}))
    try:
        exp = Evaluation(args.root, args.arm)
        selected = exp.cases
        if args.phase == "focused":
            families = {"zero-step", "int-overflow"}
            selected = [
                (c, old)
                for c, old in exp.cases
                if c.get("family") in families or c.get("legacy_id") in {"ca-before", "ca-after"}
            ]
            if len(selected) != 6:
                raise ValueError("FOCUS_SELECTION_MISMATCH")
        queue = asyncio.Queue()
        for c, old in selected:
            for repeat in range(1, 4) if args.phase == "focused" else [1]:
                queue.put_nowait((c, old, repeat))

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
            "miss": sum(r["metrics"]["miss"] for r in rows),
            "false_positive": sum(r["metrics"]["normal_false_positive"] for r in rows),
            "errors": [r["error"] for r in rows if r["error"]],
        }
        save(exp.root / f"{args.arm}-summary.json", summary)
        print(json.dumps(summary), flush=True)
    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--arm", choices=["C1", "C2", "C3", "C4"], default="C1")
    parser.add_argument("--phase", choices=["focused", "regression"], required=True)
    parser.add_argument("--execute", action="store_true", required=True)
    asyncio.run(run(parser.parse_args()))
