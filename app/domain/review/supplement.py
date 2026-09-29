"""Resolve bounded symbol requests only inside already authorized, pinned files."""

import asyncio
import copy
import json
import re
from typing import Any, cast

from app.domain.review.context import source
from app.domain.review.output_schema import ContextRequest
from app.domain.review.policy import MAX_FILE, MAX_INPUT, InputBundle, exclusion
from app.shared.github.client import GitHubClient, GitHubFailure


async def supplement(
    bundle: InputBundle,
    requests: list[ContextRequest],
    github: GitHubClient,
    token: str,
    prefix: str,
    sha: str,
    ignored: list[str],
) -> InputBundle:
    trial = copy.deepcopy(bundle)
    data = json.loads(trial.payload)
    notes: list[dict[str, str]] = []
    cache: dict[str, list[str]] = {}

    def fits(value: dict[str, Any], reserve: int = 0) -> bool:
        code = {k: v for k, v in value.items() if k not in {"untrusted_standards", "file_paths"}}
        maximum = MAX_INPUT + (12 * 1024 if value.get("purpose") == "STANDARDS" else 0)
        return (
            len(json.dumps(code, ensure_ascii=False).encode()) <= MAX_INPUT - reserve
            and len(json.dumps(value, ensure_ascii=False).encode()) <= maximum - reserve
        )

    for request in requests[:2]:
        anchor = trial.anchors.get(request.file_id)
        note = {"file_id": request.file_id, "symbol": request.symbol, "status": "UNAVAILABLE"}
        notes.append(note)
        if anchor is None or exclusion(anchor[0], "", ignored):
            continue
        file = next(f for f in data["files"] if f["file_id"] == request.file_id)
        # A visible identifier is required, not a free-form search capability.
        if not any(
            re.search(r"\b" + re.escape(request.symbol) + r"\b", r["code"]) for r in file["lines"]
        ):
            note["status"] = "SYMBOL_NOT_PROVIDED"
            continue
        try:
            async with asyncio.timeout(4):
                if anchor[0] not in cache:
                    cache[anchor[0]] = await source(github, token, prefix, sha, anchor[0])
                lines = cache[anchor[0]]
        except (TimeoutError, GitHubFailure, ValueError, OSError):
            continue
        if any(r["line"] > len(lines) or lines[r["line"] - 1] != r["code"] for r in file["lines"]):
            note["status"] = "SOURCE_MISMATCH"
            continue
        # Only complete small files: no guessed closing brace/guard truncation.
        if len(lines) > 160:
            note["status"] = "FILE_TOO_LARGE"
            continue
        prior = file["lines"]
        old = {r["line"]: r for r in prior}
        file["lines"] = [
            old.get(n, {"line": n, "code": line, "changed": False})
            for n, line in enumerate(lines, 1)
        ]
        # Reserve room for the short supplement status as well as original metadata.
        if len(json.dumps(file, ensure_ascii=False).encode()) > MAX_FILE or not fits(
            data, reserve=1024
        ):
            file["lines"] = prior
            note["status"] = "BUDGET_LIMIT"
            continue
        trial.anchors[request.file_id] = (anchor[0], set(range(1, len(lines) + 1)))
        note["status"] = "ALREADY_PROVIDED" if len(prior) == len(lines) else "ADDED"
        for covered in cast(list[dict[str, Any]], trial.coverage.get("files", [])):
            if covered["file_id"] == request.file_id:
                covered["provided_lines"] = len(trial.anchors[request.file_id][1])
    if notes:
        data["context_supplement"] = notes
        encoded = json.dumps(data, ensure_ascii=False)
        if fits(data):
            trial.payload = encoded
        else:
            bundle.coverage["context_supplement"] = [
                {**note, "status": "BUDGET_LIMIT"} for note in notes
            ]
            return bundle
        trial.coverage["context_supplement"] = notes
    return trial
