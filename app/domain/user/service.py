from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.user import repository
from app.domain.user.dto import GitHubIdentity, UserSnapshot
from app.domain.user.exceptions import UserUnavailable
from app.domain.user.models import User


def snapshot(user: User) -> UserSnapshot:
    return UserSnapshot(
        user.id, user.github_user_id, user.login, user.display_name, user.avatar_url
    )


async def upsert_identity(session: AsyncSession, identity: GitHubIdentity) -> UserSnapshot:
    user = await repository.upsert(session, identity)
    if user.status != "ACTIVE":
        raise UserUnavailable()
    return snapshot(user)


async def get_active(session: AsyncSession, user_id: UUID) -> UserSnapshot:
    user = await repository.active(session, user_id)
    if user is None:
        raise UserUnavailable()
    return snapshot(user)
