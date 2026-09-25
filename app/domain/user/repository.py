from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.user.dto import GitHubIdentity
from app.domain.user.models import User


async def upsert(session: AsyncSession, identity: GitHubIdentity) -> User:
    statement = insert(User).values(
        github_user_id=identity.github_user_id,
        login=identity.login,
        display_name=identity.display_name,
        avatar_url=identity.avatar_url,
    )
    statement = statement.on_conflict_do_update(
        index_elements=[User.github_user_id],
        set_={
            "login": statement.excluded.login,
            "display_name": statement.excluded.display_name,
            "avatar_url": statement.excluded.avatar_url,
            "updated_at": statement.excluded.updated_at,
        },
    )
    return (await session.scalars(statement.returning(User))).one()


async def active(session: AsyncSession, user_id: UUID) -> User | None:
    return (
        await session.scalars(
            select(User)
            .where(User.id == user_id, User.status == "ACTIVE")
            .with_for_update(read=True)
        )
    ).one_or_none()
