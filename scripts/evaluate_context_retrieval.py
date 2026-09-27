"""Identical-candidate local evaluation; optional explicitly bounded paid review comparison."""

import argparse
import asyncio
import base64
import hashlib
import json
import math
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote

from app.domain.review.context_selection import enrich
from app.domain.review.policy import POLICY, PROMPT, prepare, validate_result
from app.domain.review.provider import DeepSeekProvider
from app.domain.review.reranker import LocalReranker
from app.domain.review.retrieval import select
from app.shared.config.settings import Settings

CORPUS = Path("evals/context-retrieval/cases.json")
SAFE_ERRORS = {
    "AI_DISABLED",
    "INVALID_OUTPUT",
    "OUTPUT_TRUNCATED",
    "UNSUPPORTED_SEVERITY",
    "INVALID_OUTPUT_LOCATION",
    "INVALID_EVIDENCE_LINES",
    "INVALID_ASSUMPTIONS",
    "INCONSISTENT_EVIDENCE_BASIS",
    "EMPTY_EVIDENCE",
}


def error_details(error, stage):
    # Never persist arbitrary exception text: provider/validation errors can echo source.
    code = str(error)
    if type(error).__name__ == "ValidationError":
        code = "SCHEMA_VALIDATION"
    elif code not in SAFE_ERRORS:
        code = "UNCLASSIFIED_ERROR"
    return {"error_type": type(error).__name__, "error_code": code, "error_stage": stage}


class SyntheticGitHub:
    def __init__(self, files):
        self.files, self.calls = files, []

    async def request(self, method, path, token):
        self.calls.append(path)
        assert method == "GET" and "b" * 40 in path
        if "/git/commits/" in path:
            return {"tree": {"sha": "b" * 40}}
        if "/git/trees/" in path:
            return {"tree": [{"path": p, "type": "blob", "mode": "100644"} for p in self.files]}
        name = unquote(path.split("/contents/", 1)[1].split("?", 1)[0])
        raw = self.files[name].encode()
        return {
            "type": "file",
            "encoding": "base64",
            "size": len(raw),
            "content": base64.b64encode(raw).decode(),
        }


class CaptureRanker:
    def __init__(self, model):
        self.model = model
        self.pool = []
        self.query = ""
        self.order = []

    async def rank(self, query, candidates):
        self.query = query
        if self.model:
            order, meta = await LocalReranker().rank(query, candidates)
        else:
            order, meta = list(range(len(candidates))), {"mode": "rules"}
        indices = []
        for candidate in candidates:
            if candidate not in self.pool:
                self.pool.append(candidate)
            indices.append(self.pool.index(candidate))
        self.order.extend(indices[i] for i in order if indices[i] not in self.order)
        return order, meta


def grade(case, result):
    expected = set(case["expected_lines"])
    found = {i["line"] for i in result["issues"] if i["file_path"] == case["path"]}
    unexpected = sum(
        i["file_path"] != case["path"] or i["line"] not in expected
        for i in result["issues"] + result["questions"]
    )
    return {
        "missed": len(expected - found),
        "unexpected": unexpected,
        "passed": not expected - found and not unexpected,
    }


async def build(case, model=False):
    per_file, max_input = case.get("budget", [16384, 49152])
    if (per_file, max_input) not in {(8192, 24576), (16384, 49152)}:
        raise ValueError("INVALID_COMPARISON_BUDGET")
    bundle = prepare(
        [{"filename": case["path"], "patch": case["patch"]}],
        [],
        [],
        1,
        per_file=per_file,
        max_input=max_input,
    )
    capture = CaptureRanker(model)
    github = SyntheticGitHub(case["files"])
    started = time.monotonic()
    bundle = await enrich(
        bundle,
        github,
        "synthetic",
        "/repos/example/sample",
        "b" * 40,
        [],
        capture,
        per_file=per_file,
        max_input=max_input,
    )
    needed = case["required_context"]

    def relevant(candidate):
        return candidate.path == needed["path"] and set(needed["lines"]) <= set(candidate.numbers)

    selected = select(capture.pool, capture.order)
    # Candidate presence is separate from final payload presence after byte budgeting.
    data = json.loads(bundle.payload)
    included = any(
        bundle.anchors[f["file_id"]][0] == needed["path"]
        and set(needed["lines"]) <= {row["line"] for row in f["lines"]}
        for f in data["files"]
    )
    digest = hashlib.sha256(
        json.dumps(
            [(c.path, c.numbers, c.code, c.score) for c in capture.pool], ensure_ascii=False
        ).encode()
    ).hexdigest()
    return bundle, {
        "candidate_digest": digest,
        "candidate_count": len(capture.pool),
        "candidate_hit": any(relevant(c) for c in capture.pool),
        "selected_hit": included,
        "selected_paths": [c.path for c in selected],
        "input_bytes": len(bundle.payload.encode()),
        "retrieval_seconds": round(time.monotonic() - started, 4),
        "ranking": bundle.coverage.get("retrieval", {}),
        "github_reads": len(github.calls),
    }


