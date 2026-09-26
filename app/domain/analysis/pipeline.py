import base64
import hashlib
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from fnmatch import fnmatchcase
from urllib.parse import quote

from app.domain.analysis.contracts import (
    MAX_FILE,
    MAX_FILES,
    MAX_TOTAL,
    RULES,
    Evaluation,
    applicable,
    digest,
    language_for,
)
from app.domain.analysis.parser_process import parse_file
from app.domain.repository.api import RepositorySnapshot
from app.shared.github.client import GitHubClient, GitHubFailure


@dataclass(frozen=True)
class Snapshot:
    number: int
    base_sha: str
    head_sha: str


@dataclass
class Result:
    files: list[dict[str, object]]
    findings: list[dict[str, object]]
    coverage: str
    reason: str | None


def safe_path(path: object) -> str:
    if (
        not isinstance(path, str)
        or not 1 <= len(path.encode()) <= 4096
        or path.startswith("/")
        or "\\" in path
        or any(c in path for c in ("\x00", "\r", "\n"))
        or any(p in ("", ".", "..") for p in path.split("/"))
    ):
        raise GitHubFailure("GITHUB_INVALID_PATH")
    return path


def changed_lines(patch: object, additions: object, deletions: object) -> set[int] | None:
    if not isinstance(patch, str) or len(patch) > MAX_FILE:
        return None
    lines: set[int] = set()
    added = removed = 0
    remaining_old = remaining_new = 0
    current = 0
    hunk = False
    for line in patch.splitlines():
        m = re.match(r"^@@ -\d+(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
        if m:
            if remaining_old or remaining_new:
                return None
            remaining_old, current, remaining_new = int(m[1] or 1), int(m[2]), int(m[3] or 1)
            hunk = True
        elif line.startswith("\\"):
            continue
        elif hunk and line.startswith("+"):
            lines.add(current)
            current += 1
            added += 1
            remaining_new -= 1
        elif hunk and line.startswith("-"):
            removed += 1
            remaining_old -= 1
        elif hunk and line.startswith(" "):
            current += 1
            remaining_new -= 1
            remaining_old -= 1
        else:
            return None
        if remaining_new < 0 or remaining_old < 0:
            return None
    return (
        lines
        if hunk
        and not remaining_new
        and not remaining_old
        and added == additions
        and removed == deletions
        else None
    )


async def analyze(
    github: GitHubClient,
    repo: RepositorySnapshot,
    snap: Snapshot,
    ignored: list[str],
    checkpoint: Callable[[], Awaitable[None]],
) -> Result:
    await checkpoint()
    token = await github.installation_token(repo.installation_id, repo.github_repository_id)
    prefix = f"/repos/{quote(repo.owner_login, safe='')}/{quote(repo.repository_name, safe='')}"

    async def verify() -> int:
        await checkpoint()
        row = await github.request("GET", f"{prefix}/pulls/{snap.number}", token)
        if (
            not isinstance(row, dict)
            or row.get("base", {}).get("sha") != snap.base_sha
            or row.get("head", {}).get("sha") != snap.head_sha
        ):
            raise GitHubFailure("SNAPSHOT_CHANGED")
        count = row.get("changed_files")
        if type(count) is not int or count < 0:
            raise GitHubFailure("GITHUB_INVALID_RESPONSE")
        return count

    count = await verify()
    changes = await github.request(
        "GET", f"{prefix}/pulls/{snap.number}/files?per_page=100&page=1", token
    )
    if not isinstance(changes, list) or len(changes) != min(count, MAX_FILES):
        raise GitHubFailure("GITHUB_INCOMPLETE_FILE_LIST")
    # A tree walk from the immutable head commit proves the blob is a regular file.
    await checkpoint()
    commit = await github.request("GET", f"{prefix}/git/commits/{snap.head_sha}", token)
    root = commit.get("tree", {}).get("sha") if isinstance(commit, dict) else None
    if not isinstance(root, str) or not re.fullmatch("[0-9a-f]{40}", root):
        raise GitHubFailure("SOURCE_UNAVAILABLE")
    trees: dict[str, list[dict[str, object]]] = {}

    async def entry(path: str) -> dict[str, object]:
        sha = root
        parts = path.split("/")
        for i, part in enumerate(parts):
            await checkpoint()
            if sha not in trees:
                tree = await github.request("GET", f"{prefix}/git/trees/{sha}", token)
                if (
                    not isinstance(tree, dict)
                    or tree.get("truncated")
                    or not isinstance(tree.get("tree"), list)
                ):
                    raise GitHubFailure("SOURCE_UNAVAILABLE")
                trees[sha] = tree["tree"]
            item = next((v for v in trees[sha] if v.get("path") == part), None)
            if not item:
                raise GitHubFailure("SOURCE_UNAVAILABLE")
            if i == len(parts) - 1:
                return item
            if item.get("type") != "tree":
                raise GitHubFailure("SOURCE_UNAVAILABLE")
            sha_value = item.get("sha")
            if not isinstance(sha_value, str) or not re.fullmatch("[0-9a-f]{40}", sha_value):
                raise GitHubFailure("SOURCE_UNAVAILABLE")
            sha = sha_value
        raise GitHubFailure("SOURCE_UNAVAILABLE")

    files: list[dict[str, object]] = []
    findings: list[dict[str, object]] = []
    total = 0
    partial = count > MAX_FILES
    paths: set[str] = set()
    for change in changes:
        await checkpoint()
        if not isinstance(change, dict):
            raise GitHubFailure("GITHUB_INVALID_RESPONSE")
        path = safe_path(change.get("filename"))
        if path in paths:
            raise GitHubFailure("GITHUB_INVALID_RESPONSE")
        paths.add(path)
        result = Evaluation(language=language_for(path), status="EXCLUDED", reason="REMOVED")
        source_sha = None
        ranges = changed_lines(
            change.get("patch"), change.get("additions"), change.get("deletions")
        )
        if change.get("status") != "removed":
            try:
                item = await entry(path)
                size = item.get("size")
                if item.get("mode") not in ("100644", "100755") or item.get("type") != "blob":
                    result.reason = "NON_REGULAR_FILE"
                elif type(size) is not int or size < 0:
                    raise GitHubFailure("SOURCE_UNAVAILABLE")
                elif size > MAX_FILE or total + size > MAX_TOTAL:
                    result.status, result.reason = "LIMIT_EXCEEDED", "SOURCE_SIZE_LIMIT"
                else:
                    sha = item.get("sha")
                    if not isinstance(sha, str) or not re.fullmatch("[0-9a-f]{40}", sha):
                        raise GitHubFailure("SOURCE_UNAVAILABLE")
                    await checkpoint()
                    blob = await github.request("GET", f"{prefix}/git/blobs/{sha}", token)
                    if (
                        not isinstance(blob, dict)
                        or blob.get("encoding") != "base64"
                        or not isinstance(blob.get("content"), str)
                        or len(blob["content"]) > MAX_FILE * 2
                    ):
                        raise GitHubFailure("SOURCE_UNAVAILABLE")
                    try:
                        source = base64.b64decode(blob["content"].replace("\n", ""), validate=True)
                    except ValueError:
                        raise GitHubFailure("SOURCE_UNAVAILABLE") from None
                    if (
                        len(source) != size
                        or hashlib.sha1(b"blob " + str(size).encode() + b"\0" + source).hexdigest()
                        != sha
                    ):
                        raise GitHubFailure("SOURCE_UNAVAILABLE")
                    total += len(source)
                    source_sha = sha
                    result = await parse_file(
                        path, source, any(fnmatchcase(path, p) for p in ignored)
                    )
                    del source
            except GitHubFailure as exc:
                if exc.code in (
                    "GITHUB_ACCESS_UNAVAILABLE",
                    "GITHUB_RATE_LIMIT",
                    "GITHUB_UNAVAILABLE",
                ):
                    raise
                result.status, result.reason = "SOURCE_UNAVAILABLE", "SOURCE_UNAVAILABLE"
        if (
            result.status not in ("INCLUDED", "EXCLUDED")
            or result.limit
            or result.not_evaluated
            or result.reason
            in ("SECRET_SCAN_ONLY", "IGNORED_SOURCE_RULES", "GENERATED_SECRET_SCAN_ONLY")
        ):
            partial = True
        outcomes = [
            {
                "rule_id": r,
                "rule_version": RULES[r].version,
                "status": "EVALUATED" if r in result.evaluated else "NOT_EVALUATED",
                "reason_code": None if r in result.evaluated else result.reason,
            }
            for r in applicable(result.language)
        ]
        files.append(
            {
                "file_path": path,
                "path_digest": digest(path),
                "side": "BASE" if change.get("status") == "removed" else "HEAD",
                "language": result.language,
                "source_sha": source_sha,
                "status": result.status,
                "reason_code": result.reason,
                "finding_limit_reached": result.limit,
                "rule_outcomes": outcomes,
            }
        )
        for f in result.findings:
            rule = RULES[f.rule_id]
            findings.append(
                {
                    "rule_id": rule.id,
                    "rule_version": rule.version,
                    "category": rule.category,
                    "severity": rule.severity,
                    "confidence": rule.confidence,
                    "language": result.language,
                    "file_path": path,
                    "start_line": f.start_line,
                    "end_line": f.end_line,
                    "side": "HEAD",
                    "scope_location": "FILE"
                    if rule.id == "COM-001"
                    else "CHANGED"
                    if ranges is not None and any(f.start_line <= v <= f.end_line for v in ranges)
                    else "CONTEXT",
                    "message_code": rule.id,
                    "sanitized_message": rule.message,
                    "fingerprint": digest([rule.id, path, f.start_line, f.end_line]),
                }
            )
    await verify()
    included = any(f["status"] == "INCLUDED" for f in files)
    supported = any(f["status"] == "INCLUDED" and f["language"] for f in files)
    return Result(
        files,
        findings,
        "NONE" if not supported else "PARTIAL" if partial else "FULL_SCOPE",
        "NO_SUPPORTED_FILES"
        if included and not supported
        else "FILE_LIMIT"
        if count > MAX_FILES
        else "INCOMPLETE_SCOPE"
        if partial
        else None
        if included
        else "NO_EVALUATED_FILES",
    )
