"""Capped, resumable repair comparison using synthetic/public reproductions only."""

import argparse
import asyncio
import importlib.util
import json
import os
import random
import sys
import time
from pathlib import Path

from app.domain.review.dictionary_observations import dictionary_facts
from app.domain.review.empty_review import EmptyReviewOutput, validate_empty_review
from app.domain.review.harness import compose, compose_empty_review, compose_verification, documents
from app.domain.review.policy import PROMPT, SECRET, ReviewOutput, validate_result
from app.domain.review.provider import DeepSeekProvider
from app.domain.review.refinement import add_observations, needs_reasoning, verified_result
from app.domain.review.verification import (
    VerificationOutput,
    apply_verification,
    verification_payload,
)
from app.shared.config.settings import Settings
from scripts.quality_lab_bridge import legacy_bundle, old_cases
from scripts.quality_lab_protocol import bundle_for, digest, grade
from scripts.quality_lab_runner import Ledger, StopCampaign, stamp
from scripts.quality_repair_fresh import cases as fresh_cases
from scripts.quality_repair_provider import ResponsesCandidate
from scripts.stabilize_review_quality import save

BATCH = "quality-repair-20260929"
LIMIT = 600
LANGUAGES = {
    "java": "java",
    "py": "python",
    "js": "javascript",
    "jsx": "javascript",
    "ts": "typescript",
    "tsx": "typescript",
}


def load_own_snapshot(path, name):
    # This is our trusted server snapshot, NOT a repository under analysis or a fixture.
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def freeze_baseline(path):
    directory = Path("audit-artifacts") / BATCH / "baseline"
    policy = load_own_snapshot(directory / "policy.py", "repair_baseline_policy")
    verification = load_own_snapshot(directory / "verification.py", "repair_baseline_verification")
    file_check = load_own_snapshot(directory / "empty_schema.py", "repair_baseline_file_check")
    schema = policy.ReviewOutput.model_json_schema()
    empty = json.loads(json.dumps(schema))
    empty["$defs"]["FileCheck"] = file_check.FileCheck.model_json_schema()
    empty["properties"]["file_checks"] = {
        "items": {"$ref": "#/$defs/FileCheck"},
        "minItems": 1,
        "maxItems": 8,
        "type": "array",
    }
    empty["required"].append("file_checks")
    value = {
        "modules": {
            p.stem: p.read_text(encoding="utf-8") for p in (directory / "harness").glob("*.prompt")
        },
        "review": schema,
        "verify": verification.VerificationOutput.model_json_schema(),
        "empty": empty,
    }
    save(path, value)
    return value


def baseline_system(baseline, phase, payload):
    data = json.loads(payload)
    data = data.get("context", data)
    languages = sorted({LANGUAGES[f["language"]] for f in data["files"]})
    modules = ["core", "checks"]
    modules += (
        ["output", *languages]
        if phase == "review"
        else [
            *languages,
            "verification" if phase == "verify" else "empty_review",
        ]
    )
    if data.get("purpose") in {"SECURITY", "STANDARDS"}:
        modules += [data["purpose"].lower()]
    return (
        "\n\n".join(baseline["modules"][m] for m in modules)
        + "\n\nJSON schema: "
        + json.dumps(
            baseline[phase],
            sort_keys=True,
            ensure_ascii=False,
        )
    )


