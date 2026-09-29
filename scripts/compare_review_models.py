"""Paired Flash/Pro regression evaluation, charged to the existing approved campaign."""

import argparse
import asyncio
import copy
import json
import os
import random
import time
from pathlib import Path

import httpx
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_deepseek import ChatDeepSeek
from langsmith import tracing_context

from app.domain.review.harness import documents
from app.shared.config.settings import Settings
from scripts.quality_lab_bridge import old_cases
from scripts.quality_lab_bridge import task as product_task
from scripts.quality_lab_protocol import (
    LabOutput,
    bundle_for,
    digest,
    grade,
    review_system,
    validate,
)
from scripts.quality_lab_rescore import ALIASES
from scripts.quality_lab_runner import CORPUS, Ledger, StopCampaign, stamp
from scripts.stabilize_review_quality import save

BATCH = "model-comparison-20260929"
LIMIT = 480
MODELS = {"F0": "deepseek-flash", "P0": "deepseek-v4-pro"}


def score(case, output):
    adjusted = copy.deepcopy(output)
    for probe in (adjusted or {}).get("probes", []):
        probe["exception_type"] = ALIASES.get(probe["exception_type"], probe["exception_type"])
    return grade(case, adjusted)


def response_metadata(response):
    """Allowlist usage only: never persist reasoning_content or arbitrary provider metadata."""
    usage = dict(response.usage_metadata or {})
    raw = response.response_metadata.get("token_usage") or {}
    cached = raw.get("prompt_cache_hit_tokens")
    if cached is None:
        cached = (usage.get("input_token_details") or {}).get("cache_read")
    result = {
        "input_tokens": int(usage.get("input_tokens", 0)),
        "output_tokens": int(usage.get("output_tokens", 0)),
        "response_model": response.response_metadata.get("model_name"),
        "finish_reason": response.response_metadata.get("finish_reason"),
    }
    if isinstance(cached, int) and 0 <= cached <= result["input_tokens"]:
        result["cached_input_tokens"] = cached
    return result


class MeasuredProvider:
    def __init__(self, settings):
        self.settings = settings

    async def invoke(self, model_id, system, payload):
        if not self.settings.ai_enabled or not self.settings.deepseek_api_key:
            raise ValueError("AI_DISABLED")
        async with httpx.AsyncClient(trust_env=False, follow_redirects=False, timeout=60) as http:
            model = ChatDeepSeek(
                model_name=model_id,
                api_key=self.settings.deepseek_api_key,
                api_base="https://api.deepseek.com",
                temperature=0,
                max_tokens=2000,
                timeout=60,
                max_retries=0,
                http_async_client=http,
            ).bind(
                response_format={"type": "json_object"},
                extra_body={"thinking": {"type": "disabled"}},
            )
            with tracing_context(enabled=False):
                async with asyncio.timeout(60):
                    response = await model.ainvoke(
                        [SystemMessage(content=system), HumanMessage(content=payload)],
                        config={"callbacks": []},
                    )
        return response.content, response_metadata(response)


async def discover(root):
    (root / BATCH).mkdir(parents=True, exist_ok=True)
    settings = Settings()
    if not settings.deepseek_api_key:
        raise ValueError("AI_DISABLED")
    async with httpx.AsyncClient(trust_env=False, follow_redirects=False, timeout=30) as http:
        response = await http.get(
            "https://api.deepseek.com/models",
            headers={"Authorization": "Bearer " + settings.deepseek_api_key.get_secret_value()},
        )
        response.raise_for_status()
        rows = response.json()["data"]
    models = [
        {k: row[k] for k in ("id", "name", "context_window", "max_output_tokens") if k in row}
        for row in rows
        if row.get("id") in MODELS.values()
    ]
    if set(MODELS.values()) - {r["id"] for r in models}:
        raise ValueError("MODEL_UNAVAILABLE")
    save(root / BATCH / "model-discovery.json", {"at": stamp(), "models": models})
    print(json.dumps({"models": models}), flush=True)


