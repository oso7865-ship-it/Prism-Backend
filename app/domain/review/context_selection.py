"""Commit-pinned retrieval and optional ranking under the original source budget."""

import asyncio
import copy
import json
import time

from app.domain.review.context import read_tree, regular_files, source
from app.domain.review.context_plan import discover, pool_for, prioritized, queries
from app.domain.review.policy import MAX_FILE, MAX_INPUT, InputBundle, exclusion
from app.domain.review.reranker import Ranker
from app.domain.review.retrieval import (
    inspect_sources,
)
from app.shared.github.client import GitHubClient, GitHubFailure


async def enrich(
    bundle: InputBundle,
    github: GitHubClient,
    token: str,
    prefix: str,
    sha: str,
    ignored: list[str],
    ranker: Ranker | None = None,
    *,
    per_file: int = MAX_FILE,
    max_input: int = MAX_INPUT,
) -> InputBundle:
    # On deadline/error return the unchanged, safe diff, never a half-built payload.
    trial = copy.deepcopy(bundle)
    try:
        async with asyncio.timeout(20):
            return await collect(
                trial, github, token, prefix, sha, ignored, ranker, per_file, max_input
            )
    except (TimeoutError, OSError):
        bundle.coverage["context_notes"] = [{"file_id": "", "reason": "CONTEXT_UNAVAILABLE"}]
        bundle.coverage["retrieval"] = {"mode": "diff_only", "fallback": "CONTEXT_UNAVAILABLE"}
        return bundle