class RepairEvaluation:
    def __init__(self, root, revision=1):
        self.root = root / BATCH
        for name in ["calls", "results"]:
            (self.root / name).mkdir(parents=True, exist_ok=True)
        self.ledger = Ledger(root)
        path = self.root / "baseline.json"
        self.baseline = (
            json.loads(path.read_text(encoding="utf-8")) if path.exists() else freeze_baseline(path)
        )
        self.cases = json.loads(
            Path("evals/quality-lab-20260929/corpus.json").read_text(encoding="utf-8")
        )
        self.legacy = old_cases()
        self.settings = Settings().model_copy(update={"deepseek_model": "deepseek-flash"})
        self.failures = 0
        self.stop = False
        config = {
            "revision": 1,
            "harness": PROMPT,
            "modules": digest(documents()),
            "baseline": digest(self.baseline),
            "cases": digest(self.cases + self.legacy),
            "cap": LIMIT,
            "model": "deepseek-flash",
            "concurrency": 4,
            "arms": {
                "B0": "frozen original two-call path",
                "R1": "recovery contract",
                "R2": "recovery + bounded operation observations",
                "J1": "R2 Responses JSON schema",
                "T0": "R2 4000 nonthinking",
                "T1": "R2 conditional high reasoning 4000",
                "T2": "R2 conditional high reasoning 2000",
            },
        }
        if revision >= 2:
            config["revision"] = revision
            config["arms"]["R3"] = "R2 + exact dictionary expression observations"
            config["dictionary_observations"] = digest(
                Path("app/domain/review/dictionary_observations.py").read_text(encoding="utf-8")
            )
        if revision == 3:
            config["fresh_cases"] = digest(fresh_cases())
            save(self.root / "fresh-cases.json", fresh_cases())
        path = self.root / ("config.json" if revision == 1 else f"config-r{revision}.json")
        if path.exists() and json.loads(path.read_text(encoding="utf-8")) != config:
            raise ValueError("REPAIR_CONFIGURATION_CHANGED")
        save(path, config)

    @property
    def count(self):
        return sum(
            str(a.get("key", "")).startswith(BATCH + ":") for a in self.ledger.data["attempts"]
        )

    async def call(self, key, arm, phase, system, payload, schema):
        path = self.root / "calls" / (key + ".json")
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        if self.count >= LIMIT:
            raise StopCampaign("REPAIR_CAP")
        record = {
            "key": key,
            "arm": arm,
            "phase": phase,
            "at": stamp(),
            "input_hash": digest(payload),
            "system_hash": digest(system),
        }
        if not self.ledger.reserve(BATCH + ":" + key, arm, phase):
            return {**record, "status": "INTERRUPTED_UNKNOWN"}
        provider = (
            ResponsesCandidate(self.settings) if arm == "J1" else DeepSeekProvider(self.settings)
        )
        if phase != "review" and arm in {"T0", "T1", "T2"}:
            provider.max_output_tokens = 2000 if arm == "T2" else 4000
            provider.reasoning_effort = "high" if arm != "T0" and needs_reasoning(payload) else None
        started = time.monotonic()
        record.update(budget=provider.max_output_tokens, reasoning=provider.reasoning_effort)
        try:
            if arm == "J1":
                raw, incoming, outgoing = await provider.structured(system, payload, schema)
            else:
                raw, incoming, outgoing = await provider.invoke(system, payload)
            if len(raw.encode()) > 24000 or SECRET.search(raw):
                raise ValueError("UNSAFE_OUTPUT")
            record.update(status="RECEIVED", raw=raw, input_tokens=incoming, output_tokens=outgoing)
        except Exception as exc:
            # Never persist provider exception text, headers, key or reasoning.
            record.update(status="FAILED", error=type(exc).__name__)
            self.failures += 1
            if self.failures >= 8:
                self.stop = True
        record["seconds"] = round(time.monotonic() - started, 3)
        save(path, record)
        print(
            json.dumps(
                {"calls": self.count, "arm": arm, "phase": phase, "status": record["status"]}
            ),
            flush=True,
        )
        return record

    async def task(self, case, arm, legacy):
        key = f"{arm}-{case['id']}-r1"
        path = self.root / "results" / (key + ".json")
        if path.exists():
            return
        bundle = legacy_bundle(case) if legacy else bundle_for(case, "C0", probes=False)
        source_hash = digest(bundle.payload)
        if arm not in {"B0", "R1"}:
            add_observations(bundle)
        if arm == "R3":
            facts = dictionary_facts(bundle.payload)
            if facts:
                data = json.loads(bundle.payload)
                data["semantic_observations"] = [
                    f
                    for f in data.get("semantic_observations", [])
                    if (f["file_id"], f["line"]) not in {(x["file_id"], x["line"]) for x in facts}
                ] + facts
                bundle.payload = json.dumps(data, ensure_ascii=False)
        schema = ReviewOutput.model_json_schema()
        system = (
            baseline_system(self.baseline, "review", bundle.payload)
            if arm == "B0"
            else compose(bundle.payload, schema)[0]
        )
        first = await self.call(key + "-review", arm, "review", system, bundle.payload, schema)
        result, error, recovered = None, None, False
        try:
            if first["status"] != "RECEIVED":
                raise ValueError("FIRST_PROVIDER_FAILED")
            raw = first["raw"]
            try:
                draft = validate_result(raw, bundle)
            except ValueError:
                if arm == "B0":
                    raise
                draft, recovered = None, True
            phase = "verify" if draft and (draft["issues"] or draft["questions"]) else "empty"
            payload = (
                verification_payload(bundle.payload, raw) if phase == "verify" else bundle.payload
            )
            schema = (
                VerificationOutput.model_json_schema()
                if phase == "verify"
                else EmptyReviewOutput.model_json_schema()
            )
            system = (
                baseline_system(self.baseline, phase, payload)
                if arm == "B0"
                else (
                    compose_verification(payload)
                    if phase == "verify"
                    else compose_empty_review(payload, schema)
                )
            )
            second = await self.call(key + "-" + phase, arm, phase, system, payload, schema)
            if second["status"] != "RECEIVED":
                raise ValueError("SECOND_PROVIDER_FAILED")
            if phase == "verify":
                if arm == "B0":
                    revised, _ = apply_verification(second["raw"], raw)
                    result = validate_result(revised, bundle)
                else:
                    result = verified_result(second["raw"], raw, bundle)
            else:
                if arm == "B0":
                    checks = json.loads(second["raw"])["file_checks"]
                    files = {f["file_id"]: f for f in json.loads(bundle.payload)["files"]}
                    for check in checks:
                        allowed = {
                            r["line"] for r in files[check["file_id"]]["lines"] if r["changed"]
                        }
                        if check["line"] not in (allowed or bundle.anchors[check["file_id"]][1]):
                            raise ValueError("LEGACY_FILE_CHECK_LINE")
                result = validate_empty_review(second["raw"], bundle)
        except Exception as exc:
            error = (
                str(exc) if type(exc) is ValueError and str(exc).isupper() else type(exc).__name__
            )
        by_path = {path: fid for fid, (path, _) in bundle.anchors.items()}
        normalized = (
            {
                "issues": [
                    {**item, "file_id": by_path[item["file_path"]]}
                    for item in result["issues"] + result["questions"]
                ]
            }
            if result
            else None
        )
        metrics = grade(case, normalized)
        metrics.update(probe_total=0, probe_correct=0)
        save(
            path,
            {
                "case": case["id"],
                "arm": arm,
                "metrics": metrics,
                "result": result,
                "error": error,
                "recovered": recovered,
                "source_hash": source_hash,
            },
        )

    async def run(self, phase):
        cases = [(c, False) for c in self.cases] + [(c, True) for c in self.legacy]
        if phase == "smoke":
            selected = [
                (c, legacy)
                for c, legacy in cases
                if c["id"] in {"4c612348a604", "5e22872c605b", "e039b4bf0e2d", "4cf224cd4371"}
            ]
            arms = ["B0", "R1", "R2"]
        elif phase == "fresh":
            selected, arms = [(c, True) for c in fresh_cases()], ["B0", "R3"]
        elif phase == "targeted":
            selected, arms = cases, ["R3"]
        elif phase == "main":
            selected, arms = cases, ["B0", "R1", "R2"]
        else:
            selected = [
                (c, legacy)
                for c, legacy in cases
                if legacy
                or c.get("family") in {"zero-step", "nested-copy", "int-overflow", "null-branch"}
            ]
            # Use deterministic IDs if corpus labels use alternate family names.
            selected = [
                (c, legacy)
                for c, legacy in cases
                if legacy
                or c["id"]
                in {
                    "4c612348a604",
                    "5e22872c605b",
                    "0c47bb65c1ee",
                    "898c474a9d7d",
                    "2cdf3efa43ff",
                    "0add10c208ec",
                    "90900a02e0f4",
                    "cd210310faa4",
                }
            ]
            arms = ["J1"] if phase == "schema" else ["T0", "T1", "T2"]
        jobs = [(c, arm, legacy) for c, legacy in selected for arm in arms]
        random.Random(20260929).shuffle(jobs)
        queue = asyncio.Queue()
        for job in jobs:
            queue.put_nowait(job)

        async def worker():
            while not queue.empty() and not self.stop:
                await self.task(*queue.get_nowait())
                queue.task_done()

        await asyncio.gather(*(worker() for _ in range(4)))
        print(
            json.dumps(
                {
                    "batch_calls": self.count,
                    "campaign_calls": self.ledger.count,
                    "stopped": self.stop,
                }
            ),
            flush=True,
        )


async def main(args):
    lock = args.root / "running.lock"
    with lock.open("x", encoding="utf-8") as file:
        file.write(json.dumps({"batch": BATCH, "pid": os.getpid(), "at": stamp()}))
    try:
        revision = 3 if args.phase == "fresh" else 2 if args.phase == "targeted" else 1
        await RepairEvaluation(args.root, revision=revision).run(args.phase)
    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument(
        "--phase",
        choices=["smoke", "main", "schema", "reasoning", "targeted", "fresh"],
        required=True,
    )
    parser.add_argument("--execute", action="store_true", required=True)
    try:
        asyncio.run(main(parser.parse_args()))
    except Exception as exc:
        print(json.dumps({"fatal": type(exc).__name__}), flush=True)
        raise SystemExit(1) from None