async def run(output: Path, paid=False):
    cases = json.loads(CORPUS.read_text(encoding="utf-8"))
    if len(cases) != 12 or len({c["id"] for c in cases}) != 12:
        raise ValueError("FIXED_CORPUS_REQUIRED")
    record = {
        "started_at": datetime.now(UTC).isoformat(),
        "prompt_version": PROMPT,
        "policy_version": POLICY,
        "corpus_sha256": hashlib.sha256(CORPUS.read_bytes()).hexdigest(),
        "max_paid_calls": 24 if paid else 0,
        "cases": [],
    }
    with output.open("x", encoding="utf-8") as file:
        json.dump(record, file)

    def save():
        output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    provider = DeepSeekProvider(Settings()) if paid else None
    for case in cases:
        pair = {"id": case["id"], "arms": {}}
        record["cases"].append(pair)
        # Alternating order avoids always measuring the same arm first.
        modes = (False, True) if len(record["cases"]) % 2 else (True, False)
        bundles = {}
        for model in modes:
            bundle, metrics = await build(case, model)
            arm = "reranker" if model else "rules"
            bundles[arm] = bundle
            pair["arms"][arm] = metrics
            save()
            if model and metrics["ranking"].get("mode") != "local_reranker":
                raise ValueError("ACTUAL_MODEL_REQUIRED_FOR_COMPARISON")
        left, right = pair["arms"]["rules"], pair["arms"]["reranker"]
        if left["candidate_digest"] != right["candidate_digest"]:
            raise ValueError("CANDIDATE_SET_CHANGED")
        for model in modes:
            arm = "reranker" if model else "rules"
            bundle, metrics = bundles[arm], pair["arms"][arm]
            if provider:
                metrics["review"] = {"status": "STARTED", "attempts": 1}
                save()
                started = time.monotonic()
                stage = "provider"
                try:
                    raw, incoming, outgoing = await provider.review(bundle.payload)
                    metrics["review"].update(input_tokens=incoming, output_tokens=outgoing)
                    stage = "validation"
                    result = validate_result(raw, bundle)
                    metrics["review"].update(
                        status="COMPLETED",
                        input_tokens=incoming,
                        output_tokens=outgoing,
                        result=result,
                        grade=grade(case, result),
                    )
                except Exception as error:
                    metrics["review"].update(status="FAILED", **error_details(error, stage))
                metrics["review"]["seconds"] = round(time.monotonic() - started, 3)
                save()
        print(
            json.dumps(
                {
                    "id": case["id"],
                    "rules_hit": left["selected_hit"],
                    "reranker_hit": right["selected_hit"],
                    "same_candidates": True,
                }
            ),
            flush=True,
        )
    pairs = [c["arms"] for c in record["cases"]]
    latencies = sorted(p["reranker"]["ranking"]["duration_ms"] for p in pairs)
    rules_hits = sum(p["rules"]["selected_hit"] for p in pairs)
    ranked_hits = sum(p["reranker"]["selected_hit"] for p in pairs)
    regressions = sum(
        p["rules"]["selected_hit"] and not p["reranker"]["selected_hit"] for p in pairs
    )
    record["selection_gate"] = {
        "rules_hits": rules_hits,
        "reranker_hits": ranked_hits,
        "regressions": regressions,
        "observed_p95_ms": latencies[math.ceil(len(latencies) * 0.95) - 1],
        "passed": ranked_hits >= rules_hits + 2 and regressions == 0 and max(latencies) <= 2000,
    }
    record["finished_at"] = datetime.now(UTC).isoformat()
    save()
    print(json.dumps(record["selection_gate"]), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--allow-twenty-four-paid-calls", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.output, args.allow_twenty_four_paid_calls))