class Comparison:
    def __init__(self, root, provider=None):
        self.root = root / BATCH
        for folder in ("calls", "results"):
            (self.root / folder).mkdir(parents=True, exist_ok=True)
        self.ledger = Ledger(root)
        self.provider = provider or MeasuredProvider(Settings())
        self.semaphore = asyncio.Semaphore(4)
        self.stop = False
        self.failures = 0
        raw = (CORPUS / "corpus.json").read_text(encoding="utf-8")
        manifest = json.loads((CORPUS / "manifest.json").read_text(encoding="utf-8"))
        if digest(raw) != manifest["sha256"]:
            raise ValueError("CORPUS_CHANGED")
        self.cases = json.loads(raw)
        self.legacy = old_cases()
        config = {
            "batch": BATCH,
            "models": MODELS,
            "maximum_calls": LIMIT,
            "corpus_digest": digest(raw),
            "legacy_digest": digest(self.legacy),
            "harness_digest": digest(documents()),
            "protocol_digests": {
                p: digest(Path(p).read_text(encoding="utf-8"))
                for p in (
                    "scripts/quality_lab_protocol.py",
                    "scripts/quality_lab_bridge.py",
                    "scripts/compare_review_models.py",
                )
            },
            "temperature": 0,
            "thinking": "disabled",
            "max_output_tokens": 2000,
            "timeout_seconds": 60,
            "concurrency": 4,
            "automatic_retries": 0,
            "repeats": 2,
            "cases_previously_seen": True,
            "exception_aliases": ALIASES,
        }
        path = self.root / "configuration.json"
        if path.exists() and json.loads(path.read_text(encoding="utf-8")) != config:
            raise ValueError("EXPERIMENT_CONFIGURATION_CHANGED")
        save(path, config)

    @property
    def count(self):
        return sum(a.get("key", "").startswith(BATCH + ":") for a in self.ledger.data["attempts"])

    async def call(self, key, arm, phase, system, payload, schema, case, bundle):
        path = self.root / "calls" / (key + ".json")
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        async with self.semaphore:
            if self.stop or self.count >= LIMIT:
                raise StopCampaign("BATCH_STOPPED_OR_EXHAUSTED")
            if not self.ledger.reserve(BATCH + ":" + key, arm, phase):
                record = {"key": key, "status": "INTERRUPTED_UNKNOWN", "output": None}
                save(path, record)
                return record
            record = {
                "key": key,
                "arm": arm,
                "phase": phase,
                "case": case["id"],
                "at": stamp(),
                "model": MODELS[arm],
                "system_sha256": digest(system),
                "payload_sha256": digest(payload),
                "status": "STARTED",
                "output": None,
            }
            save(path, record)
            started = time.monotonic()
            try:
                raw, metadata = await self.provider.invoke(MODELS[arm], system, payload)
                record.update(metadata)
                if not isinstance(raw, str):
                    raise ValueError("INVALID_OUTPUT")
                record["response_sha256"] = digest(raw)
                if metadata["finish_reason"] != "stop":
                    raise ValueError("OUTPUT_TRUNCATED")
                record.update(status="COMPLETED", output=validate(raw, schema, case, bundle))
                self.failures = 0
            except Exception as exc:
                status = getattr(exc, "status_code", None)
                record.update(
                    status="FAILED",
                    error_class=type(exc).__name__,
                    http_status=status if isinstance(status, int) else None,
                )
                if str(exc) in {"AI_DISABLED", "INVALID_OUTPUT", "OUTPUT_TRUNCATED"}:
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
            if self.count % 20 == 0 or record["status"] != "COMPLETED":
                print(
                    json.dumps({"batch_calls": self.count, "key": key, "status": record["status"]}),
                    flush=True,
                )
            return record

    async def diagnostic(self, case, arm, repeat):
        key = f"diagnostic-{arm}-{case['id']}-r{repeat}"
        path = self.root / "results" / (key + ".json")
        if path.exists():
            return
        bundle = bundle_for(case)
        record = await self.call(
            key,
            arm,
            "diagnostic",
            review_system(bundle, "C0"),
            bundle.payload,
            LabOutput,
            case,
            bundle,
        )
        output = record.get("output")
        save(
            path,
            {
                "key": key,
                "case": case["id"],
                "arm": arm,
                "repeat": repeat,
                "split": "diagnostic",
                "output": output,
                "metrics": score(case, output),
                "original_strict_metrics": grade(case, output),
                "pipeline_complete": record["status"] == "COMPLETED",
                "stages": 1,
                **{
                    k: record.get(k, 0)
                    for k in ("input_tokens", "output_tokens", "elapsed_seconds")
                },
            },
        )

    def jobs(self, smoke=False):
        if smoke:
            return [("diagnostic", self.cases[i], a, 1, False) for i in (0, 1) for a in MODELS]
        pairs = [("diagnostic", c, r, False) for c in self.cases for r in (1, 2)]
        pairs += [("bridge", c, r, False) for c in self.cases for r in (1, 2)]
        pairs += [("bridge", c, r, True) for c in self.legacy for r in (1, 2)]
        rng = random.Random(20260929)
        rng.shuffle(pairs)
        jobs = []
        for kind, case, repeat, legacy in pairs:
            arms = list(MODELS)
            rng.shuffle(arms)
            jobs.extend((kind, case, a, repeat, legacy) for a in arms)
        return jobs

    async def run(self, smoke=False):
        queue = asyncio.Queue()
        for job in self.jobs(smoke):
            queue.put_nowait(job)

        async def worker():
            while not queue.empty() and not self.stop:
                kind, case, arm, repeat, legacy = queue.get_nowait()
                if kind == "diagnostic":
                    await self.diagnostic(case, arm, repeat)
                else:
                    await product_task(self, case, arm, repeat, legacy)
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
    if args.mode == "models":
        await discover(args.root)
        return
    lock = args.root / "running.lock"
    with lock.open("x", encoding="utf-8") as file:
        file.write(json.dumps({"batch": BATCH, "pid": os.getpid(), "at": stamp()}))
    try:
        await Comparison(args.root).run(smoke=args.mode == "smoke")
    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--mode", choices=("models", "smoke", "all"), required=True)
    parser.add_argument("--execute", action="store_true", required=True)
    try:
        asyncio.run(main(parser.parse_args()))
    except Exception as exc:
        print(
            json.dumps(
                {"fatal": type(exc).__name__, "http_status": getattr(exc, "status_code", None)}
            ),
            flush=True,
        )
        raise SystemExit(1) from None
