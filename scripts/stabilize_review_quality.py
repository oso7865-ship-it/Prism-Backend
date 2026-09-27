"""Bounded synthetic evaluations with a durable shared authorization ledger. No retries."""

import argparse
import asyncio
import hashlib
import json
import os
import re
import time
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from app.domain.review.policy import POLICY, PROMPT, Issue, ReviewOutput, prepare, validate_result
from app.domain.review.provider import DeepSeekProvider
from app.domain.review.verification import (
    VerificationOutput,
    apply_verification,
    verification_payload,
)
from app.shared.config.settings import Settings
from scripts.evaluate_context_retrieval import build, error_details
from scripts.evaluation_thinking_provider import EvaluationThinkingProvider
from scripts.recall_evaluation import (
    DiagnosticProvider,
    FrozenBaselineProvider,
    quality_metrics,
    validate_diagnostic,
)

ROOT = Path("reports/quality-stabilization")
LIMIT = 3000  # User authorization, 2026-09-27. Product quotas are unchanged.


def grade(case, result):
    if "expected_locations" in case:
        locations = case["expected_locations"]
        findings = result["issues"]
        matches = [
            [
                i
                for i, finding in enumerate(findings)
                if finding["file_path"] == case["path"] and lo <= finding["line"] <= hi
            ]
            for lo, hi in locations
        ]
        missed = sum(not indices for indices in matches)
        unexpected = (
            len(result["questions"])
            + sum(sum(i in indices for indices in matches) != 1 for i in range(len(findings)))
            + sum(max(0, len(indices) - 1) for indices in matches)
        )
        return {
            "missed": missed,
            "unexpected": unexpected,
            "passed": missed == 0 and unexpected == 0,
            "scope": "location_only",
        }
    expected = set(case["expected_lines"])
    expected_questions = set(case.get("expected_questions", []))
    found = {i["line"] for i in result["issues"] if i["file_path"] == case["path"]}
    questions = {i["line"] for i in result["questions"] if i["file_path"] == case["path"]}
    unexpected = sum(
        i["file_path"] != case["path"] or i["line"] not in expected for i in result["issues"]
    ) + sum(
        i["file_path"] != case["path"] or i["line"] not in expected | expected_questions
        for i in result["questions"]
    )
    missed = len(expected - found) + len(expected_questions - questions)
    return {"missed": missed, "unexpected": unexpected, "passed": missed == 0 and unexpected == 0}


def save(path, value):
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def diagnostics(error, stage, raw, bundle):
    detail = error_details(error, stage)
    if isinstance(error, ValidationError):
        fields = set(ReviewOutput.model_fields) | set(Issue.model_fields) | {"questions"}
        detail["fields"] = [
            {
                "type": item["type"],
                "location": [
                    p if type(p) is int or p in fields else "<unknown-field>" for p in item["loc"]
                ],
            }
            for item in error.errors(include_input=False, include_context=False)[:10]
        ]
    # Only bounded numeric anchors and server-known IDs; never text or raw responses.
    if stage == "validation" and raw:
        try:
            response = json.loads(raw)
            files = {f["file_id"]: f for f in json.loads(bundle.payload)["files"]}
            anchors = []
            for item in response.get("issues", [])[:10]:
                fid = item.get("file_id")
                source = files.get(fid, {}) if isinstance(fid, str) else {}
                refs = item.get("evidence_lines", [])
                refs = [n for n in refs[:8] if type(n) is int and 0 <= n <= 1000000]
                line = item.get("line")
                valid = {r["line"] for r in source.get("lines", [])}
                changed = {r["line"] for r in source.get("lines", []) if r.get("changed")}
                anchors.append(
                    {
                        "file_id": fid if fid in files else "<unknown-file>",
                        "line": line if type(line) is int and 0 <= line <= 1000000 else None,
                        "evidence_lines": refs,
                        "unprovided": sorted(set(refs) - valid),
                        "has_changed_evidence": bool(set(refs) & changed),
                        "representative_in_evidence": line in refs,
                    }
                )
            detail["anchors"] = anchors
        except (TypeError, ValueError, AttributeError, KeyError):
            pass
    return detail


