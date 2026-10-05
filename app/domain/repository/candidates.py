"""Short-lived candidate lists for choose-from-GitHub repository connection."""

from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repository.dto import CandidateList, CandidateRepository
from app.domain.repository.models import RepositoryCandidateSet, RepositoryConnection

TTL = timedelta(minutes=15)


async def save(s: AsyncSession, uid: UUID, wid: UUID, found: CandidateList) -> None:
    """Replace this user's list for the team; expired lists of anyone are removed."""
    now = datetime.now(UTC)
    await s.execute(
        delete(RepositoryCandidateSet).where(
            (RepositoryCandidateSet.expires_at <= now)
            | (
                (RepositoryCandidateSet.workspace_id == wid)
                & (RepositoryCandidateSet.user_id == uid)
            )
        )
    )
    s.add(
        RepositoryCandidateSet(
            id=uuid4(),
            workspace_id=wid,
            user_id=uid,
            expires_at=now + TTL,
            truncated=found.truncated,
            skipped_installations=found.skipped_installations,
            items=[asdict(item) for item in found.items],
        )
    )
    await s.flush()


async def load(
    s: AsyncSession, uid: UUID, wid: UUID
) -> tuple[RepositoryCandidateSet, list[CandidateRepository]] | None:
    row = await s.scalar(
        select(RepositoryCandidateSet).where(
            RepositoryCandidateSet.workspace_id == wid,
            RepositoryCandidateSet.user_id == uid,
            RepositoryCandidateSet.expires_at > datetime.now(UTC),
        )
    )
    if row is None:
        return None
    return row, [CandidateRepository(**item) for item in row.items]  # type: ignore[arg-type]


async def connection_states(
    s: AsyncSession, wid: UUID, github_ids: list[int]
) -> tuple[set[int], set[int]]:
    """Return (connected in this team, active in another team) among the given repositories."""
    if not github_ids:
        return set(), set()
    rows = (
        await s.execute(
            select(
                RepositoryConnection.github_repository_id,
                RepositoryConnection.workspace_id,
                RepositoryConnection.status,
            ).where(
                RepositoryConnection.github_repository_id.in_(github_ids),
                RepositoryConnection.status.in_(("ACTIVE", "SUSPENDED")),
            )
        )
    ).all()
    here = {gid for gid, w, _ in rows if w == wid}
    elsewhere = {gid for gid, w, _ in rows if w != wid}
    return here, elsewhere - here
