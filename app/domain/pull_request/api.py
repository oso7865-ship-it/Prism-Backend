from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.pull_request.dto import PRView
from app.domain.pull_request.service import enqueue


async def analysis_snapshot(session: AsyncSession, uid: UUID, wid: UUID, pid: UUID) -> PRView:
    from app.domain.pull_request import repository as store
    from app.domain.pull_request.query import missing, pr_view
    from app.domain.repository.api import RepositoryAccess
    from app.domain.workspace.api import WorkspaceAccess

    await WorkspaceAccess(session).require_permission(uid, wid, "sync")
    row = await store.get(session, wid, pid)
    if not row:
        raise missing()
    await RepositoryAccess(session).require(uid, wid, row.repository_connection_id, "sync")
    return pr_view(row)


async def request_sync(
    session: AsyncSession, user_id: UUID, workspace_id: UUID, repository_id: UUID
) -> UUID:
    return (await enqueue(session, user_id, workspace_id, repository_id)).id


async def request_event_sync(
    session: AsyncSession, wid: UUID, rid: UUID, generation: int, number: int
) -> UUID | None:
    """Called under delivery fence. Busy repositories leave the delivery retryable."""
    from app.domain.pull_request import repository as store
    from app.domain.pull_request.models import PullRequestSyncRun
    from app.domain.repository.api import RepositoryEvents
    from app.shared.jobs import store as jobs

    await RepositoryEvents(session).require(wid, rid, generation)
    # Do not join an already running sync: it could have fetched before this event.
    if await store.active(session, rid):
        return None
    run = PullRequestSyncRun(
        workspace_id=wid,
        repository_connection_id=rid,
        connection_generation=generation,
        actor_type="SYSTEM",
        requested_by=None,
        mode="SINGLE",
        requested_pr_number=number,
    )
    session.add(run)
    await session.flush()
    await jobs.enqueue(session, "SYNC_PULL_REQUESTS", run.id, wid)
    return run.id
