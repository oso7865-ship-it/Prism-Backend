from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.user.dto import GitHubIdentity as GitHubIdentity
from app.domain.user.dto import UserSnapshot as UserSnapshot
from app.domain.user.service import get_active, upsert_identity


class UserAPI:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_active_user(self, user_id: UUID) -> UserSnapshot:
        return await get_active(self.session, user_id)

    async def upsert_github_identity(self, identity: GitHubIdentity) -> UserSnapshot:
        return await upsert_identity(self.session, identity)
