"""Bounded syntactic candidate retrieval, not a full call graph or semantic proof."""

import asyncio
import json
import os
import re
import subprocess
import sys
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

MAX_CANDIDATE_FILES = 12
MAX_CANDIDATES = 24
MAX_SNIPPET_LINES = 160


async def inspect_sources(sources: dict[str, list[str]]) -> dict[str, Any]:
    if not sources:
        return {}
    env = {k: v for k, v in os.environ.items() if k.upper() in {"SYSTEMROOT", "WINDIR"}}
    proc = subprocess.Popen(
        [sys.executable, "-I", str(Path(__file__).with_name("syntax_entry.py"))],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=env,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0,
    )
    task = asyncio.create_task(
        asyncio.to_thread(
            proc.communicate,
            json.dumps({p: "\n".join(lines) for p, lines in sources.items()}).encode(),
            timeout=5,
        )
    )
    try:
        data, _ = await asyncio.shield(task)
        if proc.returncode or len(data) > 512_000:
            return {}
        result = json.loads(data)
        return result if isinstance(result, dict) and set(result) == set(sources) else {}
    except (ValueError, subprocess.TimeoutExpired):
        return {}
    finally:
        if proc.poll() is None:
            proc.kill()
        with suppress(subprocess.TimeoutExpired):
            await asyncio.shield(task)
        await asyncio.to_thread(proc.wait)
        for stream in (proc.stdin, proc.stdout):
            if stream:
                stream.close()


def words(value: str) -> set[str]:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return {w.lower() for w in re.findall(r"[A-Za-z]{3,}", value)} - {
        "java",
        "main",
        "src",
        "test",
        "tests",
        "class",
        "public",
        "return",
        "const",
        "void",
    }


def candidate_paths(
    regular: set[str],
    changed: dict[str, list[str]],
    metadata: dict[str, Any],
) -> list[tuple[str, int]]:
    names: set[str] = set()
    imported: set[str] = set()
    path_words: set[str] = set()
    for path, lines in changed.items():
        info = metadata.get(path, {})
        names.update(info.get("identifiers", []))
        path_words.update(words(PurePosixPath(path).stem))
        for statement in info.get("imports", []):
            for module in re.findall(r"[\"']([^\"']+)[\"']", statement):
                if module.startswith("."):
                    parts = list(PurePosixPath(path).parent.parts)
                    for part in module.split("/"):
                        if part == ".." and parts:
                            parts.pop()
                        elif part not in {".", "..", ""}:
                            parts.append(part)
                    imported.add("/".join(parts))
                else:
                    imported.add(module)
            for module in re.findall(r"(?:from|import)\s+([\w.]+)", statement):
                imported.add(module.replace(".", "/"))
        # Patch-only/error fallback; these are weak signals, never trusted instructions.
        if not info:
            names.update(re.findall(r"\b[A-Za-z_]\w{2,}\b", "\n".join(lines)[:8192]))
    scored = []
    for path in sorted(regular - changed.keys()):
        stem = str(PurePosixPath(path).with_suffix(""))
        leaf = PurePosixPath(path).stem
        # ESM commonly retains .js/.ts in the import. Compare the full path too;
        # stripping only the candidate suffix made such imports miss every file.
        direct = any(
            path == p or path.endswith("/" + p) or stem == p or stem.endswith("/" + p)
            for p in imported
        )
        score = 100 * direct + 30 * (leaf in names) + 4 * len(words(leaf) & path_words)
        if score:
            scored.append((path, score))
    return sorted(scored, key=lambda item: (-item[1], item[0]))[:MAX_CANDIDATE_FILES]


def around(lines: list[str], center: int, info: dict[str, Any]) -> list[int]:
    spans = [s for s in info.get("spans", []) if s[0] <= center <= s[1]]
    if spans:
        start, end, _ = min(spans, key=lambda s: s[1] - s[0])
        if end - start < MAX_SNIPPET_LINES:
            return list(range(max(1, start - 2), min(len(lines), end) + 1))[-MAX_SNIPPET_LINES:]
        return sorted(
            set(range(start, min(start + 4, len(lines) + 1)))
            | set(range(max(start, center - 60), min(end, center + 60, len(lines)) + 1))
            | set(range(max(start, end - 31), min(end, len(lines)) + 1))
        )
    return list(range(max(1, center - 15), min(len(lines), center + 15) + 1))


@dataclass(frozen=True)
class Candidate:
    path: str
    numbers: tuple[int, ...]
    code: str
    score: float
    protected: bool = False
    groups: tuple[int, ...] = ()


def candidates(
    paths: list[tuple[str, int]],
    sources: dict[str, list[str]],
    metadata: dict[str, Any],
    identifiers: set[str],
    calls: set[str] | None = None,
    group: int = 0,
) -> list[Candidate]:
    result = []
    for path, path_score in paths:
        lines = sources.get(path)
        if not lines:
            continue
        info = metadata.get(path, {})
        hits = [
            (n, len(set(re.findall(r"\b[A-Za-z_$][\w$]*\b", line)) & identifiers))
            for n, line in enumerate(lines, 1)
        ]
        hits = sorted((h for h in hits if h[1]), key=lambda h: (-h[1], h[0]))
        if not hits:
            hits = [(s[0], 0) for s in info.get("spans", [])[:2]] or [(1, 0)]
        direct = {s[0] for s in info.get("spans", []) if s[2] in (calls or set())}
        hits = [(n, 0) for n in sorted(direct)] + hits
        seen: set[tuple[int, ...]] = set()
        for center, matches in hits:
            numbers = tuple(around(lines, center, info))
            if numbers in seen:
                continue
            code = "\n".join(lines[n - 1] for n in numbers)
            if len(code.encode()) > 14000:
                continue
            seen.add(numbers)
            result.append(
                Candidate(path, numbers, code, path_score + 8 * matches, center in direct, (group,))
            )
            if len(seen) == 4:
                break
    return sorted(result, key=lambda c: (not c.protected, -c.score, c.path, c.numbers))[
        :MAX_CANDIDATES
    ]


def select(candidates: list[Candidate], order: list[int] | None = None) -> list[Candidate]:
    selected: dict[str, Candidate] = {}
    ranked = order if order is not None else list(range(len(candidates)))
    indices = [i for i, c in enumerate(candidates) if c.protected]
    indices += [i for i in ranked if i not in indices]
    for index in indices:
        item = candidates[index]
        if item.path not in selected:
            if len(selected) < 4:
                selected[item.path] = item
        else:
            previous = selected[item.path]
            rows = dict(zip(previous.numbers, previous.code.split("\n"), strict=True))
            rows.update(zip(item.numbers, item.code.split("\n"), strict=True))
            numbers = tuple(sorted(rows))
            selected[item.path] = Candidate(
                item.path,
                numbers,
                "\n".join(rows[n] for n in numbers),
                max(previous.score, item.score),
                previous.protected or item.protected,
                tuple(sorted(set(previous.groups + item.groups))),
            )
    return list(selected.values())


def ranking_query(changed_code: str) -> str:
    # Independent of the expected defect, model output, and user's previous judgments.
    return (
        "Find implementations and callers needed to understand this changed code:\n"
        + changed_code[:1800]
    )