async def collect(
    bundle: InputBundle,
    github: GitHubClient,
    token: str,
    prefix: str,
    sha: str,
    ignored: list[str],
    ranker: Ranker | None,
    per_file: int = MAX_FILE,
    max_input: int = MAX_INPUT,
) -> InputBundle:
    data = json.loads(bundle.payload)
    notes: list[dict[str, str]] = []
    try:
        tree = await read_tree(github, token, prefix, sha)
        entries = tree.get("tree")
        if tree.get("truncated") or (isinstance(entries, list) and len(entries) > 5000):
            notes.append({"file_id": "", "reason": "TREE_TRUNCATED"})
    except (GitHubFailure, ValueError):
        tree = {"tree": []}
        notes.append({"file_id": "", "reason": "RELATED_SEARCH_UNAVAILABLE"})
    regular = {path for path in regular_files(tree) if not exclusion(path, "", ignored)}
    semaphore = asyncio.Semaphore(3)

    async def read(path: str) -> tuple[str, list[str] | None]:
        try:
            async with semaphore:
                return path, await source(github, token, prefix, sha, path, regular)
        except (GitHubFailure, ValueError):
            return path, None

    changed = {fid: path for fid, (path, _) in bundle.anchors.items()}
    loaded = dict(await asyncio.gather(*(read(path) for path in changed.values())))
    safe: dict[str, list[str]] = {}
    for item in data["files"]:
        path, lines = changed[item["file_id"]], loaded.get(changed[item["file_id"]])
        if lines is None or any(
            row["line"] > len(lines) or lines[row["line"] - 1] != row["code"]
            for row in item["lines"]
        ):
            notes.append({"file_id": item["file_id"], "reason": "SOURCE_UNAVAILABLE"})
        else:
            safe[path] = lines
    metadata = await inspect_sources(safe)

    groups, omitted_groups = queries(data["files"], changed, safe, metadata)
    paths, per_group = discover(regular, groups, metadata, set(changed.values()))
    related_loaded = dict(await asyncio.gather(*(read(path) for path, _ in paths)))
    related: dict[str, list[str]] = {}
    for path, lines in related_loaded.items():
        if lines is None:
            notes.append({"file_id": "", "reason": "RELATED_SOURCE_UNAVAILABLE"})
        else:
            related[path] = lines
    related_metadata = await inspect_sources(related)
    sources = {**safe, **related}
    all_metadata = {**metadata, **related_metadata}
    pool = pool_for(groups, per_group, sources, all_metadata)
    orders = [[i for i, c in enumerate(pool) if g in c.groups] for g in range(len(groups))]
    ranking: dict[str, object] = {
        "mode": "rules",
        "candidate_count": len(pool),
        "fetched_files": len(paths),
        "query_count": len(groups),
        "omitted_queries": omitted_groups,
        "protected_candidates": sum(c.protected for c in pool),
        "per_file_bytes": per_file,
        "max_input_bytes": max_input,
    }
    if ranker and pool:
        started = time.monotonic()
        ranked: list[list[int]] = []
        diagnostics = []
        try:
            async with asyncio.timeout(2):
                for q, indices in zip(groups, orders, strict=True):
                    if not indices:
                        ranked.append([])
                        continue
                    order, result = await ranker.rank(q.code, [pool[i] for i in indices])
                    ranked.append([indices[i] for i in order])
                    diagnostics.append(result)
            orders = ranked
            if len(diagnostics) == 1:
                ranking.update(diagnostics[0])
            elif diagnostics:
                ranking["mode"] = (
                    "local_reranker"
                    if all(d.get("mode") == "local_reranker" for d in diagnostics)
                    else "rules_or_mixed"
                )
            ranking["queries"] = diagnostics
            ranking["duration_ms"] = round((time.monotonic() - started) * 1000, 2)
            ranking["truncated_documents"] = sum(
                int(str(d.get("truncated_documents", 0))) for d in diagnostics
            )
        except TimeoutError:
            ranking["fallback"] = "RERANK_TOTAL_TIMEOUT"
    by_path = {changed[f["file_id"]]: f for f in data["files"]}
    protected_missing = 0

    def append_chunk(path: str, numbers: tuple[int, ...], protected: bool = False) -> None:
        nonlocal protected_missing
        item = by_path.get(path)
        new = item is None
        if new:
            if sum(f.get("role") == "related" for f in data["files"]) >= 4:
                notes.append({"file_id": "", "reason": "RELATED_CONTEXT_LIMIT"})
                protected_missing += int(protected)
                return
            item = {
                "file_id": f"c{len(data['files']) + 1}",
                "language": path.rsplit(".", 1)[-1],
                "role": "related",
                "lines": [],
            }
            data["files"].append(item)
        assert item is not None
        previous = item["lines"]
        rows = {r["line"]: r for r in previous}
        rows.update(
            {
                n: {"line": n, "code": sources[path][n - 1], "changed": False}
                for n in numbers
                if n not in rows
            }
        )
        item["lines"] = [rows[n] for n in sorted(rows)]
        if (
            len(json.dumps(item, ensure_ascii=False).encode()) > per_file
            or len(json.dumps(data, ensure_ascii=False).encode()) > max_input
        ):
            item["lines"] = previous
            if new:
                data["files"].pop()
            notes.append({"file_id": "" if new else item["file_id"], "reason": "CONTEXT_LIMIT"})
            protected_missing += int(protected)
            return
        by_path[path] = item
        bundle.anchors[item["file_id"]] = (path, set(rows))

    # Mandatory diff already exists. Admit complete chunks atomically: never cut off a
    # guard/return mid-chunk merely to fill the final bytes of the budget.
    for index in prioritized(pool, orders):
        c = pool[index]
        if c.protected:
            append_chunk(c.path, c.numbers, True)
    for q in groups:
        append_chunk(q.path, q.numbers)
    for index in prioritized(pool, orders):
        c = pool[index]
        if not c.protected:
            append_chunk(c.path, c.numbers)
    for path, info in all_metadata.items():
        item = by_path.get(path)
        if item is None:
            continue
        if not info or info.get("partial"):
            notes.append({"file_id": item["file_id"], "reason": "SYNTAX_PARTIAL"})
        provided = {r["line"] for r in item["lines"]}
        if any(
            provided.intersection(range(s[0], s[1] + 1))
            and not set(range(s[0], s[1] + 1)) <= provided
            for s in info.get("spans", [])
        ):
            notes.append({"file_id": item["file_id"], "reason": "FUNCTION_PARTIAL"})
    ranking["protected_missing"] = protected_missing
    if omitted_groups:
        notes.append({"file_id": "", "reason": "QUERY_LIMIT"})
    for item in data["files"]:
        fid = item["file_id"]
        bundle.anchors[fid] = (bundle.anchors[fid][0], {row["line"] for row in item["lines"]})
    bundle.coverage["files"] = [
        {
            "file_id": item["file_id"],
            "file_path": bundle.anchors[item["file_id"]][0],
            "provided_lines": len(item["lines"]),
            "role": item.get("role", "changed"),
        }
        for item in data["files"]
    ]
    bundle.coverage["context_notes"] = [
        dict(t) for t in dict.fromkeys(tuple(n.items()) for n in notes)
    ]
    bundle.coverage["retrieval"] = ranking
    bundle.payload = json.dumps(data, ensure_ascii=False)
    return bundle
