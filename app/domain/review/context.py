"""Bounded, commit-pinned source context. Source never enters persistent storage."""

import base64
import binascii
import re
from urllib.parse import quote

from app.domain.review.policy import SECRET, exclusion
from app.shared.github.client import GitHubClient


def repository_path(owner: str, name: str) -> str:
    return f"/repos/{quote(owner, safe='')}/{quote(name, safe='')}"


async def read_tree(github: GitHubClient, token: str, prefix: str, sha: str) -> dict[str, object]:
    commit = await github.request("GET", f"{prefix}/git/commits/{sha}", token)
    root = commit.get("tree") if isinstance(commit, dict) else None
    tree_sha = root.get("sha") if isinstance(root, dict) else None
    if not isinstance(tree_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", tree_sha):
        raise ValueError("INVALID_TREE")
    tree = await github.request("GET", f"{prefix}/git/trees/{tree_sha}?recursive=1", token)
    if not isinstance(tree, dict) or not isinstance(tree.get("tree"), list):
        raise ValueError("INVALID_TREE")
    return tree


async def source(
    github: GitHubClient,
    token: str,
    prefix: str,
    sha: str,
    path: str,
    regular_paths: set[str] | None = None,
) -> list[str]:
    if exclusion(path, "", []) or not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("SOURCE_UNAVAILABLE")
    if regular_paths is None:
        tree = await read_tree(github, token, prefix, sha)
        regular_paths = regular_files(tree)
    if path not in regular_paths:
        raise ValueError("SOURCE_UNAVAILABLE")
    data = await github.request(
        "GET", f"{prefix}/contents/{quote(path, safe='/')}?ref={sha}", token
    )
    if (
        not isinstance(data, dict)
        or data.get("type") != "file"
        or data.get("encoding") != "base64"
        or type(data.get("size")) is not int
        or not 0 <= data["size"] <= 200_000
        or not isinstance(data.get("content"), str)
        or len(data["content"]) > 280_000
    ):
        raise ValueError("SOURCE_UNAVAILABLE")
    try:
        raw = base64.b64decode("".join(data["content"].split()), validate=True)
        text = raw.decode("utf-8")
    except (ValueError, UnicodeError, binascii.Error) as exc:
        raise ValueError("SOURCE_UNAVAILABLE") from exc
    if len(raw) > 200_000 or "\x00" in text or SECRET.search(text):
        raise ValueError("SOURCE_UNAVAILABLE")
    return text.splitlines()


def regular_files(tree: dict[str, object]) -> set[str]:
    entries = tree.get("tree")
    if not isinstance(entries, list):
        return set()
    return {
        t["path"]
        for t in entries[:5000]
        if isinstance(t, dict)
        and isinstance(t.get("path"), str)
        and t.get("type") == "blob"
        and t.get("mode") in ("100644", "100755")
    }
