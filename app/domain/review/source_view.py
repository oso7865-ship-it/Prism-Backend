import asyncio
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncEngine

from app.domain.repository.api import RepositoryAccess
from app.domain.review.context import repository_path, source
from app.domain.review.feedback import entries
from app.domain.review.policy import issue_key
from app.domain.review.service import authorize, error
from app.shared.database.engine import transaction
from app.shared.exception.base import ErrorKind
from app.shared.github.client import GitHubClient, GitHubFailure


async def excerpt(
    engine: AsyncEngine,
    github: GitHubClient,
    uid: UUID,
    wid: UUID,
    rid: UUID,
    key: str,
    line: int | None = None,
    *,
    by_file: bool = False,
) -> dict[str, object]:
    async with transaction(engine) as s:
        row = await authorize(s, uid, wid, rid)
        repo = await RepositoryAccess(s).require(uid, wid, row.repository_connection_id)
        if repo.connection_generation != row.connection_generation:
            raise error("ACCESS_REVOKED")
        if by_file:
            coverage = (row.result or {}).get("coverage", {})
            files = coverage.get("files", []) if isinstance(coverage, dict) else []
            item = next((f for f in files if isinstance(f, dict) and f.get("file_id") == key), None)
        else:
            item = next((i for i in entries(row) if issue_key(i) == key), None)
        if not item or not isinstance(item.get("file_path"), str):
            raise error("FINDING_NOT_FOUND", ErrorKind.NOT_FOUND)
        path = str(item["file_path"])
        if line is None:
            line = 1 if by_file else int(str(item.get("line", 1)))
    try:
        async with asyncio.timeout(20):
            token = await github.installation_token(repo.installation_id, repo.github_repository_id)
            lines = await source(
                github,
                token,
                repository_path(repo.owner_login, repo.repository_name),
                row.head_sha,
                path,
            )
    except (GitHubFailure, ValueError, TimeoutError) as exc:
        raise error("SOURCE_UNAVAILABLE", ErrorKind.UNAVAILABLE) from exc
    if not 1 <= line <= max(1, len(lines)):
        raise error("SOURCE_LINE_UNAVAILABLE", ErrorKind.INVALID_INPUT)
    async with transaction(engine) as s:
        await authorize(s, uid, wid, rid)
        current = await RepositoryAccess(s).require(uid, wid, row.repository_connection_id)
        if current.connection_generation != repo.connection_generation:
            raise error("ACCESS_REVOKED")
    start = ((line - 1) // 80) * 80 + 1
    end = min(len(lines), start + 79)
    clipped = any(len(x) > 300 for x in lines[start - 1 : end])
    return {
        "file_path": path,
        "head_sha": row.head_sha,
        "start_line": start,
        "total_lines": len(lines),
        "lines": [x[:300] for x in lines[start - 1 : end]],
        "truncated": clipped,
    }
