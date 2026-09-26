import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.jobs.models import Job


@dataclass(frozen=True)
class Claim:
    id: UUID
    aggregate_id: UUID
    workspace_id: UUID | None
    kind: str
    generation: int
    worker: str


async def enqueue(s: AsyncSession, kind: str, aggregate: UUID, wid: UUID | None) -> None:
    s.add(
        Job(
            kind=kind,
            aggregate_id=aggregate,
            workspace_id=wid,
            dedupe_key=hashlib.sha256(f"{kind}:{aggregate}:{wid}".encode()).hexdigest(),
            max_attempts=3,
        )
    )


async def claim(s: AsyncSession, worker: str, kinds: list[str]) -> Claim | None:
    now = datetime.now(UTC)
    j = (
        await s.scalars(
            select(Job)
            .where(Job.state == "READY", Job.available_at <= now, Job.kind.in_(kinds))
            .order_by(Job.available_at, Job.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
    ).one_or_none()
    if not j:
        return None
    j.state = "LEASED"
    j.attempts += 1
    j.lease_generation += 1
    j.claimed_by = worker
    j.lease_until = now + timedelta(seconds=60)
    j.attempt_history = [
        *j.attempt_history,
        {
            "attempt": j.attempts,
            "generation": j.lease_generation,
            "started_at": now.isoformat(),
            "finished_at": None,
            "outcome": None,
            "error_code": None,
        },
    ]
    await s.flush()
    return Claim(j.id, j.aggregate_id, j.workspace_id, j.kind, j.lease_generation, worker)


async def fence(s: AsyncSession, c: Claim, expired: bool = False) -> Job | None:
    j = (await s.scalars(select(Job).where(Job.id == c.id).with_for_update())).one_or_none()
    now = datetime.now(UTC)
    if (
        not j
        or j.state != "LEASED"
        or j.lease_generation != c.generation
        or j.claimed_by != c.worker
        or not j.lease_until
    ):
        return None
    if (j.lease_until <= now) != expired:
        return None
    return j


async def expired(s: AsyncSession, kinds: list[str]) -> list[Claim]:
    rows = (
        await s.scalars(
            select(Job)
            .where(Job.state == "LEASED", Job.lease_until <= datetime.now(UTC), Job.kind.in_(kinds))
            .limit(50)
        )
    ).all()
    return [
        Claim(j.id, j.aggregate_id, j.workspace_id, j.kind, j.lease_generation, j.claimed_by or "")
        for j in rows
    ]


def finish(j: Job, code: str | None = None, retry: bool = False, delay: int = 5) -> str:
    now = datetime.now(UTC)
    again = bool(code and retry and j.attempts < j.max_attempts)
    j.state = "READY" if again else "DEAD" if code else "SUCCEEDED"
    j.error_code = code
    j.lease_until = None
    j.claimed_by = None
    j.completed_at = None if again else now
    if again:
        j.available_at = now + timedelta(seconds=max(delay, 5 if j.attempts == 1 else 30))
    history = [dict(item) for item in j.attempt_history]
    history[-1].update(
        finished_at=now.isoformat(),
        outcome="RETRY" if again else "FAILED" if code else "SUCCEEDED",
        error_code=code,
    )
    j.attempt_history = history
    return j.state


async def heartbeat(session: AsyncSession, current: Claim) -> bool:
    job = await fence(session, current)
    if not job:
        return False
    job.lease_until = datetime.now(UTC) + timedelta(seconds=60)
    return True
