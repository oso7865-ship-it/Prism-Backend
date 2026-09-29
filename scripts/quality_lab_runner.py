"""Resumable, capped paid experiments on authored synthetic source only."""

import argparse
import asyncio
import json
import os
import random
import time
from datetime import UTC, datetime
from pathlib import Path

from app.domain.review.harness import documents
from app.domain.review.policy import PROMPT
from app.domain.review.provider import DeepSeekProvider
from app.shared.config.settings import Settings
from scripts.quality_lab_protocol import (
    ARMS,
    REVISION,
    LabOutput,
    Notes,
    ProbeReport,
    Selection,
    auxiliary_system,
    bundle_for,
    digest,
    grade,
    review_system,
    validate,
)
from scripts.stabilize_review_quality import save

CAMPAIGN = "quality-lab-20260929"
START = 1563
MINIMUM = 1000
MAXIMUM = 5000
CORPUS = Path("evals/quality-lab-20260929")


def stamp():
    return datetime.now(UTC).isoformat()


class StopCampaign(Exception):
    pass


class Ledger:
    def __init__(self, root):
        self.path = root / "usage.json"
        self.data = json.loads(self.path.read_text(encoding="utf-8"))
        self.count = sum(a["run"] == CAMPAIGN for a in self.data["attempts"])
        if len(self.data["attempts"]) - self.count != START:
            raise ValueError("LEDGER_BASELINE_CHANGED")
        if self.data["limit"] == 3000 and self.count == 0:
            self.data["limit"] = START + MAXIMUM
            self.data.setdefault("authorizations", []).append(
                {
                    "campaign": CAMPAIGN,
                    "previous_attempts": START,
                    "minimum": MINIMUM,
                    "maximum_new_attempts": MAXIMUM,
                    "absolute_limit": START + MAXIMUM,
                    "recorded_at": stamp(),
                    "user_authorization": (
                        "1천회 넘어도 괜찮아 최대 5천회까지 승인해주며 최소 1천회로 잡아"
                    ),
                }
            )
            save(self.path, self.data)
        if self.data["limit"] != START + MAXIMUM:
            raise ValueError("AUTHORIZATION_MISMATCH")

    def reserve(self, key, arm, phase):
        if self.count >= MAXIMUM or len(self.data["attempts"]) >= self.data["limit"]:
            raise StopCampaign("BUDGET_EXHAUSTED")
        if any(a.get("key") == key for a in self.data["attempts"]):
            return False
        self.data["attempts"].append(
            {"run": CAMPAIGN, "key": key, "experiment": arm, "phase": phase, "reserved_at": stamp()}
        )
        # Synchronous fsync + atomic replace, before any await or network request.
        save(self.path, self.data)
        self.count += 1
        return True


