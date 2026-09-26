from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repository.models import RepositoryConnection


async def get(s: AsyncSession, wid: UUID, rid: UUID) -> RepositoryConnection | None:
    return (
        await s.scalars(
            select(RepositoryConnection)
            .where(RepositoryConnection.workspace_id == wid, RepositoryConnection.id == rid)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).one_or_none()


async def by_github(s: AsyncSession, wid: UUID, gid: int) -> RepositoryConnection | None:
    return (
        await s.scalars(
            select(RepositoryConnection)
            .where(
                RepositoryConnection.workspace_id == wid,
                RepositoryConnection.github_repository_id == gid,
            )
            .with_for_update()
        )
    ).one_or_none()


async def listing(s: AsyncSession, wid: UUID, cursor: UUID | None) -> list[RepositoryConnection]:
    q = (
        select(RepositoryConnection)
        .where(RepositoryConnection.workspace_id == wid)
        .order_by(RepositoryConnection.id)
        .limit(51)
    )
    if cursor:
        q = q.where(RepositoryConnection.id > cursor)
    return list((await s.scalars(q)).all())


async def event_mapping(
    s: AsyncSession, installation: int, gid: int
) -> RepositoryConnection | None:
    return (
        await s.scalars(
            select(RepositoryConnection).where(
                RepositoryConnection.installation_id == installation,
                RepositoryConnection.github_repository_id == gid,
                RepositoryConnection.status == "ACTIVE",
            )
        )
    ).one_or_none()


async def event_candidates(
    s: AsyncSession, installation: int, ids: list[int] | None, before: datetime
) -> list[RepositoryConnection]:
    q = (
        select(RepositoryConnection)
        .where(
            RepositoryConnection.installation_id == installation,
            RepositoryConnection.status == "ACTIVE",
            RepositoryConnection.connected_at <= before,
        )
        .order_by(RepositoryConnection.workspace_id, RepositoryConnection.id)
    )
    if ids is not None:
        q = q.where(RepositoryConnection.github_repository_id.in_(ids))
    return list((await s.scalars(q)).all())


async def event_by_id(s: AsyncSession, rid: UUID) -> RepositoryConnection | None:
    return await s.get(RepositoryConnection, rid)
