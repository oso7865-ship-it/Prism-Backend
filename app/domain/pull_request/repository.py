from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import literal, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.pull_request.github import RemotePR
from app.domain.pull_request.models import PullRequest, PullRequestSyncRun
from app.shared.github.client import GitHubFailure


async def active(s: AsyncSession, rid: UUID) -> PullRequestSyncRun | None:
    return (
        await s.scalars(
            select(PullRequestSyncRun).where(
                PullRequestSyncRun.repository_connection_id == rid,
                PullRequestSyncRun.status.in_(["PENDING", "RUNNING"]),
            )
        )
    ).one_or_none()


async def run(s: AsyncSession, wid: UUID, rid: UUID, sid: UUID) -> PullRequestSyncRun | None:
    return (
        await s.scalars(
            select(PullRequestSyncRun)
            .where(
                PullRequestSyncRun.workspace_id == wid,
                PullRequestSyncRun.repository_connection_id == rid,
                PullRequestSyncRun.id == sid,
            )
            .with_for_update()
        )
    ).one_or_none()


async def run_by_id(s: AsyncSession, sid: UUID) -> PullRequestSyncRun | None:
    return (
        await s.scalars(select(PullRequestSyncRun).where(PullRequestSyncRun.id == sid))
    ).one_or_none()


async def listing(s: AsyncSession, wid: UUID, rid: UUID, cursor: UUID | None) -> list[PullRequest]:
    q = (
        select(PullRequest)
        .where(PullRequest.workspace_id == wid, PullRequest.repository_connection_id == rid)
        .order_by(PullRequest.github_updated_at.desc(), PullRequest.id.desc())
        .limit(51)
    )
    if cursor:
        anchor = await get(s, wid, cursor)
        if not anchor or anchor.repository_connection_id != rid:
            return []
        q = q.where(
            tuple_(PullRequest.github_updated_at, PullRequest.id)
            < tuple_(literal(anchor.github_updated_at), literal(anchor.id))
        )
    return list((await s.scalars(q)).all())


async def get(s: AsyncSession, wid: UUID, pid: UUID) -> PullRequest | None:
    return (
        await s.scalars(
            select(PullRequest).where(PullRequest.workspace_id == wid, PullRequest.id == pid)
        )
    ).one_or_none()


async def upsert(s: AsyncSession, wid: UUID, rid: UUID, generation: int, pr: RemotePR) -> None:
    row = (
        await s.scalars(
            select(PullRequest).where(
                PullRequest.repository_connection_id == rid, PullRequest.pr_number == pr.number
            )
        )
    ).one_or_none()
    if row and row.github_updated_at > pr.updated_at:
        return
    if (
        row
        and row.github_updated_at == pr.updated_at
        and (row.head_sha != pr.head.sha or row.base_sha != pr.base.sha)
    ):
        raise GitHubFailure("GITHUB_SNAPSHOT_CONFLICT")
    values = dict(
        workspace_id=wid,
        repository_connection_id=rid,
        github_pr_id=pr.id,
        pr_number=pr.number,
        title=pr.title,
        author_github_user_id=pr.user.id if pr.user else None,
        author_login=pr.user.login if pr.user else None,
        state=pr.state.upper(),
        merge_status="MERGED"
        if pr.merged_at or pr.merged
        else "NOT_MERGED"
        if pr.merged is False
        else "UNKNOWN",
        is_draft=pr.draft,
        base_ref=pr.base.ref,
        head_ref=pr.head.ref,
        base_sha=pr.base.sha,
        head_sha=pr.head.sha,
        changed_files_count=pr.changed_files,
        commits_count=pr.commits,
        github_created_at=pr.created_at,
        github_updated_at=pr.updated_at,
        closed_at=pr.closed_at,
        merged_at=pr.merged_at,
        synced_at=datetime.now(UTC),
        synced_connection_generation=generation,
    )
    if row:
        for key, value in values.items():
            setattr(row, key, value)
    else:
        s.add(PullRequest(**values))


async def cached_run(
    s: AsyncSession, rid: UUID, mode: str, cursor: str | None, number: int | None, generation: int
) -> PullRequestSyncRun | None:
    query = (
        select(PullRequestSyncRun)
        .where(
            PullRequestSyncRun.repository_connection_id == rid,
            PullRequestSyncRun.mode == mode,
            PullRequestSyncRun.request_cursor == cursor,
            PullRequestSyncRun.requested_pr_number == number,
            PullRequestSyncRun.connection_generation == generation,
            PullRequestSyncRun.status == "COMPLETED",
        )
        .order_by(PullRequestSyncRun.finished_at.desc())
        .limit(1)
    )
    return (await s.scalars(query)).one_or_none()
