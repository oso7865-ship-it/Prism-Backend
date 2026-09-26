from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.workspace.service import require


class WorkspaceAccess:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def require_permission(self, user_id: UUID, workspace_id: UUID, permission: str) -> str:
        return (await require(self.session, user_id, workspace_id, permission)).role

    async def lock_system(self, workspace_id: UUID) -> bool:
        """Internal event workers only; does not authorize an HTTP user."""
        from app.domain.workspace.repository import lock_workspace

        row = await lock_workspace(self.session, workspace_id)
        return bool(row and row.status == "ACTIVE")
