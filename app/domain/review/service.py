import hashlib
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.domain.analysis.api import require_review_read, review_snapshot
from app.domain.repository.api import RepositoryAccess
from app.domain.review.models import ReviewRun
from app.domain.review.policy import POLICY, PROMPT
from app.domain.workspace.api import WorkspaceAccess
from app.shared.config.settings import Settings
from app.shared.database.engine import transaction
from app.shared.exception.base import AppException, ErrorKind
from app.shared.jobs.models import Job
from app.shared.jobs.store import enqueue

TERMINAL = ("COMPLETED", "FAILED", "CANCELED")


def error(code: str, kind: ErrorKind = ErrorKind.CONFLICT) -> AppException:
    return AppException(code, "AI 리뷰 요청·권한·실행 한도를 확인해 주세요.", kind)


async def get_row(s: AsyncSession, wid: UUID, rid: UUID) -> ReviewRun:
    row = await s.scalar(
        select(ReviewRun)
        .where(ReviewRun.workspace_id == wid, ReviewRun.id == rid)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if not row:
        raise error("REVIEW_NOT_FOUND", ErrorKind.NOT_FOUND)
    return row


async def authorize(
    s: AsyncSession, uid: UUID, wid: UUID, rid: UUID, execute: bool = False
) -> ReviewRun:
    await WorkspaceAccess(s).require_permission(uid, wid, "owner" if execute else "read")
    row = await get_row(s, wid, rid)
    repo = await RepositoryAccess(s).require(uid, wid, row.repository_connection_id, active=execute)
    if execute and repo.connection_generation != row.connection_generation:
        raise error("ACCESS_REVOKED")
    return row


class ReviewService:
    def __init__(self, engine: AsyncEngine | None, settings: Settings) -> None:
        self.engine, self.settings = engine, settings

    def ready(self) -> AsyncEngine:
        if self.engine is None:
            raise error("DATABASE_UNAVAILABLE", ErrorKind.UNAVAILABLE)
        return self.engine

    async def start(
        self, uid: UUID, wid: UUID, aid: UUID, consent: bool, rerun: UUID | None
    ) -> ReviewRun:
        if not self.settings.ai_enabled:
            raise error("AI_DISABLED", ErrorKind.UNAVAILABLE)
        if not consent:
            raise error("AI_CONSENT_REQUIRED", ErrorKind.INVALID_INPUT)
        async with transaction(self.ready()) as s:
            await WorkspaceAccess(s).require_permission(uid, wid, "owner")
            snap = await review_snapshot(s, uid, wid, aid)
            conditions = (
                ReviewRun.workspace_id == wid,
                ReviewRun.analysis_id == aid,
                ReviewRun.model == self.settings.deepseek_model,
                ReviewRun.prompt_version == PROMPT,
                ReviewRun.policy_version == POLICY,
            )
            generation = 0
            if rerun:
                previous = await get_row(s, wid, rerun)
                if previous.analysis_id != aid or previous.status not in TERMINAL:
                    raise error("INVALID_RERUN")
                generation = (
                    await s.scalar(select(func.max(ReviewRun.generation)).where(*conditions)) or 0
                ) + 1
            key = hashlib.sha256(
                f"{wid}:{aid}:{snap.connection_generation}:{self.settings.deepseek_model}:{PROMPT}:{POLICY}:{generation}".encode()
            ).hexdigest()
            existing = await s.scalar(select(ReviewRun).where(ReviewRun.execution_key == key))
            if existing:
                return existing
            if await s.scalar(
                select(ReviewRun.id)
                .where(ReviewRun.workspace_id == wid, ReviewRun.status.in_(("PENDING", "RUNNING")))
                .limit(1)
            ):
                raise error("REVIEW_IN_PROGRESS")
            now = datetime.now(UTC)
            used = await s.scalar(
                select(func.count())
                .select_from(ReviewRun)
                .where(
                    ReviewRun.workspace_id == wid,
                    ReviewRun.created_at >= now.replace(hour=0, minute=0, second=0, microsecond=0),
                )
            )
            if (used or 0) >= self.settings.ai_daily_limit:
                raise error("AI_DAILY_LIMIT")
            row = ReviewRun(
                workspace_id=wid,
                analysis_id=aid,
                pr_id=snap.pr_id,
                repository_connection_id=snap.repository_id,
                connection_generation=snap.connection_generation,
                requested_by=uid,
                head_sha=snap.head_sha,
                model=self.settings.deepseek_model,
                prompt_version=PROMPT,
                policy_version=POLICY,
                generation=generation,
                execution_key=key,
                consented_at=now,
            )
            s.add(row)
            await s.flush()
            await enqueue(s, "EXPLAIN_FINDINGS", row.id, wid)
            return row

    async def history(self, uid: UUID, wid: UUID, aid: UUID) -> list[ReviewRun]:
        async with transaction(self.ready()) as s:
            # Historical results remain readable after disconnect, just like static results.
            await require_review_read(s, uid, wid, aid)
            return list(
                (
                    await s.scalars(
                        select(ReviewRun)
                        .where(ReviewRun.workspace_id == wid, ReviewRun.analysis_id == aid)
                        .order_by(ReviewRun.created_at.desc(), ReviewRun.id.desc())
                        .limit(50)
                    )
                ).all()
            )

    async def get(self, uid: UUID, wid: UUID, rid: UUID) -> ReviewRun:
        async with transaction(self.ready()) as s:
            return await authorize(s, uid, wid, rid)

    async def cancel(self, uid: UUID, wid: UUID, rid: UUID) -> ReviewRun:
        async with transaction(self.ready()) as s:
            row = await authorize(s, uid, wid, rid, True)
            if row.status in TERMINAL:
                return row
            job = await s.scalar(
                select(Job)
                .where(Job.kind == "EXPLAIN_FINDINGS", Job.aggregate_id == rid)
                .with_for_update()
            )
            assert job
            now = datetime.now(UTC)
            row.status, row.finished_at, row.error_code = "CANCELED", now, "USER_CANCELED"
            row.usage_uncertain = row.call_attempts > 0
            job.state, job.completed_at, job.lease_until, job.claimed_by = (
                "CANCELED",
                now,
                None,
                None,
            )
            job.error_code = "USER_CANCELED"
            if job.attempt_history:
                history = [dict(h) for h in job.attempt_history]
                history[-1].update(
                    finished_at=now.isoformat(), outcome="CANCELED", error_code="USER_CANCELED"
                )
                job.attempt_history = history
            return row
