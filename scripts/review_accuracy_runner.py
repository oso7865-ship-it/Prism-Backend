"""Resumable, capped paid runs of the product review path on review-accuracy-v1 (synthetic only).

Every provider call is reserved in the shared ledger and fsynced BEFORE transmission. Failed
attempts count. There are no automatic retries. A reserved call without a stored result is never
repeated automatically.
"""

import argparse
import asyncio
import hashlib
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.domain.review.empty_review import validate_empty_review
from app.domain.review.policy import PROMPT, prepare, validate_result
from app.domain.review.provider import DeepSeekProvider
from app.domain.review.refinement import add_observations, verified_result
from app.domain.review.verification import verification_payload
from app.shared.config.settings import Settings

CAMPAIGN = "review-accuracy-20261005"
# Each campaign is a separate user authorization. A campaign never uses another one's allowance.
CAMPAIGNS = {
    "review-accuracy-20261005": {
        "maximum": 3000,
        "text": "2026-10-05 사용자: 이번 작업용으로 새로 승인, 최대상한은 3천번이야",
        "plan_cap": 600,
    },
    "review-modes-20261005": {
        "maximum": 600,
        "text": "2026-10-05 사용자: 주니어/시니어 모드 평가 유료 호출 최대 600회(채팅 선택)",
        "plan_cap": 600,
    },
}
AUTHORIZED_MAXIMUM = 3000  # User authorization 2026-10-05: "최대상한은 3천번이야".
LEDGER = Path("../prism/records/quality-evaluations/usage.json")
CORPUS = Path("evals/review-accuracy-v1")
AUTHORIZATION_TEXT = (
    "2026-10-05 사용자: 이번 작업용으로 새로 승인, 기존 계획 그대로 3단계까지, 최대상한은 3천번이야"
)
HALT = {
    "OpenAIConnectionError",
    "APIConnectionError",
    "AuthenticationError",
    "PermissionDeniedError",
    "RateLimitError",
}


def stamp() -> str:
    return datetime.now(UTC).isoformat()


