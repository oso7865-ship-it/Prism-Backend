"""Function-local syntactic retrieval. Name matches are hints, never a call-graph proof."""

from dataclasses import dataclass, replace
from itertools import zip_longest
from typing import Any

from app.domain.review.retrieval import (
    MAX_CANDIDATES,
    Candidate,
    around,
    candidate_paths,
    candidates,
)

MAX_GROUPS = 8


@dataclass(frozen=True)
class Query:
    path: str
    numbers: tuple[int, ...]
    identifiers: frozenset[str]
    calls: frozenset[str]
    code: str


def queries(
    files: list[dict[str, Any]],
    paths: dict[str, str],
    sources: dict[str, list[str]],
    metadata: dict[str, Any],
) -> tuple[list[Query], int]:
    per_file: list[list[Query]] = []
    for item in files:
        path = paths[item["file_id"]]
        lines, info = sources.get(path), metadata.get(path, {})
        groups: dict[tuple[int, ...], Query] = {}
        if lines:
            for row in item["lines"]:
                if not row["changed"]:
                    continue
                spans = [s for s in info.get("spans", []) if s[0] <= row["line"] <= s[1]]
                span = min(spans, key=lambda s: s[1] - s[0]) if spans else None
                # Long functions have one group too, not a query for every changed line.
                key = (span[0], span[1]) if span else (row["line"] // 30,)
                if key in groups:
                    continue
                numbers = tuple(around(lines, row["line"], info))
                start, end = (span[0], span[1]) if span else (min(numbers), max(numbers))
                groups[key] = Query(
                    path,
                    numbers,
                    frozenset(n for line, n in info.get("symbols", []) if start <= line <= end),
                    frozenset(n for line, n in info.get("calls", []) if start <= line <= end),
                    "\n".join(lines[n - 1] for n in numbers),
                )
        per_file.append(list(groups.values()))
    fair = [q for row in zip_longest(*per_file) for q in row if q is not None]
    return fair[:MAX_GROUPS], max(0, len(fair) - MAX_GROUPS)


def discover(
    regular: set[str], groups: list[Query], metadata: dict[str, Any], changed: set[str]
) -> tuple[list[tuple[str, int]], list[list[tuple[str, int]]]]:
    per_group = [
        candidate_paths(
            regular - changed,
            {q.path: q.code.splitlines()},
            {
                q.path: {
                    "imports": metadata.get(q.path, {}).get("imports", []),
                    "identifiers": sorted(q.identifiers),
                }
            },
        )
        for q in groups
    ]
    chosen: dict[str, int] = {}
    for row in zip_longest(*per_group):
        for entry in row:
            if entry is not None and (entry[0] in chosen or len(chosen) < 12):
                chosen[entry[0]] = max(chosen.get(entry[0], 0), entry[1])
    return list(chosen.items()), per_group


def pool_for(
    groups: list[Query],
    per_group: list[list[tuple[str, int]]],
    sources: dict[str, list[str]],
    metadata: dict[str, Any],
) -> list[Candidate]:
    pools = [
        candidates([(q.path, 100), *paths], sources, metadata, set(q.identifiers), set(q.calls), i)
        for i, (q, paths) in enumerate(zip(groups, per_group, strict=True))
    ]
    merged: dict[tuple[str, tuple[int, ...]], Candidate] = {}
    for protected in (True, False):
        rows = [[c for c in pool if c.protected == protected] for pool in pools]
        for row in zip_longest(*rows):
            for item in row:
                if item is None:
                    continue
                key = (item.path, item.numbers)
                if key in merged:
                    old = merged[key]
                    merged[key] = replace(old, groups=tuple(sorted(set(old.groups + item.groups))))
                elif len(merged) < MAX_CANDIDATES:
                    merged[key] = item
    return list(merged.values())


def prioritized(pool: list[Candidate], orders: list[list[int]]) -> list[int]:
    """Protected chunks are independent of model rank; remaining queries share the budget."""
    result = [i for i, c in enumerate(pool) if c.protected]
    for row in zip_longest(*orders):
        for index in row:
            if index is not None and index not in result:
                result.append(index)
    return result
