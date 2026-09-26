from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.domain.pull_request import repository as store
from app.domain.pull_request.github import RemotePR, fetch
from app.domain.pull_request.models import PullRequestSyncRun
from app.domain.repository.api import RepositoryAccess, RepositoryEvents, RepositorySnapshot
from app.shared.database.engine import transaction
from app.shared.exception.base import AppException, ErrorKind
from app.shared.github.client import GitHubClient, GitHubFailure
from app.shared.jobs import store as jobs
from app.shared.jobs.store import Claim


async def enqueue(
    s: AsyncSession, uid: UUID, wid: UUID, rid: UUID, page: int = 1, number: int | None = None
) -> PullRequestSyncRun:
    repo = await RepositoryAccess(s).require(uid, wid, rid, "sync")
    mode = "SINGLE" if number else "RECENT" if page == 1 else "PAGE"
    cursor = str(page) if mode == "PAGE" else None
    existing = await store.active(s, rid)
    if existing:
        if (
            existing.mode,
            existing.request_cursor,
            existing.requested_pr_number,
            existing.connection_generation,
        ) != (mode, cursor, number, repo.connection_generation):
            raise AppException(
                "SYNC_IN_PROGRESS", "다른 동기화가 진행 중입니다.", ErrorKind.CONFLICT
            )
        return existing
    cached = await store.cached_run(s, rid, mode, cursor, number, repo.connection_generation)
    run = PullRequestSyncRun(
        workspace_id=wid,
        repository_connection_id=rid,
        connection_generation=repo.connection_generation,
        actor_type="USER",
        requested_by=uid,
        mode=mode,
        request_cursor=cursor,
        requested_pr_number=number,
        etag=cached.etag if cached else None,
        next_cursor=cached.next_cursor if cached else None,
    )
    s.add(run)
    await s.flush()
    await jobs.enqueue(s, "SYNC_PULL_REQUESTS", run.id, wid)
    return run


class SyncWorker:
    def __init__(self, engine: AsyncEngine, github: GitHubClient) -> None:
        self.engine = engine
        self.github = github

    async def access(self, s: AsyncSession, run: PullRequestSyncRun) -> RepositorySnapshot:
        if run.actor_type == "SYSTEM":
            return await RepositoryEvents(s).require(
                run.workspace_id, run.repository_connection_id, run.connection_generation
            )
        assert run.requested_by
        return await RepositoryAccess(s).require(
            run.requested_by, run.workspace_id, run.repository_connection_id, "sync"
        )

    async def execute(self, c: Claim, expired: bool = False) -> None:
        if expired:
            await self.complete(c, [], "LEASE_EXPIRED", True, expired=True)
            return
        try:
            async with transaction(self.engine) as s:
                run = await store.run_by_id(s, c.aggregate_id)
                if not run:
                    return
                repo = await self.access(s, run)
                run = await store.run(s, run.workspace_id, run.repository_connection_id, run.id)
                assert run
                if not await jobs.fence(s, c):
                    return
                if repo.connection_generation != run.connection_generation:
                    raise AppException(
                        "CONNECTION_CHANGED", "연결이 변경되었습니다.", ErrorKind.CONFLICT
                    )
                run.status = "RUNNING"
                run.started_at = datetime.now(UTC)
                page = int(run.request_cursor or "1")
                number = run.requested_pr_number
                etag = run.etag
            # Total HTTP budget fits inside lease; no transaction held across network.
            import asyncio

            async with asyncio.timeout(40):
                rows, new_etag, not_modified = await fetch(
                    self.github,
                    repo.installation_id,
                    repo.github_repository_id,
                    repo.owner_login,
                    repo.repository_name,
                    page,
                    number,
                    etag,
                )
            await self.complete(c, rows, etag=new_etag, not_modified=not_modified)
        except GitHubFailure as exc:
            await self.complete(
                c,
                [],
                exc.code,
                exc.code in {"GITHUB_UNAVAILABLE", "GITHUB_RATE_LIMIT", "GITHUB_SNAPSHOT_CONFLICT"},
                delay=exc.retry_after or 5,
            )
        except TimeoutError:
            await self.complete(c, [], "GITHUB_TIMEOUT", True)
        except AppException as exc:
            await self.complete(c, [], exc.code)

    async def complete(
        self,
        c: Claim,
        rows: list[RemotePR],
        code: str | None = None,
        retry: bool = False,
        delay: int = 5,
        expired: bool = False,
        etag: str | None = None,
        not_modified: bool = False,
    ) -> None:
        async with transaction(self.engine) as s:
            run = await store.run_by_id(s, c.aggregate_id)
            if not run:
                return
            try:
                repo = await self.access(s, run)
                if repo.connection_generation != run.connection_generation:
                    code, retry = "CONNECTION_CHANGED", False
            except AppException as exc:
                code, retry = exc.code, False
            run = await store.run(s, run.workspace_id, run.repository_connection_id, run.id)
            assert run
            job = await jobs.fence(s, c, expired)
            if not job:
                return
            if code == "GITHUB_ACCESS_UNAVAILABLE":
                await RepositoryEvents(s).suspend_locked([run.repository_connection_id])
            if code is None:
                from app.domain.pull_request.github import RemotePR

                for row in rows:
                    assert isinstance(row, RemotePR)
                    await store.upsert(
                        s,
                        run.workspace_id,
                        run.repository_connection_id,
                        run.connection_generation,
                        row,
                    )
                now = datetime.now(UTC)
                run.etag = etag
                run.fetched_count = len(rows)
                run.last_success_at = now
                if not not_modified:
                    run.next_cursor = (
                        str(int(run.request_cursor or "1") + 1)
                        if len(rows) == 30 and run.mode != "SINGLE"
                        else None
                    )
                if run.actor_type == "SYSTEM":
                    await RepositoryEvents(s).sync_success(
                        run.workspace_id,
                        run.repository_connection_id,
                        run.connection_generation,
                        now,
                    )
                else:
                    assert run.requested_by
                    await RepositoryAccess(s).sync_success(
                        run.requested_by, run.workspace_id, run.repository_connection_id, now
                    )
            state = jobs.finish(job, code, retry, delay)
            run.status = "PENDING" if state == "READY" else "FAILED" if code else "COMPLETED"
            run.finished_at = None if state == "READY" else datetime.now(UTC)
            run.error_code = code
