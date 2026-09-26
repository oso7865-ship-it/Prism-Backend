import hashlib
import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.domain.repository import repository as store
from app.domain.repository.dto import RepositorySnapshot, VerifiedRepository
from app.domain.repository.models import RepositoryConnection, RuleConfigVersion
from app.domain.workspace.api import WorkspaceAccess
from app.shared.database.engine import transaction
from app.shared.exception.base import AppException, ErrorKind


def snapshot(r: RepositoryConnection) -> RepositorySnapshot:
    return RepositorySnapshot(
        r.id,
        r.workspace_id,
        r.github_repository_id,
        r.installation_id,
        r.owner_login,
        r.repository_name,
        r.status,
        r.connection_generation,
        r.last_sync_success_at,
    )


async def access(
    s: AsyncSession, uid: UUID, wid: UUID, rid: UUID, permission: str = "read", active: bool = False
) -> RepositoryConnection:
    await WorkspaceAccess(s).require_permission(uid, wid, permission)
    r = await store.get(s, wid, rid)
    if not r:
        raise AppException(
            "REPOSITORY_NOT_FOUND", "저장소를 찾을 수 없습니다.", ErrorKind.NOT_FOUND
        )
    if active and r.status != "ACTIVE":
        raise AppException(
            "REPOSITORY_INACTIVE", "저장소를 다시 연결해 주세요.", ErrorKind.CONFLICT
        )
    return r


async def connect(
    s: AsyncSession, uid: UUID, wid: UUID, verified: VerifiedRepository
) -> RepositorySnapshot:
    await WorkspaceAccess(s).require_permission(uid, wid, "manage")
    row = await store.by_github(s, wid, verified.github_repository_id)
    if row and row.status != "DISCONNECTED":
        raise AppException("REPOSITORY_EXISTS", "이미 연결된 저장소입니다.", ErrorKind.CONFLICT)
    rid = row.id if row else uuid4()
    cid = uuid4()
    if row:
        row.connection_generation += 1
        row.status = "ACTIVE"
        row.disconnected_at = None
        row.connected_at = datetime.now(UTC)
        row.connected_by = uid
        row.installation_id = verified.installation_id
        row.owner_login = verified.owner_login
        row.repository_name = verified.repository_name
        row.is_private = verified.is_private
        row.default_branch = verified.default_branch
    # Reconnection keeps its last immutable config and opt-in policy.
    else:
        row = RepositoryConnection(
            id=rid,
            workspace_id=wid,
            github_repository_id=verified.github_repository_id,
            installation_id=verified.installation_id,
            owner_login=verified.owner_login,
            repository_name=verified.repository_name,
            is_private=verified.is_private,
            default_branch=verified.default_branch,
            connected_by=uid,
            current_config_version_id=cid,
        )
        s.add(row)
        config = {
            "rules": {},
            "layer_mappings": {},
            "ignored_paths": [],
            "auto_analysis_enabled": False,
            "ai_mode": "OFF",
            "schema_version": 1,
        }
        digest = hashlib.sha256(
            json.dumps(config, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        s.add(
            RuleConfigVersion(
                id=cid,
                workspace_id=wid,
                repository_connection_id=rid,
                version=1,
                created_by=uid,
                config_digest=digest,
            )
        )
    await s.flush()
    return snapshot(row)


class RepositoryService:
    def __init__(self, engine: "AsyncEngine | None") -> None:
        self.engine = engine

    def ready(self) -> "AsyncEngine":
        if not self.engine:
            raise AppException(
                "DATABASE_UNAVAILABLE", "데이터베이스 연결이 필요합니다.", ErrorKind.UNAVAILABLE
            )
        return self.engine

    async def listing(self, uid: UUID, wid: UUID, cursor: UUID | None) -> list[RepositorySnapshot]:
        async with transaction(self.ready()) as s:
            await WorkspaceAccess(s).require_permission(uid, wid, "read")
            return [snapshot(row) for row in await store.listing(s, wid, cursor)]

    async def disconnect(self, uid: UUID, wid: UUID, rid: UUID) -> None:
        async with transaction(self.ready()) as s:
            row = await access(s, uid, wid, rid, "manage")
            row.status = "DISCONNECTED"
            row.disconnected_at = datetime.now(UTC)
