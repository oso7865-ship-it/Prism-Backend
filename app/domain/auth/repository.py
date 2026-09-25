from datetime import datetime
from uuid import UUID

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.auth.models import LoginAttempt, RefreshSession


async def consume_login(
    session: AsyncSession, state_hash: str, binding_hash: str, now: datetime
) -> bool:
    result = await session.execute(
        update(LoginAttempt)
        .where(
            LoginAttempt.state_hash == state_hash,
            LoginAttempt.browser_binding_hash == binding_hash,
            LoginAttempt.purpose == "OAUTH_LOGIN",
            LoginAttempt.consumed_at.is_(None),
            LoginAttempt.expires_at > now,
        )
        .values(consumed_at=now)
        .returning(LoginAttempt.id)
    )
    return result.scalar_one_or_none() is not None


async def lock_refresh(session: AsyncSession, token_hash: str) -> RefreshSession | None:
    family = await session.scalar(
        select(RefreshSession.family_id).where(RefreshSession.token_hash == token_hash)
    )
    if family is None:
        return None
    # Every rotation/revocation uses the same transaction-scoped family lock.
    lock_id = int.from_bytes(family.bytes[:8], signed=True)
    await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_id})
    return (
        await session.scalars(
            select(RefreshSession).where(RefreshSession.token_hash == token_hash).with_for_update()
        )
    ).one_or_none()


async def revoke_family(session: AsyncSession, family: UUID, now: datetime, reason: str) -> None:
    await session.execute(
        update(RefreshSession)
        .where(
            RefreshSession.family_id == family,
            RefreshSession.revoked_at.is_(None),
        )
        .values(revoked_at=now, revoke_reason=reason)
    )
