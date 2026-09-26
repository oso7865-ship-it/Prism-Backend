import re
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.domain.analysis.contracts import RULE_SET, build_digest, digest
from app.domain.analysis.models import AnalysisFileResult, AnalysisRun, Finding
from app.domain.pull_request.api import analysis_snapshot
from app.domain.repository.api import RepositoryAccess
from app.domain.workspace.api import WorkspaceAccess
from app.shared.database.engine import transaction
from app.shared.exception.base import AppException, ErrorKind
from app.shared.jobs.models import Job
from app.shared.jobs.store import enqueue

TERMINAL = ("COMPLETED", "FAILED", "CANCELED")


def error(code: str, kind: ErrorKind = ErrorKind.CONFLICT) -> AppException:
    return AppException(code, "분석 요청 또는 접근 상태를 확인해 주세요.", kind)


async def find_run(s: AsyncSession, wid: UUID, aid: UUID) -> AnalysisRun:
    row = await s.scalar(
        select(AnalysisRun)
        .where(AnalysisRun.id == aid, AnalysisRun.workspace_id == wid)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if not row:
        raise error("ANALYSIS_NOT_FOUND", ErrorKind.NOT_FOUND)
    return row


async def authorized(
    s: AsyncSession, uid: UUID, wid: UUID, aid: UUID, active: bool = False
) -> AnalysisRun:
    await WorkspaceAccess(s).require_permission(uid, wid, "read")
    row = await find_run(s, wid, aid)
    repo = await RepositoryAccess(s).require(uid, wid, row.repository_connection_id, active=active)
    if active and repo.connection_generation != row.connection_generation:
        raise error("CONNECTION_CHANGED")
    return row


class AnalysisService:
    def __init__(self, engine: AsyncEngine | None, enabled: bool) -> None:
        self.engine, self.enabled = engine, enabled

    def ready(self) -> AsyncEngine:
        if self.engine is None:
            raise error("DATABASE_UNAVAILABLE", ErrorKind.UNAVAILABLE)
        return self.engine

    async def start(self, uid: UUID, wid: UUID, pid: UUID, rerun_of: UUID | None) -> AnalysisRun:
        if not self.enabled:
            raise error("ANALYSIS_RUNNER_DISABLED", ErrorKind.UNAVAILABLE)
        async with transaction(self.ready()) as s:
            pr = await analysis_snapshot(s, uid, wid, pid)
            repo = await RepositoryAccess(s).require(uid, wid, pr.repository_connection_id, "sync")
            config, config_digest, _ = await RepositoryAccess(s).analysis_config(uid, wid, repo.id)
            base, head = pr.base_sha, pr.head_sha
            generation = 0
            if rerun_of:
                previous = await find_run(s, wid, rerun_of)
                if (
                    previous.pr_id != pid
                    or previous.repository_connection_id != repo.id
                    or previous.connection_generation != repo.connection_generation
                    or previous.status not in TERMINAL
                ):
                    raise error("INVALID_RERUN")
                base, head = previous.base_sha, previous.head_sha
            if (
                not base
                or not head
                or not re.fullmatch("[0-9a-f]{40}", base)
                or not re.fullmatch("[0-9a-f]{40}", head)
            ):
                raise error("PR_SNAPSHOT_REQUIRED")
            build = build_digest()
            inputs = {
                "workspace_id": wid,
                "repository_connection_id": repo.id,
                "connection_generation": repo.connection_generation,
                "pr_id": pid,
                "base_sha": base,
                "head_sha": head,
                "merge_base_sha": None,
                "rule_set_version": RULE_SET,
                "config_version_id": config,
                "effective_config_digest": config_digest,
                "analyzer_build_digest": build,
                "scope": "PR_CHANGED_FILES",
            }
            if rerun_of:
                maximum = await s.scalar(
                    select(func.max(AnalysisRun.generation)).where(
                        *(getattr(AnalysisRun, k) == v for k, v in inputs.items())
                    )
                )
                generation = (maximum or 0) + 1
            key = digest({**inputs, "generation": generation})
            existing = await s.scalar(select(AnalysisRun).where(AnalysisRun.execution_key == key))
            if existing:
                return existing
            # Bound queued work from repeated explicit reruns and concurrent HTTP requests.
            active = await s.scalar(
                select(AnalysisRun.id).where(
                    AnalysisRun.pr_id == pid,
                    AnalysisRun.workspace_id == wid,
                    AnalysisRun.status.in_(("PENDING", "RUNNING")),
                )
            )
            if active:
                raise error("ANALYSIS_IN_PROGRESS")
            row = AnalysisRun(
                **inputs,
                generation=generation,
                execution_key=key,
                requested_by=uid,
                actor_type="USER",
            )
            s.add(row)
            await s.flush()
            await enqueue(s, "ANALYZE_PR", row.id, wid)
            return row

    async def get(self, uid: UUID, wid: UUID, aid: UUID) -> AnalysisRun:
        async with transaction(self.ready()) as s:
            return await authorized(s, uid, wid, aid)

    async def history(self, uid: UUID, wid: UUID, pid: UUID) -> list[AnalysisRun]:
        async with transaction(self.ready()) as s:
            await analysis_snapshot(s, uid, wid, pid)
            return list(
                (
                    await s.scalars(
                        select(AnalysisRun)
                        .where(AnalysisRun.workspace_id == wid, AnalysisRun.pr_id == pid)
                        .order_by(AnalysisRun.created_at.desc(), AnalysisRun.id.desc())
                        .limit(50)
                    )
                ).all()
            )

    async def results(
        self, uid: UUID, wid: UUID, aid: UUID, kind: str, cursor: UUID | None
    ) -> list[AnalysisFileResult] | list[Finding]:
        async with transaction(self.ready()) as s:
            await authorized(s, uid, wid, aid)
            model = Finding if kind == "findings" else AnalysisFileResult
            query = (
                select(model).where(model.workspace_id == wid, model.analysis_id == aid).limit(101)
            )
            if kind == "findings":
                ranks = {"CRITICAL": 0, "ERROR": 1, "WARNING": 2, "INFO": 3}
                rank = case(ranks, value=Finding.severity, else_=4)
                query = query.order_by(rank, model.id)
                if cursor:
                    previous = await s.scalar(
                        select(Finding).where(
                            Finding.workspace_id == wid,
                            Finding.analysis_id == aid,
                            Finding.id == cursor,
                        )
                    )
                    if previous is None:
                        raise error("INVALID_CURSOR", ErrorKind.INVALID_INPUT)
                    position = ranks[previous.severity]
                    query = query.where(
                        or_(rank > position, (rank == position) & (model.id > cursor))
                    )
            else:
                query = query.order_by(model.id)
                if cursor:
                    query = query.where(model.id > cursor)
            return list((await s.scalars(query)).all())  # type: ignore[return-value]

    async def cancel(self, uid: UUID, wid: UUID, aid: UUID) -> AnalysisRun:
        async with transaction(self.ready()) as s:
            row = await authorized(s, uid, wid, aid)
            if row.requested_by != uid:
                await WorkspaceAccess(s).require_permission(uid, wid, "manage")
            if row.status in TERMINAL:
                return row
            job = await s.scalar(
                select(Job)
                .where(Job.kind == "ANALYZE_PR", Job.aggregate_id == aid)
                .with_for_update()
            )
            if not job:
                raise error("JOB_NOT_FOUND")
            now = datetime.now(UTC)
            if job.state == "LEASED" and job.attempt_history:
                history = [dict(item) for item in job.attempt_history]
                history[-1].update(
                    finished_at=now.isoformat(), outcome="CANCELED", error_code="USER_CANCELED"
                )
                job.attempt_history = history
            job.state, job.completed_at, job.lease_until, job.claimed_by = (
                "CANCELED",
                now,
                None,
                None,
            )
            job.error_code = "USER_CANCELED"
            row.status, row.finished_at, row.error_code = "CANCELED", now, "USER_CANCELED"
            return row
