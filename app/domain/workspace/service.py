from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.domain.user.api import UserAPI
from app.domain.workspace import repository as store
from app.domain.workspace.dto import InvitationCreated, InvitationView, MemberView, WorkspaceView
from app.domain.workspace.exceptions import PermissionDenied, WorkspaceConflict, WorkspaceMissing
from app.domain.workspace.models import Invitation, Workspace, WorkspaceMember
from app.domain.workspace.permission import allowed
from app.shared.database.engine import transaction
from app.shared.exception.base import AppException, ErrorKind
from app.shared.security.hashing import random_token, token_hash


async def require(s: AsyncSession, uid: UUID, wid: UUID, permission: str) -> WorkspaceMember:
    workspace = await store.lock_workspace(s, wid)
    await UserAPI(s).get_active_user(uid)
    member = await store.member(s, wid, uid)
    if not workspace or workspace.status != "ACTIVE" or not member or member.status != "ACTIVE":
        raise WorkspaceMissing()
    if not allowed(member.role, permission):
        raise PermissionDenied()
    return member


def invitation_view(i: Invitation) -> InvitationView:
    return InvitationView(i.id, i.target_github_user_id, i.role, i.status, i.expires_at)


class WorkspaceService:
    def __init__(self, engine: AsyncEngine | None) -> None:
        self.engine = engine

    def ready(self) -> AsyncEngine:
        if self.engine is None:
            raise AppException(
                "DATABASE_UNAVAILABLE", "데이터베이스 연결이 필요합니다.", ErrorKind.UNAVAILABLE
            )
        return self.engine

    async def create(self, uid: UUID, name: str) -> WorkspaceView:
        async with transaction(self.ready()) as s:
            await UserAPI(s).get_active_user(uid)
            w = Workspace(name=name, created_by=uid)
            s.add(w)
            await s.flush()
            s.add(WorkspaceMember(workspace_id=w.id, user_id=uid, role="OWNER"))
            return WorkspaceView(w.id, w.name, "OWNER")

    async def list_workspaces(self, uid: UUID, cursor: UUID | None) -> list[WorkspaceView]:
        async with transaction(self.ready()) as s:
            await UserAPI(s).get_active_user(uid)
            return [
                WorkspaceView(w.id, w.name, m.role)
                for w, m in await store.workspaces(s, uid, cursor)
            ]

    async def members(self, uid: UUID, wid: UUID, cursor: UUID | None) -> list[MemberView]:
        async with transaction(self.ready()) as s:
            await require(s, uid, wid, "read")
            return [MemberView(m.user_id, m.role) for m in await store.members(s, wid, cursor)]

    async def invite(self, uid: UUID, wid: UUID, target: int, role: str) -> InvitationCreated:
        async with transaction(self.ready()) as s:
            await require(s, uid, wid, "owner" if role == "ADMIN" else "manage")
            await store.expire(s, wid, datetime.now(UTC))
            if await store.pending(s, wid, target):
                raise WorkspaceConflict("INVITATION_EXISTS")
            raw = random_token()
            i = Invitation(
                workspace_id=wid,
                target_github_user_id=target,
                invited_by=uid,
                role=role,
                token_hash=token_hash(raw),
                expires_at=datetime.now(UTC) + timedelta(hours=24),
            )
            s.add(i)
            await s.flush()
            return InvitationCreated(invitation_view(i), raw)

    async def invitations(self, uid: UUID, wid: UUID, cursor: UUID | None) -> list[InvitationView]:
        async with transaction(self.ready()) as s:
            await require(s, uid, wid, "manage")
            await store.expire(s, wid, datetime.now(UTC))
            return [invitation_view(i) for i in await store.invitations(s, wid, cursor)]

    async def revoke(self, uid: UUID, wid: UUID, iid: UUID) -> None:
        async with transaction(self.ready()) as s:
            actor = await require(s, uid, wid, "manage")
            i = await store.invitation(s, wid, iid)
            if not i:
                raise WorkspaceMissing()
            if i.role == "ADMIN" and actor.role != "OWNER":
                raise PermissionDenied()
            if i.status != "PENDING":
                raise WorkspaceConflict()
            i.status = "REVOKED"
            i.revoked_at = datetime.now(UTC)

    async def accept(self, uid: UUID, raw: str) -> WorkspaceView:
        async with transaction(self.ready()) as s:
            user = await UserAPI(s).get_active_user(uid)
            found = await store.invitation_by_hash(s, token_hash(raw))
            if not found:
                raise WorkspaceMissing()
            wid = found.workspace_id
            w = await store.lock_workspace(s, wid)
            # Refresh after workspace lock: another request may have consumed it while waiting.
            await s.refresh(found)
            if not w or w.status != "ACTIVE":
                raise WorkspaceMissing()
            if found.target_github_user_id != user.github_user_id:
                raise PermissionDenied()
            if found.status != "PENDING" or found.expires_at <= datetime.now(UTC):
                raise WorkspaceConflict("INVITATION_UNAVAILABLE")
            inviter = await store.member(s, wid, found.invited_by)
            if (
                not inviter
                or inviter.status != "ACTIVE"
                or not allowed(inviter.role, "owner" if found.role == "ADMIN" else "manage")
            ):
                raise WorkspaceConflict("INVITER_UNAVAILABLE")
            m = await store.member(s, wid, uid)
            if m and m.status == "ACTIVE":
                raise WorkspaceConflict("ALREADY_MEMBER")
            if m:
                m.status = "ACTIVE"
                m.role = found.role
                m.ended_at = None
                m.joined_at = datetime.now(UTC)
            else:
                s.add(WorkspaceMember(workspace_id=wid, user_id=uid, role=found.role))
            found.status = "ACCEPTED"
            found.accepted_by = uid
            found.accepted_at = datetime.now(UTC)
            return WorkspaceView(w.id, w.name, found.role)

    async def change_role(self, uid: UUID, wid: UUID, target: UUID, role: str) -> MemberView:
        async with transaction(self.ready()) as s:
            await require(s, uid, wid, "owner")
            m = await store.member(s, wid, target)
            if not m or m.status != "ACTIVE":
                raise WorkspaceMissing()
            if m.role == "OWNER":
                raise WorkspaceConflict("OWNER_TRANSFER_REQUIRED")
            await UserAPI(s).get_active_user(target)
            m.role = role
            return MemberView(target, role)

    async def remove(self, uid: UUID, wid: UUID, target: UUID) -> None:
        async with transaction(self.ready()) as s:
            actor = await require(s, uid, wid, "read" if uid == target else "manage")
            m = await store.member(s, wid, target)
            if not m or m.status != "ACTIVE":
                raise WorkspaceMissing()
            if m.role == "OWNER":
                raise WorkspaceConflict("OWNER_TRANSFER_REQUIRED")
            if uid != target and m.role == "ADMIN" and actor.role != "OWNER":
                raise PermissionDenied()
            m.status = "LEFT" if uid == target else "REMOVED"
            m.ended_at = datetime.now(UTC)

    async def transfer(self, uid: UUID, wid: UUID, target: UUID) -> MemberView:
        async with transaction(self.ready()) as s:
            owner = await require(s, uid, wid, "owner")
            m = await store.member(s, wid, target)
            if not m or m.status != "ACTIVE":
                raise WorkspaceMissing()
            if uid == target:
                raise WorkspaceConflict()
            await UserAPI(s).get_active_user(target)
            owner.role = "ADMIN"
            await s.flush()
            m.role = "OWNER"
            return MemberView(target, "OWNER")