class Experiment:
    def __init__(self, root, provider=None):
        self.root = root / CAMPAIGN
        self.root.mkdir(exist_ok=True)
        (self.root / "calls").mkdir(exist_ok=True)
        (self.root / "results").mkdir(exist_ok=True)
        self.ledger = Ledger(root)
        self.provider = provider or DeepSeekProvider(Settings())
        self.semaphore = asyncio.Semaphore(4)
        self.stop = False
        self.failures = 0
        raw = (CORPUS / "corpus.json").read_text(encoding="utf-8")
        manifest = json.loads((CORPUS / "manifest.json").read_text(encoding="utf-8"))
        if digest(raw) != manifest["sha256"]:
            raise ValueError("CORPUS_CHANGED")
        self.cases = json.loads(raw)
        configuration = {
            "revision": REVISION,
            "corpus": manifest,
            "model": self.provider.model,
            "harness": PROMPT,
            "harness_digest": digest(documents()),
            "protocol_digest": digest(
                Path("scripts/quality_lab_protocol.py").read_text(encoding="utf-8")
            ),
            "temperature": 0,
            "normal_output_tokens": 2000,
            "E12_output_tokens": 8192,
            "concurrency": 4,
            "automatic_retries": 0,
            "selection_order": [
                "miss",
                "normal_false_positive",
                "invalid",
                "probe_errors",
                "calls",
            ],
        }
        path = self.root / "configuration.json"
        if path.exists() and json.loads(path.read_text(encoding="utf-8")) != configuration:
            raise ValueError("EXPERIMENT_CONFIGURATION_CHANGED")
        save(path, configuration)

    async def call(self, key, arm, phase, system, payload, schema, case, bundle):
        path = self.root / "calls" / (key + ".json")
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        async with self.semaphore:
            if self.stop:
                raise StopCampaign("CIRCUIT_BREAKER")
            if not self.ledger.reserve(key, arm, phase):
                lost = {
                    "key": key,
                    "status": "INTERRUPTED_UNKNOWN",
                    "output": None,
                    "reason": "Reserved before interruption; not repeated automatically.",
                }
                save(path, lost)
                return lost
            record = {
                "key": key,
                "arm": arm,
                "phase": phase,
                "at": stamp(),
                "system_sha256": digest(system),
                "payload_sha256": digest(payload),
                "input_bytes": len(payload.encode()),
                "status": "STARTED",
                "output": None,
                "model": self.provider.model,
                "reasoning": "low" if arm == "E12" else "disabled",
            }
            save(path, record)
            started = time.monotonic()
            try:
                provider = self.provider
                if arm == "E12":
                    provider = DeepSeekProvider(self.provider.settings)
                    provider.reasoning_effort = "low"
                    provider.max_output_tokens = 8192
                raw, incoming, outgoing = await provider.invoke(system, payload)
                record.update(
                    response_sha256=digest(raw), input_tokens=incoming, output_tokens=outgoing
                )
                output = validate(raw, schema, case, bundle)
                record.update(status="COMPLETED", output=output)
                self.failures = 0
            except Exception as exc:
                # Only safe diagnostic metadata; no provider response/error body or credentials.
                status = getattr(exc, "status_code", None)
                record.update(
                    status="FAILED",
                    error_class=type(exc).__name__,
                    http_status=status if isinstance(status, int) else None,
                )
                if str(exc) in {
                    "OUTPUT_TRUNCATED",
                    "AI_DISABLED",
                    "PROBE_IDS",
                    "PROBE_RETURN",
                    "PROBE_RAISE",
                    "PROBE_UNKNOWN",
                    "INVALID_OUTPUT",
                }:
                    record["error_code"] = str(exc)
                if hasattr(exc, "errors"):
                    record["schema_errors"] = [
                        {"type": e["type"], "loc": e["loc"]} for e in exc.errors()
                    ][:8]
                self.failures += 1
                if status in (401, 402, 403) or self.failures >= 12:
                    self.stop = True
            record["elapsed_seconds"] = round(time.monotonic() - started, 3)
            save(path, record)
            if self.ledger.count % 10 == 0 or record["status"] != "COMPLETED":
                print(
                    json.dumps(
                        {
                            "calls": self.ledger.count,
                            "key": key,
                            "status": record["status"],
                            "error": record.get("error_code"),
                        }
                    ),
                    flush=True,
                )
            return record

    async def task(self, case, arm, repeat, split):
        key = f"{split}-{arm}-{case['id']}-r{repeat}"
        result_path = self.root / "results" / (key + ".json")
        if result_path.exists():
            return
        bundle = bundle_for(case, arm)
        records = []

        async def invoke(phase, schema=LabOutput, guidance_arm=None, independent=None):
            system = (
                auxiliary_system(guidance_arm, schema)
                if guidance_arm
                else review_system(bundle, arm, independent=independent)
            )
            result = await self.call(
                f"{key}-{phase}", arm, phase, system, bundle.payload, schema, case, bundle
            )
            records.append(result)
            return result.get("output")

        if arm in ("E02", "E06", "E07", "E08", "E11"):
            data = json.loads(bundle.payload)
            if arm == "E02":
                data["evidence_manifest"] = [
                    {"id": "contract", "description": "Expected behavior and accepted input types"},
                    {
                        "id": "related",
                        "description": "Implementation of functions called by changed code",
                    },
                ]
                bundle.payload = json.dumps(data, ensure_ascii=False)
            schema = Selection if arm == "E02" else ProbeReport if arm == "E06" else Notes
            notes = await invoke("observe", schema, arm)
            if arm == "E02":
                for requested in (notes or {}).get("request_ids", []):
                    data[
                        "behavior_contract" if requested == "contract" else "related_implementation"
                    ] = case["contract"] if requested == "contract" else case["extra"]
            else:
                data["untrusted_observations"] = notes
            bundle.payload = json.dumps(data, ensure_ascii=False)
        elif arm in ("E09", "E10"):
            first = await invoke("draft1", independent=1 if arm == "E10" else None)
            second = await invoke("draft2", independent=2) if arm == "E10" else None
            data = json.loads(bundle.payload)
            data["untrusted_drafts"] = [d for d in [first, second] if d is not None]
            bundle.payload = json.dumps(data, ensure_ascii=False)
        output = await invoke("final")
        result = {
            "key": key,
            "case": case["id"],
            "arm": arm,
            "split": split,
            "repeat": repeat,
            "metrics": grade(case, output),
            "output": output,
            "stages": len(records),
            "pipeline_complete": all(r["status"] == "COMPLETED" for r in records),
            "input_tokens": sum(r.get("input_tokens", 0) for r in records),
            "output_tokens": sum(r.get("output_tokens", 0) for r in records),
            "elapsed_seconds": round(sum(r.get("elapsed_seconds", 0) for r in records), 3),
        }
        save(result_path, result)

    def aggregate(self, split):
        rows = [
            json.loads(p.read_text(encoding="utf-8"))
            for p in sorted((self.root / "results").glob(f"{split}-*.json"))
        ]
        table = {}
        for row in rows:
            entry = table.setdefault(
                row["arm"],
                {
                    k: 0
                    for k in [
                        "cases",
                        "bugs",
                        "miss",
                        "normal_false_positive",
                        "questions",
                        "invalid",
                        "incomplete",
                        "probe_correct",
                        "probe_total",
                        "calls",
                        "input_tokens",
                        "output_tokens",
                        "elapsed_seconds",
                    ]
                },
            )
            m = row["metrics"]
            entry["cases"] += 1
            entry["bugs"] += m["expected_bug"]
            for field in [
                "miss",
                "normal_false_positive",
                "questions",
                "probe_correct",
                "probe_total",
            ]:
                entry[field] += m[field]
            entry["invalid"] += not m["valid"]
            entry["incomplete"] += not row["pipeline_complete"]
            entry["calls"] += row["stages"]
            for field in ["input_tokens", "output_tokens", "elapsed_seconds"]:
                entry[field] += row[field]
        save(self.root / (split + "-summary.json"), table)
        return table

    def select(self):
        path = self.root / "selection.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))["arms"]
        table = self.aggregate("development")
        if any(table.get(arm, {}).get("cases") != 40 for arm in ARMS):
            raise ValueError("DEVELOPMENT_INCOMPLETE")
        eligible = [arm for arm in ARMS if arm not in ("C0", "E01a", "E01b", "E01c", "E13")]

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

        selected = ["C0", *sorted(eligible, key=score)[:2]]
        save(
            path,
            {
                "at": stamp(),
                "arms": selected,
                "development_digest": digest(table),
                "rule": (
                    "lexicographic miss, normal FP, invalid+incomplete, probe errors, calls, ID"
                ),
            },
        )
        return selected

    async def run(self, mode):
        if mode == "smoke":
            jobs = [(self.cases[0], "C0", 1, "development")]
        else:
            split = "holdout" if mode == "holdout" else "development"
            arms = self.select() if split == "holdout" else ARMS
            cases = [c for c in self.cases if c["split"] == split]
            jobs = [(c, arm, repeat, split) for repeat in (1, 2) for c in cases for arm in arms]
            random.Random(20260929).shuffle(jobs)
        # Four worker tasks bound memory and avoid a giant queue of active HTTP requests.
        queue = asyncio.Queue()
        for job in jobs:
            queue.put_nowait(job)

        async def worker():
            while not queue.empty() and not self.stop:
                job = queue.get_nowait()
                await self.task(*job)
                queue.task_done()

        await asyncio.gather(*(worker() for _ in range(4)))
        for split in ("development", "holdout"):
            self.aggregate(split)
        print(json.dumps({"campaign_calls": self.ledger.count, "stopped": self.stop}), flush=True)


async def main(args):
    lock = args.root / "running.lock"
    with lock.open("x", encoding="utf-8") as file:
        file.write(json.dumps({"campaign": CAMPAIGN, "pid": os.getpid(), "at": stamp()}))
    try:
        experiment = Experiment(args.root)
        await experiment.run(args.mode)
    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--mode", choices=["smoke", "development", "holdout"], required=True)
    parser.add_argument("--execute", action="store_true", required=True)
    asyncio.run(main(parser.parse_args()))
