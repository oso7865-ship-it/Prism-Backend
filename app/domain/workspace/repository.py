from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.workspace.models import Invitation, Workspace, WorkspaceMember


async def lock_workspace(s: AsyncSession, wid: UUID) -> Workspace | None:
    return (
        await s.scalars(select(Workspace).where(Workspace.id == wid).with_for_update())
    ).one_or_none()


async def member(s: AsyncSession, wid: UUID, uid: UUID) -> WorkspaceMember | None:
    return (
        await s.scalars(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == wid, WorkspaceMember.user_id == uid
            )
        )
    ).one_or_none()


async def workspaces(
    s: AsyncSession, uid: UUID, cursor: UUID | None
) -> list[tuple[Workspace, WorkspaceMember]]:
    query = (
        select(Workspace, WorkspaceMember)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(
            WorkspaceMember.user_id == uid,
            WorkspaceMember.status == "ACTIVE",
            Workspace.status == "ACTIVE",
        )
        .order_by(Workspace.id)
        .limit(51)
    )
    if cursor:
        query = query.where(Workspace.id > cursor)
    return [(w, m) for w, m in (await s.execute(query)).all()]


async def members(s: AsyncSession, wid: UUID, cursor: UUID | None) -> list[WorkspaceMember]:
    query = (
        select(WorkspaceMember)
        .where(WorkspaceMember.workspace_id == wid, WorkspaceMember.status == "ACTIVE")
        .order_by(WorkspaceMember.user_id)
        .limit(51)
    )
    if cursor:
        query = query.where(WorkspaceMember.user_id > cursor)
    return list((await s.scalars(query)).all())


async def invitation_by_hash(s: AsyncSession, digest: str) -> Invitation | None:
    return (
        await s.scalars(select(Invitation).where(Invitation.token_hash == digest))
    ).one_or_none()


async def invitation(s: AsyncSession, wid: UUID, iid: UUID) -> Invitation | None:
    return (
        await s.scalars(
            select(Invitation).where(Invitation.workspace_id == wid, Invitation.id == iid)
        )
    ).one_or_none()


async def expire(s: AsyncSession, wid: UUID, now: datetime) -> None:
    await s.execute(
        update(Invitation)
        .where(
            Invitation.workspace_id == wid,
            Invitation.status == "PENDING",
            Invitation.expires_at <= now,
        )
        .values(status="EXPIRED")
    )


async def pending(s: AsyncSession, wid: UUID, target: int) -> Invitation | None:
    return (
        await s.scalars(
            select(Invitation).where(
                Invitation.workspace_id == wid,
                Invitation.target_github_user_id == target,
                Invitation.status == "PENDING",
            )
        )
    ).one_or_none()


async def invitations(s: AsyncSession, wid: UUID, cursor: UUID | None) -> list[Invitation]:
    q = (
        select(Invitation)
        .where(Invitation.workspace_id == wid, Invitation.status == "PENDING")
        .order_by(Invitation.id)
        .limit(51)
    )
    if cursor:
        q = q.where(Invitation.id > cursor)
    return list((await s.scalars(q)).all())
