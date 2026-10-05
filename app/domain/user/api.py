from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.user.dto import GitHubIdentity as GitHubIdentity
from app.domain.user.dto import UserSnapshot as UserSnapshot
from app.domain.user.models import User
from app.domain.user.service import get_active, set_review_mode, snapshot, upsert_identity
from app.shared.review_mode import ReviewMode


class UserAPI:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_active_user(self, user_id: UUID) -> UserSnapshot:
        return await get_active(self.session, user_id)

    async def profiles(self, user_ids: list[UUID]) -> dict[UUID, UserSnapshot]:
        users = await self.session.scalars(
            select(User).where(User.id.in_(user_ids[:51]), User.status == "ACTIVE")
        )
        return {u.id: snapshot(u) for u in users}

    async def upsert_github_identity(self, identity: GitHubIdentity) -> UserSnapshot:
        return await upsert_identity(self.session, identity)

    async def set_review_mode(self, user_id: UUID, mode: ReviewMode) -> UserSnapshot:
        return await set_review_mode(self.session, user_id, mode)
