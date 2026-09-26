from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncEngine

from app.domain.pull_request import repository as store
from app.domain.pull_request.dto import PRView, SyncView
from app.domain.pull_request.models import PullRequest, PullRequestSyncRun
from app.domain.pull_request.service import enqueue
from app.domain.repository.api import RepositoryAccess
from app.domain.workspace.api import WorkspaceAccess
from app.shared.database.engine import transaction
from app.shared.exception.base import AppException, ErrorKind
from app.shared.github.client import GitHubClient, GitHubFailure


def sync_view(row: PullRequestSyncRun) -> SyncView:
    return SyncView(
        row.id, row.status, row.fetched_count, row.next_cursor, row.error_code, row.last_success_at
    )


def pr_view(row: PullRequest) -> PRView:
    return PRView(
        row.id,
        row.repository_connection_id,
        row.pr_number,
        row.title,
        row.author_login,
        row.state,
        row.merge_status,
        row.is_draft,
        row.base_sha,
        row.head_sha,
        row.github_updated_at,
        row.synced_at,
    )


def missing() -> AppException:
    return AppException("NOT_FOUND", "리소스를 찾을 수 없습니다.", ErrorKind.NOT_FOUND)


class PRService:
    def __init__(self, engine: AsyncEngine | None, github: GitHubClient) -> None:
        self.engine = engine
        self.github = github

    def ready(self) -> AsyncEngine:
        if not self.engine:
            raise AppException(
                "DATABASE_UNAVAILABLE", "데이터베이스 연결이 필요합니다.", ErrorKind.UNAVAILABLE
            )
        return self.engine

    async def sync(
        self, uid: UUID, wid: UUID, rid: UUID, page: int, number: int | None
    ) -> SyncView:
        self.github.ready()
        async with transaction(self.ready()) as s:
            return sync_view(await enqueue(s, uid, wid, rid, page, number))

    async def status(self, uid: UUID, wid: UUID, rid: UUID, sid: UUID) -> SyncView:
        async with transaction(self.ready()) as s:
            await RepositoryAccess(s).require(uid, wid, rid, active=False)
            row = await store.run(s, wid, rid, sid)
            if not row:
                raise missing()
            return sync_view(row)

    async def listing(self, uid: UUID, wid: UUID, rid: UUID, cursor: UUID | None) -> list[PRView]:
        async with transaction(self.ready()) as s:
            await RepositoryAccess(s).require(uid, wid, rid)
            return [pr_view(row) for row in await store.listing(s, wid, rid, cursor)]

    async def detail(self, uid: UUID, wid: UUID, pid: UUID) -> PRView:
        async with transaction(self.ready()) as s:
            await WorkspaceAccess(s).require_permission(uid, wid, "read")
            row = await store.get(s, wid, pid)
            if not row:
                raise missing()
            await RepositoryAccess(s).require(uid, wid, row.repository_connection_id)
            return pr_view(row)

    async def reviews(
        self, uid: UUID, wid: UUID, pid: UUID, kind: str, page: int
    ) -> list[dict[str, object]]:
        async with transaction(self.ready()) as s:
            await WorkspaceAccess(s).require_permission(uid, wid, "read")
            pr = await store.get(s, wid, pid)
            if not pr:
                raise missing()
            repo = await RepositoryAccess(s).require(uid, wid, pr.repository_connection_id)
            number = pr.pr_number
        routes = {
            "reviews": f"pulls/{number}/reviews",
            "comments": f"issues/{number}/comments",
            "review_comments": f"pulls/{number}/comments",
            "commits": f"pulls/{number}/commits",
        }
        token = await self.github.installation_token(
            repo.installation_id, repo.github_repository_id
        )
        data = await self.github.request(
            "GET",
            f"/repos/{repo.owner_login}/{repo.repository_name}/{routes[kind]}?per_page=30&page={page}",
            token,
        )
        if not isinstance(data, list) or len(data) > 30:
            raise GitHubFailure("GITHUB_INVALID_RESPONSE")
        result: list[dict[str, object]] = []
        for item in data:
            if not isinstance(item, dict):
                raise GitHubFailure("GITHUB_INVALID_RESPONSE")
            # Do not expose source hunks, commit messages or potentially secret prose.
            user = item.get("user")
            result.append(
                {
                    "id": str(item.get("id", item.get("sha", "")))[:128],
                    "author": str(user.get("login", ""))[:255] if isinstance(user, dict) else None,
                    "state": str(item.get("state", ""))[:64],
                    "body": "본문과 코드 조각은 GitHub에서 확인하세요."
                    if kind != "commits"
                    else "",
                    "github_url": f"https://github.com/{repo.owner_login}/{repo.repository_name}/pull/{number}",
                }
            )
        async with transaction(self.ready()) as s:
            current = await RepositoryAccess(s).require(uid, wid, repo.id)
            if current.connection_generation != repo.connection_generation:
                raise missing()
        return result
