from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repository.dto import (
    RepositorySnapshot as RepositorySnapshot,
)
from app.domain.repository.dto import (
    VerifiedRepository as VerifiedRepository,
)
from app.domain.repository.events import RepositoryEvents as RepositoryEvents
from app.domain.repository.service import access, connect, snapshot


class RepositoryAccess:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def require(
        self, uid: UUID, wid: UUID, rid: UUID, permission: str = "read", active: bool = True
    ) -> RepositorySnapshot:
        return snapshot(await access(self.session, uid, wid, rid, permission, active))

    async def connect(
        self, uid: UUID, wid: UUID, verified: VerifiedRepository
    ) -> RepositorySnapshot:
        return await connect(self.session, uid, wid, verified)

    async def sync_success(self, uid: UUID, wid: UUID, rid: UUID, at: datetime) -> None:
        row = await access(self.session, uid, wid, rid, "sync", True)
        row.last_sync_success_at = at

    async def suspend(self, uid: UUID, wid: UUID, rid: UUID) -> None:
        row = await access(self.session, uid, wid, rid)
        if row.status == "ACTIVE":
            row.status = "SUSPENDED"

    async def analysis_config(
        self, uid: UUID, wid: UUID, rid: UUID, version: UUID | None = None
    ) -> tuple[UUID, str, list[str]]:
        from sqlalchemy import select

        from app.domain.repository.models import RuleConfigVersion
        from app.shared.exception.base import AppException, ErrorKind

        row = await access(self.session, uid, wid, rid, "sync", True)
        config = await self.session.scalar(
            select(RuleConfigVersion).where(
                RuleConfigVersion.id == (version or row.current_config_version_id),
                RuleConfigVersion.workspace_id == wid,
                RuleConfigVersion.repository_connection_id == rid,
            )
        )
        if not config or config.rules or config.layer_mappings:
            raise AppException(
                "CONFIG_UNSUPPORTED", "이 분석기의 기본 규칙 설정만 지원합니다.", ErrorKind.CONFLICT
            )
        return config.id, config.config_digest, list(config.ignored_paths)