def save(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


class Ledger:
    def __init__(self, path: Path, operational_cap: int, campaign: str = CAMPAIGN) -> None:
        spec = CAMPAIGNS[campaign]
        maximum = int(spec["maximum"])  # type: ignore[call-overload]
        self.campaign, self.maximum = campaign, maximum
        if operational_cap > maximum:
            raise ValueError("CAP_EXCEEDS_AUTHORIZATION")
        self.path = path
        self.data = json.loads(path.read_text(encoding="utf-8"))
        self.cap = operational_cap
        self.count = sum(a["run"] == campaign for a in self.data["attempts"])
        if not any(a.get("campaign") == campaign for a in self.data.get("authorizations", [])):
            previous = len(self.data["attempts"])
            self.data["limit"] = max(self.data["limit"], previous + maximum)
            self.data.setdefault("authorizations", []).append(
                {
                    "campaign": campaign,
                    "previous_attempts": previous,
                    "maximum_new_attempts": maximum,
                    "absolute_limit": previous + maximum,
                    "operational_cap_in_plan": spec["plan_cap"],
                    "recorded_at": stamp(),
                    "user_authorization": spec["text"],
                }
            )
            save(path, self.data)

    def reserved(self, key: str) -> bool:
        return any(a.get("key") == key for a in self.data["attempts"])

    def reserve(self, key: str, case: str, phase: str) -> None:
        if self.count >= self.cap or self.count >= self.maximum:
            raise RuntimeError("BUDGET_EXHAUSTED")
        if len(self.data["attempts"]) >= self.data["limit"]:
            raise RuntimeError("LEDGER_LIMIT_REACHED")
        if self.reserved(key):
            raise RuntimeError("ALREADY_RESERVED_WITHOUT_RESULT")
        self.data["attempts"].append(
            {
                "run": self.campaign,
                "key": key,
                "experiment": case,
                "phase": phase,
                "reserved_at": stamp(),
            }
        )
        save(self.path, self.data)  # must reach disk before any network request
        self.count += 1


async def review_case(
    provider: Any,
    ledger: Ledger,
    run: str,
    case: dict[str, Any],
    repeat: int,
    mode: str | None = None,
) -> dict[str, Any]:
    bundle = prepare(
        [{"filename": case["path"], "patch": case["patch"]}], [], [], 1, review_mode=mode
    )
    if not bundle.anchors:
        raise ValueError("EMPTY_SYNTHETIC_INPUT")
    add_observations(bundle)  # same order as the product worker
    item: dict[str, Any] = {
        "id": case["id"],
        "repeat": repeat,
        "status": "STARTED",
        "payload_sha256": hashlib.sha256(bundle.payload.encode()).hexdigest(),
        "input_tokens": 0,
        "output_tokens": 0,
    }
    started, stage = time.monotonic(), "draft"
    try:
        ledger.reserve(f"{run}:{case['id']}:r{repeat}:draft", case["id"], "draft")
        raw, incoming, outgoing = await provider.review(bundle.payload)
        item.update(draft_raw=raw, input_tokens=incoming, output_tokens=outgoing)
        recovered = False
        try:
            draft = validate_result(raw, bundle)
        except ValueError:
            recovered, draft = True, None  # same recovery rule as the product worker
        if draft and (draft["issues"] or draft["questions"]):
            item["draft_result"] = draft
            stage = "verification"
            ledger.reserve(f"{run}:{case['id']}:r{repeat}:verify", case["id"], "verify")
            checked, extra_in, extra_out = await provider.verify(
                verification_payload(bundle.payload, raw)
            )
            item.update(
                checked_raw=checked,
                input_tokens=incoming + extra_in,
                output_tokens=outgoing + extra_out,
            )
            result = verified_result(checked, raw, bundle)
        else:
            stage = "empty_recheck"
            ledger.reserve(f"{run}:{case['id']}:r{repeat}:recheck", case["id"], "recheck")
            checked, extra_in, extra_out = await provider.recheck_empty(bundle.payload)
            item.update(
                checked_raw=checked,
                input_tokens=incoming + extra_in,
                output_tokens=outgoing + extra_out,
            )
            result = validate_empty_review(checked, bundle)
            if recovered:
                result["verification"]["status"] = "OUTPUT_RECOVERED"  # type: ignore[index]
        item.update(status="COMPLETED", result=result)
    except RuntimeError:
        raise
    except Exception as error:  # noqa: BLE001 - only the type/stage is stored, never content
        item.update(status="FAILED", error_type=type(error).__name__, error_stage=stage)
        if isinstance(error, ValueError):
            item["error_code"] = str(error)[:80]
    item["seconds"] = round(time.monotonic() - started, 3)
    return item


async def run(
    corpus: Path,
    name: str,
    repeats: int,
    max_calls: int,
    ledger_path: Path = LEDGER,
    provider: Any = None,
    results_root: Path | None = None,
    mode: str | None = None,
    campaign: str = CAMPAIGN,
) -> dict[str, Any]:
    cases = json.loads(corpus.read_text(encoding="utf-8"))
    if len({c["id"] for c in cases}) != len(cases) or not 1 <= repeats <= 3:
        raise ValueError("INVALID_RUN")
    # Worst case: one draft call plus one follow-up call per review.
    if len(cases) * repeats * 2 > max_calls:
        raise ValueError("MAX_CALLS_BELOW_WORST_CASE")
    root = results_root or ledger_path.parent / campaign
    root.mkdir(parents=True, exist_ok=True)
    lock = root / "running.lock"
    with lock.open("x", encoding="utf-8") as stream:
        stream.write(name)
    try:
        output = root / f"{name}.json"
        if output.exists():
            raise FileExistsError("RUN_ALREADY_EXISTS")
        ledger = Ledger(ledger_path, max_calls, campaign)
        ledger.cap = ledger.count + max_calls  # per-run cap on top of earlier campaign use
        provider = provider or DeepSeekProvider(Settings())
        record: dict[str, Any] = {
            "campaign": campaign,
            "run": name,
            "started_at": stamp(),
            "model": provider.model,
            "prompt_version": PROMPT,
            "review_mode": mode,
            "corpus": str(corpus),
            "corpus_sha256": hashlib.sha256(corpus.read_bytes()).hexdigest(),
            "repeats": repeats,
            "max_calls": max_calls,
            "scope": "synthetic authored sources only; product path; no retries; no DB writes",
            "cases": [],
        }
        save(output, record)
        for repeat in range(1, repeats + 1):
            for case in cases:
                try:
                    item = await review_case(provider, ledger, name, case, repeat, mode)
                except RuntimeError as stop:
                    record["halted"] = str(stop)
                    break
                record["cases"].append(item)
                save(output, record)
                print(
                    json.dumps(
                        {
                            k: v
                            for k, v in item.items()
                            if k in {"id", "repeat", "status", "seconds"}
                        }
                    ),
                    flush=True,
                )
                if item.get("error_type") in HALT:
                    record["halted"] = "PROVIDER_UNAVAILABLE"
                    break
            if record.get("halted"):
                break
        record["finished_at"] = stamp()
        record["summary"] = {
            "reviews": len(record["cases"]),
            "completed": sum(i["status"] == "COMPLETED" for i in record["cases"]),
            "attempts_this_run": ledger.count - (ledger.cap - max_calls),
            "campaign_attempts_total": ledger.count,
            "input_tokens": sum(i["input_tokens"] for i in record["cases"]),
            "output_tokens": sum(i["output_tokens"] for i in record["cases"]),
        }
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
    parser.add_argument("--max-calls", type=int, required=True)
    parser.add_argument("--ledger", type=Path, default=LEDGER)
    parser.add_argument("--mode", choices=["JUNIOR", "SENIOR"])
    parser.add_argument("--campaign", choices=sorted(CAMPAIGNS), default=CAMPAIGN)
    args = parser.parse_args()
    asyncio.run(
        run(
            args.corpus,
            args.name,
            args.repeats,
            args.max_calls,
            args.ledger,
            mode=args.mode,
            campaign=args.campaign,
        )
    )
