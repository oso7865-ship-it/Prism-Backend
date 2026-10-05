from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repository import candidates as candidate_store
from app.domain.repository.dto import (
    CandidateList as CandidateList,
)
from app.domain.repository.dto import (
    CandidateRepository as CandidateRepository,
)
from app.domain.repository.dto import (
    CandidateView as CandidateView,
)
from app.domain.repository.dto import (
    RepositorySnapshot as RepositorySnapshot,
)
from app.domain.repository.dto import (
    VerifiedRepository as VerifiedRepository,
)
from app.domain.repository.events import RepositoryEvents as RepositoryEvents
from app.domain.repository.service import access, connect, snapshot
from app.domain.workspace.api import WorkspaceAccess
from app.shared.exception.base import AppException, ErrorKind


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

    async def save_candidates(self, uid: UUID, wid: UUID, found: CandidateList) -> None:
        await WorkspaceAccess(self.session).require_permission(uid, wid, "manage")
        await candidate_store.save(self.session, uid, wid, found)

    async def candidates(self, uid: UUID, wid: UUID) -> CandidateView:
        """The caller's own list with a connect state per repository."""
        await WorkspaceAccess(self.session).require_permission(uid, wid, "manage")
        loaded = await candidate_store.load(self.session, uid, wid)
        if loaded is None:
            raise AppException(
                "CANDIDATES_NOT_FOUND",
                "목록이 만료됐어요. 저장소 연결을 다시 눌러 주세요.",
                ErrorKind.NOT_FOUND,
            )
        row, items = loaded
        here, elsewhere = await candidate_store.connection_states(
            self.session, wid, [item.github_repository_id for item in items]
        )

        def state(item: CandidateRepository) -> str:
            if item.github_repository_id in here:
                return "CONNECTED"
            if item.github_repository_id in elsewhere:
                return "OTHER_TEAM"
            return "AVAILABLE" if item.admin else "ADMIN_REQUIRED"

        ordered = sorted(items, key=lambda i: (i.owner_login.lower(), i.repository_name.lower()))
        return CandidateView(
            row.expires_at,
            row.truncated,
            row.skipped_installations,
            [(item, state(item)) for item in ordered],
        )

    async def candidate_map(self, uid: UUID, wid: UUID) -> dict[int, CandidateRepository]:
        await WorkspaceAccess(self.session).require_permission(uid, wid, "manage")
        loaded = await candidate_store.load(self.session, uid, wid)
        if loaded is None:
            raise AppException(
                "CANDIDATES_NOT_FOUND",
                "목록이 만료됐어요. 저장소 연결을 다시 눌러 주세요.",
                ErrorKind.NOT_FOUND,
            )
        return {item.github_repository_id: item for item in loaded[1]}

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
