import asyncio
from datetime import UTC, datetime
from typing import cast

from sqlalchemy.ext.asyncio import AsyncEngine

from app.domain.analysis.contracts import RULE_SET, build_digest
from app.domain.analysis.models import AnalysisFileResult, Finding
from app.domain.analysis.pipeline import Result, Snapshot, analyze
from app.domain.analysis.service import TERMINAL, authorized, error, find_run
from app.domain.pull_request.api import analysis_snapshot
from app.domain.repository.api import RepositoryAccess
from app.domain.workspace.api import WorkspaceAccess
from app.shared.database.engine import transaction
from app.shared.exception.base import AppException
from app.shared.github.client import GitHubClient, GitHubFailure
from app.shared.jobs import store as jobs
from app.shared.jobs.store import Claim


class AnalysisWorker:
    def __init__(self, engine: AsyncEngine, github: GitHubClient) -> None:
        self.engine, self.github = engine, github

    async def checkpoint(self, c: Claim) -> None:
        assert c.workspace_id
        async with transaction(self.engine) as s:
            # Same lock order everywhere: workspace -> repository/run -> job.
            if not await WorkspaceAccess(s).lock_system(c.workspace_id):
                raise error("ACCESS_REVOKED")
            row = await find_run(s, c.workspace_id, c.aggregate_id)
            if row.status in TERMINAL:
                raise error("ANALYSIS_CANCELED")
            assert row.requested_by
            await authorized(s, row.requested_by, row.workspace_id, row.id, active=True)
            if not await jobs.fence(s, c):
                raise error("LEASE_LOST")

    async def execute(self, c: Claim, expired: bool = False) -> None:
        if expired:
            await self.complete(c, None, "LEASE_EXPIRED", True, expired=True)
            return
        assert c.workspace_id
        try:
            async with transaction(self.engine) as s:
                if not await WorkspaceAccess(s).lock_system(c.workspace_id):
                    raise error("ACCESS_REVOKED")
                row = await find_run(s, c.workspace_id, c.aggregate_id)
                if row.status in TERMINAL or not await jobs.fence(s, c):
                    return
                assert row.requested_by
                await authorized(s, row.requested_by, row.workspace_id, row.id, active=True)
                repo = await RepositoryAccess(s).require(
                    row.requested_by, row.workspace_id, row.repository_connection_id
                )
                config_id, config_digest, ignored = await RepositoryAccess(s).analysis_config(
                    row.requested_by, row.workspace_id, repo.id, row.config_version_id
                )
                if (
                    row.analyzer_build_digest != build_digest()
                    or row.rule_set_version != RULE_SET
                    or config_id != row.config_version_id
                    or config_digest != row.effective_config_digest
                ):
                    raise error("ANALYZER_VERSION_CHANGED")
                pr = await analysis_snapshot(s, row.requested_by, row.workspace_id, row.pr_id)
                snap = Snapshot(pr.pr_number, row.base_sha, row.head_sha)
                row.status, row.started_at = "RUNNING", datetime.now(UTC)
            async with asyncio.timeout(120):
                result = await analyze(self.github, repo, snap, ignored, lambda: self.checkpoint(c))
            await self.complete(c, result)
        except TimeoutError:
            await self.complete(c, None, "ANALYSIS_TIMEOUT")
        except GitHubFailure as exc:
            await self.complete(
                c,
                None,
                exc.code,
                exc.code in ("GITHUB_UNAVAILABLE", "GITHUB_RATE_LIMIT"),
                delay=exc.retry_after or 5,
            )
        except AppException as exc:
            await self.complete(c, None, exc.code)
        except Exception:
            # No source or provider exception representation is logged or persisted.
            await self.complete(c, None, "ANALYSIS_FAILED")

    async def complete(
        self,
        c: Claim,
        result: Result | None,
        code: str | None = None,
        retry: bool = False,
        expired: bool = False,
        delay: int = 5,
    ) -> None:
        assert c.workspace_id
        async with transaction(self.engine) as s:
            await WorkspaceAccess(s).lock_system(c.workspace_id)
            row = await find_run(s, c.workspace_id, c.aggregate_id)
            if row.status in TERMINAL:
                return
            try:
                assert row.requested_by
                await authorized(s, row.requested_by, row.workspace_id, row.id, active=True)
            except AppException:
                code, retry, result = "ACCESS_REVOKED", False, None
            job = await jobs.fence(s, c, expired)
            if not job:
                return
            if code is None and result is not None:
                s.add_all(
                    [
                        AnalysisFileResult(workspace_id=row.workspace_id, analysis_id=row.id, **f)
                        for f in result.files
                    ]
                )
                s.add_all(
                    [
                        Finding(workspace_id=row.workspace_id, analysis_id=row.id, **f)
                        for f in result.findings
                    ]
                )
                row.coverage_status, row.coverage_reason = result.coverage, result.reason
                row.total_files, row.finding_count = len(result.files), len(result.findings)
                row.included_files = sum(f["status"] == "INCLUDED" for f in result.files)
                row.excluded_files = sum(f["status"] == "EXCLUDED" for f in result.files)
                row.failed_files = row.total_files - row.included_files - row.excluded_files
                row.not_evaluated_rules = sum(
                    o["status"] == "NOT_EVALUATED"
                    for f in result.files
                    for o in cast(list[dict[str, str | None]], f["rule_outcomes"])
                )
            state = jobs.finish(job, code, retry, delay)
            row.status = (
                "PENDING"
                if state == "READY"
                else "CANCELED"
                if code in ("ACCESS_REVOKED", "ANALYSIS_CANCELED", "CONNECTION_CHANGED")
                else "FAILED"
                if code
                else "COMPLETED"
            )
            if row.status == "CANCELED":
                job.state = "CANCELED"
            row.error_code = code
            row.finished_at = None if state == "READY" else datetime.now(UTC)