async def run(
    corpus: Path,
    name: str,
    repeats: int,
    max_calls: int,
    root=ROOT,
    *,
    thinking=False,
    verify=False,
    verify_drafts=False,
    baseline=False,
    diagnose=False,
):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", name):
        raise ValueError("INVALID_RUN_NAME")
    cases = json.loads(corpus.read_text(encoding="utf-8"))
    if not cases or len({c["id"] for c in cases}) != len(cases):
        raise ValueError("UNIQUE_CASES_REQUIRED")
    if verify_drafts and (not verify or any(not c.get("draft") for c in cases)):
        raise ValueError("VALIDATED_DRAFTS_REQUIRED")
    total = len(cases) * repeats * (2 if verify and not verify_drafts else 1)
    if thinking and verify:
        raise ValueError("COMPARISON_MODES_ARE_SEPARATE")
    if (baseline and (thinking or diagnose)) or (diagnose and (thinking or verify)):
        raise ValueError("COMPARISON_MODES_ARE_SEPARATE")
    if repeats < 1 or total != max_calls or not 1 <= total <= 100:
        raise ValueError("EXACT_BATCH_LIMIT_REQUIRED")
    root.mkdir(parents=True, exist_ok=True)
    lock = root / "running.lock"
    # Lock the entire run: a second process cannot race the usage reservation.
    with lock.open("x", encoding="utf-8") as stream:
        stream.write(name)
    try:
        usage_path, output = root / "usage.json", root / f"{name}.json"
        usage = (
            json.loads(usage_path.read_text())
            if usage_path.exists()
            else {"limit": LIMIT, "attempts": []}
        )
        if usage.get("limit") != LIMIT or len(usage["attempts"]) + total > LIMIT:
            raise ValueError("AUTHORIZATION_EXHAUSTED")
        if output.exists() or any(a["run"] == name for a in usage["attempts"]):
            raise FileExistsError("RUN_ALREADY_RESERVED")
        # Validate/build every synthetic input before reserving a paid attempt.
        bundles = []
        for case in cases:
            if "required_context" in case:
                bundle, metadata = await build(case)
            else:
                bundle = prepare([{"filename": case["path"], "patch": case["patch"]}], [], [], 1)
                metadata = {}
            if not bundle.anchors:
                raise ValueError("EMPTY_SYNTHETIC_INPUT")
            if verify_drafts:
                draft_result = validate_result(json.dumps(case["draft"]), bundle)
                if not draft_result["issues"] and not draft_result["questions"]:
                    raise ValueError("NONEMPTY_DRAFT_REQUIRED")
            bundles.append((case, bundle, metadata))
        provider_type = (
            FrozenBaselineProvider
            if baseline
            else DiagnosticProvider
            if diagnose
            else EvaluationThinkingProvider
            if thinking
            else DeepSeekProvider
        )
        provider = provider_type(Settings())
        record = {
            "started_at": datetime.now(UTC).isoformat(),
            "model": provider.model,
            "mode": "evaluation-thinking-low" if thinking else "product-non-thinking",
            "verification_enabled": verify,
            "verification_only": verify_drafts,
            "max_output_tokens": 4096 if thinking else 2000,
            "timeout_seconds": 90 if thinking else 60,
            "prompt_version": PROMPT,
            "prompt_profile": "frozen-baseline"
            if baseline
            else "diagnostic"
            if diagnose
            else "product",
            "frozen_baseline_manifest": json.loads(
                Path("evals/recall-repair/baseline-manifest.json").read_text(encoding="utf-8")
            )
            if baseline
            else None,
            "policy_version": POLICY,
            "corpus_sha256": hashlib.sha256(corpus.read_bytes()).hexdigest(),
            "max_calls": total,
            "repeats": repeats,
            "cases": [],
            "scope": "synthetic only; no product DB writes or automatic retries",
            "implementation_sha256": {
                p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
                for p in (
                    "app/domain/review/policy.py",
                    "app/domain/review/provider.py",
                    "app/domain/review/retrieval.py",
                    "app/domain/review/context_selection.py",
                    "app/domain/review/context_plan.py",
                    "app/domain/review/verification.py",
                    "scripts/evaluation_thinking_provider.py",
                    "scripts/recall_evaluation.py",
                    "scripts/stabilize_review_quality.py",
                )
            },
        }
        if baseline:
            record["prompt_version"] = record["frozen_baseline_manifest"]["prompt_version"]
        elif diagnose:
            from scripts.recall_evaluation import DIAGNOSTIC_SYSTEM, DiagnosticOutput

            record["prompt_version"] = (
                "diagnostic-"
                + hashlib.sha256(
                    (DIAGNOSTIC_SYSTEM + json.dumps(DiagnosticOutput.model_json_schema())).encode()
                ).hexdigest()[:16]
            )
        record["scope"] = (
            "authored synthetic/public-PR-derived evaluation; no product DB writes or retries"
        )
        record["temperature"] = 0
        save(output, record)
        for repeat in range(repeats):
            for case, bundle, metadata in bundles:
                attempt = {
                    "run": name,
                    "case": case["id"],
                    "repeat": repeat + 1,
                    "reserved_at": datetime.now(UTC).isoformat(),
                }
                usage["attempts"].append(attempt)
                save(usage_path, usage)  # Must reach disk BEFORE provider invocation.
                item = {
                    "id": case["id"],
                    "repeat": repeat + 1,
                    "status": "STARTED",
                    "retrieval": metadata,
                    "payload_sha256": hashlib.sha256(bundle.payload.encode()).hexdigest(),
                    "payload_bytes": len(bundle.payload.encode()),
                }
                record["cases"].append(item)
                save(output, record)
                started, stage, raw = time.monotonic(), "provider", None
                try:
                    if verify_drafts:
                        raw, incoming, outgoing = json.dumps(case["draft"]), 0, 0
                    else:
                        raw, incoming, outgoing = await provider.review(bundle.payload)
                    item.update(input_tokens=incoming, output_tokens=outgoing)
                    stage = "validation"
                    if diagnose:
                        item.update(
                            status="COMPLETED",
                            candidate_diagnostic=validate_diagnostic(raw, bundle),
                        )
                        item["seconds"] = round(time.monotonic() - started, 3)
                        save(output, record)
                        print(
                            json.dumps(
                                {"id": case["id"], "status": "COMPLETED", "diagnostic": True}
                            ),
                            flush=True,
                        )
                        continue
                    result = validate_result(raw, bundle)
                    if verify and (result["issues"] or result["questions"]):
                        item["draft_result"] = result
                        item["draft_grade"] = grade(case, result)
                        if not verify_drafts:
                            usage["attempts"].append({**attempt, "phase": "verification"})
                            save(usage_path, usage)
                        stage = "verification_provider"
                        checked, extra_in, extra_out = await provider.verify(
                            verification_payload(bundle.payload, raw)
                        )
                        item.update(
                            input_tokens=incoming + extra_in, output_tokens=outgoing + extra_out
                        )
                        stage = "verification_validation"
                        revised, verification = apply_verification(checked, raw)
                        result = validate_result(revised, bundle)
                        result["verification"] = verification
                        item["verification_decisions"] = [
                            {"index": d.index, "action": d.action, "reason": d.reason}
                            for d in VerificationOutput.model_validate_json(checked).decisions
                        ]
                    if case.get("rubric"):
                        item["semantic_review"] = {
                            "status": "PENDING_MANUAL",
                            "rubric": case["rubric"],
                        }
                    item.update(status="COMPLETED", result=result, grade=grade(case, result))
                except Exception as error:
                    item.update(status="FAILED", **diagnostics(error, stage, raw, bundle))
                item["seconds"] = round(time.monotonic() - started, 3)
                save(output, record)
                print(
                    json.dumps(
                        {
                            k: v
                            for k, v in item.items()
                            if k not in {"result", "retrieval", "draft_result", "semantic_review"}
                        }
                    ),
                    flush=True,
                )
                if item.get("error_type") in {
                    "OpenAIConnectionError",
                    "APIConnectionError",
                    "AuthenticationError",
                    "PermissionDeniedError",
                    "RateLimitError",
                }:
                    record["halted"] = "PROVIDER_UNAVAILABLE"
                    break
            if record.get("halted"):
                break
        record["finished_at"] = datetime.now(UTC).isoformat()
        record["summary"] = {
            "attempts": sum(a["run"] == name for a in usage["attempts"]),
            "reviews": len(record["cases"]),
            "validated": sum(i["status"] == "COMPLETED" for i in record["cases"]),
            "automatic_passed": sum(
                i.get("grade", {}).get("passed", False) for i in record["cases"]
            ),
            "input_tokens": sum(i.get("input_tokens", 0) for i in record["cases"]),
            "output_tokens": sum(i.get("output_tokens", 0) for i in record["cases"]),
            "authorized_attempts_used": len(usage["attempts"]),
        }
        if not diagnose and all("expected_locations" in case for case in cases):
            record["quality_metrics"] = quality_metrics(cases, record["cases"])
        save(output, record)
        print(json.dumps(record["summary"]), flush=True)
        return record
    finally:
        lock.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus", type=Path)
    parser.add_argument("name")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--allow-paid-calls", type=int, required=True)
    parser.add_argument("--evaluation-thinking", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--verify-drafts", action="store_true")
    parser.add_argument("--baseline", action="store_true")
    parser.add_argument("--diagnose", action="store_true")
    args = parser.parse_args()
    asyncio.run(
        run(
            args.corpus,
            args.name,
            args.repeats,
            args.allow_paid_calls,
            thinking=args.evaluation_thinking,
            verify=args.verify,
            verify_drafts=args.verify_drafts,
            baseline=args.baseline,
            diagnose=args.diagnose,
        )
    )
