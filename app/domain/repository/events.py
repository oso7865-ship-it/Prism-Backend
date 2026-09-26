from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repository import repository as store
from app.domain.repository.dto import RepositorySnapshot
from app.domain.repository.service import snapshot
from app.domain.workspace.api import WorkspaceAccess
from app.shared.exception.base import AppException, ErrorKind


class RepositoryEvents:
    """Internal trusted delivery mapping, never exposed as user authorization."""

    def __init__(self, session: AsyncSession) -> None:
        self.s = session

    async def mapped(self, installation: int, gid: int) -> RepositorySnapshot | None:
        row = await store.event_mapping(self.s, installation, gid)
        if not row:
            return None
        return await self.require(row.workspace_id, row.id, row.connection_generation)

    async def require(self, wid: UUID, rid: UUID, generation: int) -> RepositorySnapshot:
        active = await WorkspaceAccess(self.s).lock_system(wid)
        row = await store.get(self.s, wid, rid)
        if (
            not active
            or not row
            or row.status != "ACTIVE"
            or row.connection_generation != generation
        ):
            raise AppException("CONNECTION_CHANGED", "연결이 변경되었습니다.", ErrorKind.CONFLICT)
        return snapshot(row)

    async def lock_affected(
        self, installation: int, ids: list[int] | None, before: datetime
    ) -> list[UUID]:
        candidates = await store.event_candidates(self.s, installation, ids, before)
        result = []
        for candidate in candidates:
            await WorkspaceAccess(self.s).lock_system(candidate.workspace_id)
            row = await store.get(self.s, candidate.workspace_id, candidate.id)
            if row:
                await self.s.refresh(row)
            if (
                row
                and row.status == "ACTIVE"
                and row.installation_id == installation
                and row.connected_at <= before
            ):
                result.append(row.id)
        return result

    async def suspend_locked(self, ids: list[UUID]) -> None:
        for rid in ids:
            row = await store.event_by_id(self.s, rid)
            if row and row.status == "ACTIVE":
                row.status = "SUSPENDED"

    async def sync_success(self, wid: UUID, rid: UUID, generation: int, at: datetime) -> None:
        await self.require(wid, rid, generation)
        row = await store.get(self.s, wid, rid)
        assert row
        row.last_sync_success_at = at
