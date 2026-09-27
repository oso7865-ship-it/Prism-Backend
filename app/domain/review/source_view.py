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
    engine: AsyncEngine, github: GitHubClient, uid: UUID, wid: UUID, rid: UUID, key: str
) -> dict[str, object]:
    async with transaction(engine) as s:
        row = await authorize(s, uid, wid, rid)
        repo = await RepositoryAccess(s).require(uid, wid, row.repository_connection_id)
        if repo.connection_generation != row.connection_generation:
            raise error("ACCESS_REVOKED")
        item = next((i for i in entries(row) if issue_key(i) == key), None)
        if (
            not item
            or type(item.get("line")) is not int
            or not isinstance(item.get("file_path"), str)
        ):
            raise error("FINDING_NOT_FOUND", ErrorKind.NOT_FOUND)
        path, line = str(item["file_path"]), int(str(item["line"]))
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
    if not 1 <= line <= len(lines):
        raise error("SOURCE_UNAVAILABLE", ErrorKind.UNAVAILABLE)
    async with transaction(engine) as s:
        await authorize(s, uid, wid, rid)
        current = await RepositoryAccess(s).require(uid, wid, row.repository_connection_id)
        if current.connection_generation != repo.connection_generation:
            raise error("ACCESS_REVOKED")
    start, end = max(1, line - 8), min(len(lines), line + 8)
    clipped = any(len(x) > 300 for x in lines[start - 1 : end])
    return {
        "file_path": path,
        "head_sha": row.head_sha,
        "start_line": start,
        "lines": [x[:300] for x in lines[start - 1 : end]],
        "truncated": clipped,
    }
