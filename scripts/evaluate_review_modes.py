"""Small synthetic purpose/RAG integration evaluation; no customer code is transmitted."""

import argparse
import asyncio
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from app.domain.review.empty_review import validate_empty_review
from app.domain.review.policy import PROMPT, prepare, validate_result
from app.domain.review.provider import DeepSeekProvider
from app.domain.review.verification import apply_verification, verification_payload
from app.domain.standards.api import StandardSnapshot, context
from app.domain.standards.index import index_document
from app.shared.config.settings import Settings
from scripts.stabilize_review_quality import save

CASES = [
    (
        "code-null",
        "CODE",
        "app.py",
        "def name(user):\n    return user.name if user is None else ''",
        None,
        True,
    ),
    (
        "code-guard",
        "CODE",
        "app.py",
        "def name(user):\n    return '' if user is None else user.name",
        None,
        False,
    ),
    (
        "sql-injection",
        "SECURITY",
        "api.py",
        "from flask import request\n\ndef lookup(cursor):\n"
        "    cursor.execute(\"SELECT name FROM users WHERE id = \" + request.args['id'])\n"
        "    return cursor.fetchone()",
        None,
        True,
    ),
    (
        "sql-parameters",
        "SECURITY",
        "api.py",
        "from flask import request\n\ndef lookup(cursor):\n"
        "    cursor.execute(\"SELECT name FROM users WHERE id = %s\", (request.args['id'],))\n"
        "    return cursor.fetchone()",
        None,
        False,
    ),
    (
        "convention-print",
        "STANDARDS",
        "app.py",
        "def save_record(record, logger):\n    print('record saved')\n    return record",
        "# 로깅 규칙\n애플리케이션 함수에서 print를 사용하지 않는다. "
        "주입한 logger.info를 사용한다. 로깅 내용에는 비밀정보를 넣지 않는다.",
        True,
    ),
    (
        "convention-logger",
        "STANDARDS",
        "app.py",
        "def save_record(record, logger):\n    logger.info('record saved')\n    return record",
        "# 로깅 규칙\n애플리케이션 함수에서 print를 사용하지 않는다. "
        "주입한 logger.info를 사용한다. 로깅 내용에는 비밀정보를 넣지 않는다.",
        False,
    ),
]


async def run(root: Path, name: str, max_calls: int) -> dict:
    if max_calls != len(CASES) * 2:
        raise ValueError("EXACT_MAX_CALLS_REQUIRED")
    usage_path, output, lock = root / "usage.json", root / f"{name}.json", root / "running.lock"
    with lock.open("x", encoding="utf-8") as file:
        file.write(name)
    try:
        usage = json.loads(usage_path.read_text(encoding="utf-8"))
        if usage["limit"] != 3000 or len(usage["attempts"]) + max_calls > 3000:
            raise ValueError("AUTHORIZATION_EXHAUSTED")
        if output.exists() or any(a["run"] == name for a in usage["attempts"]):
            raise ValueError("DUPLICATE_RUN")
        provider = DeepSeekProvider(Settings())
        results = []
        report = {
            "scope": "six synthetic cases, purpose integration only; not a security certification",
            "prompt_version": PROMPT,
            "model": provider.model,
            "cases": results,
        }
        for case, purpose, path, source, document, expect_finding in CASES:
            patch = (
                "@@ -0,0 +1,"
                + str(len(source.splitlines()))
                + " @@\n"
                + "\n".join("+" + line for line in source.splitlines())
            )
            bundle = prepare([{"filename": path, "patch": patch}], [], [], 1)
            payload = json.loads(bundle.payload)
            payload["purpose"] = purpose
            if document:
                snapshot = StandardSnapshot(
                    UUID(int=1),
                    UUID(int=2),
                    1,
                    "합성 로깅 규칙",
                    "CONVENTION",
                    ["**"],
                    [],
                    True,
                    [],
                    index_document(document),
                )
                payload["untrusted_standards"] = context([snapshot], {"f1": path}, source)[
                    "sections"
                ]
                payload["file_paths"] = {"f1": path}
            bundle.payload = json.dumps(payload, ensure_ascii=False)
            item = {
                "id": case,
                "purpose": purpose,
                "expected_finding": expect_finding,
                "payload_sha256": hashlib.sha256(bundle.payload.encode()).hexdigest(),
                "input_tokens": 0,
                "output_tokens": 0,
                "status": "STARTED",
            }
            results.append(item)
            save(output, report)

            def reserve(phase):
                usage["attempts"].append(
                    {
                        "run": name,
                        "case": case,
                        "repeat": 1,
                        "phase": phase,
                        "reserved_at": datetime.now(UTC).isoformat(),
                    }
                )
                save(usage_path, usage)

            try:
                reserve("draft")
                raw, incoming, outgoing = await provider.review(bundle.payload)
                item.update(input_tokens=incoming, output_tokens=outgoing)
                result = validate_result(raw, bundle)
                if result["issues"] or result["questions"]:
                    reserve("verification")
                    checked, extra_in, extra_out = await provider.verify(
                        verification_payload(bundle.payload, raw)
                    )
                    revised, verification = apply_verification(checked, raw)
                    result = validate_result(revised, bundle)
                    result["verification"] = verification
                else:
                    reserve("empty_recheck")
                    checked, extra_in, extra_out = await provider.recheck_empty(bundle.payload)
                    result = validate_empty_review(checked, bundle)
                item.update(
                    status="COMPLETED",
                    result=result,
                    input_tokens=incoming + extra_in,
                    output_tokens=outgoing + extra_out,
                    signal_pass=bool(result["issues"]) == expect_finding
                    and not result["questions"],
                )
            except Exception as exc:
                # No raw provider exception/output/code/key persistence.
                item.update(status="FAILED", error_type=type(exc).__name__, signal_pass=False)
            save(output, report)
            print(
                json.dumps(
                    {"case": case, "status": item["status"], "signal_pass": item["signal_pass"]}
                ),
                flush=True,
            )
        report["attempts"] = sum(a["run"] == name for a in usage["attempts"])
        report["authorized_attempts_used"] = len(usage["attempts"])
        save(output, report)
        return report
    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--max-calls", type=int, required=True)
    parser.add_argument("--execute", action="store_true", required=True)
    args = parser.parse_args()
    asyncio.run(run(args.root, args.name, args.max_calls))
