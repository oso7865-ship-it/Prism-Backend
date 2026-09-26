import asyncio
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
import pytest
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from test_analysis import analysis_provider, execute, start
from test_analysis import analysis_setup as analysis_setup
from test_auth import auth_settings as auth_settings
from test_repository_sync import app_settings as app_settings

from app.domain.analysis.models import AnalysisRun
from app.domain.repository.models import RepositoryConnection
from app.domain.review.models import ReviewRun
from app.domain.review.service import ReviewService
from app.domain.review.worker import ReviewWorker
from app.domain.workspace.models import WorkspaceMember
from app.shared.database.engine import build_engine, transaction
from app.shared.database.event_loop import loop_factory
from app.shared.exception.base import AppException
from app.shared.github.client import GitHubClient
from app.shared.jobs.models import Job
from app.shared.jobs.store import claim


class FakeProvider:
    model = "deepseek-flash"
    calls = 0
    fail = False

    async def review(self, payload):
        self.calls += 1
        assert "x.js" not in payload
        if self.fail:
            raise TimeoutError()
        return (
            json.dumps({"summary": "제한된 변경 검토", "issues": [], "limitations": "실행 미검증"}),
            100,
            40,
        )


async def scenario(settings, wid, aid, owner, other):
    engine = build_engine(settings.database_url.get_secret_value())
    settings = settings.model_copy(update={"ai_enabled": True})
    service = ReviewService(engine, settings)
    try:
        for uid, consent in [(owner, False), (other, True)]:
            try:
                await service.start(uid, wid, aid, consent, None)
                assert False, "must reject"
            except AppException:
                pass
        row = await service.start(owner, wid, aid, True, None)
        for operation in (
            service.get(other, wid, row.id),
            service.history(other, wid, aid),
            service.cancel(other, wid, row.id),
        ):
            with pytest.raises(AppException):
                await operation
        assert (await service.start(owner, wid, aid, True, None)).id == row.id
        provider = FakeProvider()
        async with httpx.AsyncClient(transport=httpx.MockTransport(analysis_provider)) as http:
            worker = ReviewWorker(engine, GitHubClient(settings, http), provider)
            async with transaction(engine) as s:
                item = await claim(s, "review-test", ["EXPLAIN_FINDINGS"])
            await worker.execute(item)
            result = await service.get(owner, wid, row.id)
            assert result.status == "COMPLETED" and result.input_tokens == 100
            assert result.result["coverage"]["files"][0]["file_path"] == "x.js"
            assert result.result["coverage"]["unfetched_files"] == 0
            assert result.result["harness"]["version"] == result.prompt_version
            assert result.result["harness"]["modules"] == ["core", "checks", "output", "javascript"]
            assert provider.calls == 1
            again = await service.start(owner, wid, aid, True, row.id)
            await service.cancel(owner, wid, again.id)
            assert (await service.get(owner, wid, again.id)).status == "CANCELED"
            failed = await service.start(owner, wid, aid, True, again.id)
            provider.fail = True
            async with transaction(engine) as s:
                item = await claim(s, "review-test", ["EXPLAIN_FINDINGS"])
            await worker.execute(item)
            result = await service.get(owner, wid, failed.id)
            assert result.status == "FAILED" and result.usage_uncertain
            assert provider.calls == 2
    finally:
        await engine.dispose()


def test_review_success_failure_cancel_and_tenant(analysis_setup, db):
    data = analysis_setup
    run = start(data)
    asyncio.run(execute(data[1]), loop_factory=loop_factory)
    owner, other = data[6][0][0], data[6][1][0]
    asyncio.run(
        scenario(data[1], UUID(data[2]), UUID(run["id"]), owner, other), loop_factory=loop_factory
    )
    with Session(db) as s:
        assert len(s.scalars(select(ReviewRun)).all()) == 3


async def boundary_scenario(settings, wid, aid, owner):
    engine = build_engine(settings.database_url.get_secret_value())
    provider = FakeProvider()
    enabled = settings.model_copy(update={"ai_enabled": True, "ai_daily_limit": 2})
    service = ReviewService(engine, enabled)
    try:
        with pytest.raises(AppException, match="AI"):
            await ReviewService(engine, settings).start(owner, wid, aid, True, None)
        first = await service.start(owner, wid, aid, True, None)
        async with httpx.AsyncClient(transport=httpx.MockTransport(analysis_provider)) as http:
            worker = ReviewWorker(engine, GitHubClient(enabled, http), provider)
            async with transaction(engine) as s:
                item = await claim(s, "boundary", ["EXPLAIN_FINDINGS"])
                await s.execute(
                    update(Job)
                    .where(Job.id == item.id)
                    .values(lease_until=datetime.now(UTC) - timedelta(seconds=1))
                )
            await worker.execute(item, expired=True)
            assert (await service.get(owner, wid, first.id)).error_code == "LEASE_EXPIRED"
            await worker.execute(item)
            assert provider.calls == 0
            second = await service.start(owner, wid, aid, True, first.id)
            async with transaction(engine) as s:
                item = await claim(s, "boundary", ["EXPLAIN_FINDINGS"])
                await s.execute(
                    update(RepositoryConnection)
                    .where(RepositoryConnection.id == second.repository_connection_id)
                    .values(connection_generation=second.connection_generation + 1)
                )
            await worker.execute(item)
            assert (await service.get(owner, wid, second.id)).error_code == "ACCESS_REVOKED"
            assert provider.calls == 0
            async with transaction(engine) as s:
                await s.execute(
                    update(RepositoryConnection)
                    .where(RepositoryConnection.id == second.repository_connection_id)
                    .values(connection_generation=second.connection_generation)
                )
            with pytest.raises(AppException) as failure:
                await service.start(owner, wid, aid, True, second.id)
            assert failure.value.code == "AI_DAILY_LIMIT"
            async with transaction(engine) as s:
                assert (await s.get(AnalysisRun, aid)).status == "COMPLETED"
    finally:
        await engine.dispose()


def test_review_disabled_budget_expiry_revocation_preserves_analysis(analysis_setup):
    data = analysis_setup
    run = start(data)
    asyncio.run(execute(data[1]), loop_factory=loop_factory)
    asyncio.run(
        boundary_scenario(data[1], UUID(data[2]), UUID(run["id"]), data[6][0][0]),
        loop_factory=loop_factory,
    )


async def revoked_during_call(settings, wid, aid, owner):
    engine = build_engine(settings.database_url.get_secret_value())
    enabled = settings.model_copy(update={"ai_enabled": True})
    service = ReviewService(engine, enabled)
    row = await service.start(owner, wid, aid, True, None)

    class RevokingProvider(FakeProvider):
        async def review(self, payload):
            result = await super().review(payload)
            async with transaction(engine) as s:
                await s.execute(
                    update(RepositoryConnection)
                    .where(RepositoryConnection.id == row.repository_connection_id)
                    .values(connection_generation=row.connection_generation + 1)
                )
            return result

    provider = RevokingProvider()
    try:
        async with httpx.AsyncClient(transport=httpx.MockTransport(analysis_provider)) as http:
            worker = ReviewWorker(engine, GitHubClient(enabled, http), provider)
            async with transaction(engine) as s:
                item = await claim(s, "revoke-during-call", ["EXPLAIN_FINDINGS"])
            await worker.execute(item)
            result = await service.get(owner, wid, row.id)
            assert result.status == "FAILED" and result.error_code == "ACCESS_REVOKED"
            assert result.result is None and result.usage_uncertain and provider.calls == 1
            await worker.execute(item)
            assert provider.calls == 1
    finally:
        await engine.dispose()


def test_review_discards_result_after_access_revoked(analysis_setup):
    data = analysis_setup
    run = start(data)
    asyncio.run(execute(data[1]), loop_factory=loop_factory)
    asyncio.run(
        revoked_during_call(data[1], UUID(data[2]), UUID(run["id"]), data[6][0][0]),
        loop_factory=loop_factory,
    )


async def stale_harness_scenario(settings, wid, aid, owner):
    engine = build_engine(settings.database_url.get_secret_value())
    enabled = settings.model_copy(update={"ai_enabled": True})
    service = ReviewService(engine, enabled)
    provider = FakeProvider()
    try:
        row = await service.start(owner, wid, aid, True, None)
        async with transaction(engine) as s:
            await s.execute(
                update(ReviewRun).where(ReviewRun.id == row.id).values(prompt_version="review-1")
            )
            item = await claim(s, "old-harness", ["EXPLAIN_FINDINGS"])
        async with httpx.AsyncClient(transport=httpx.MockTransport(analysis_provider)) as http:
            await ReviewWorker(engine, GitHubClient(enabled, http), provider).execute(item)
        result = await service.get(owner, wid, row.id)
        assert result.status == "FAILED" and result.error_code == "REVIEW_REPLAY_BLOCKED"
        assert result.call_attempts == 0 and provider.calls == 0
    finally:
        await engine.dispose()


def test_old_harness_job_does_not_silently_use_new_instructions(analysis_setup):
    data = analysis_setup
    run = start(data)
    asyncio.run(execute(data[1]), loop_factory=loop_factory)
    asyncio.run(
        stale_harness_scenario(data[1], UUID(data[2]), UUID(run["id"]), data[6][0][0]),
        loop_factory=loop_factory,
    )


@pytest.mark.parametrize("action", ["cancel", "demote", "expire"])
def test_review_inflight_change_blocks_late_result_and_replay(analysis_setup, action):
    data = analysis_setup
    analysis = start(data)
    asyncio.run(execute(data[1]), loop_factory=loop_factory)

    async def check():
        settings = data[1].model_copy(update={"ai_enabled": True})
        engine = build_engine(settings.database_url.get_secret_value())
        service = ReviewService(engine, settings)
        owner, wid = data[6][0][0], UUID(data[2])
        row = await service.start(owner, wid, UUID(analysis["id"]), True, None)
        entered, release = asyncio.Event(), asyncio.Event()

        class PausedProvider(FakeProvider):
            async def review(self, payload):
                result = await super().review(payload)
                entered.set()
                await release.wait()
                return result

        provider = PausedProvider()
        try:
            async with httpx.AsyncClient(transport=httpx.MockTransport(analysis_provider)) as http:
                worker = ReviewWorker(engine, GitHubClient(settings, http), provider)
                async with transaction(engine) as s:
                    item = await claim(s, "inflight-check", ["EXPLAIN_FINDINGS"])
                task = asyncio.create_task(worker.execute(item))
                try:
                    await asyncio.wait_for(entered.wait(), 10)
                    if action == "cancel":
                        await service.cancel(owner, wid, row.id)
                    else:
                        async with transaction(engine) as s:
                            if action == "demote":
                                await s.execute(
                                    update(WorkspaceMember)
                                    .where(
                                        WorkspaceMember.workspace_id == wid,
                                        WorkspaceMember.user_id == owner,
                                    )
                                    .values(role="MEMBER")
                                )
                            else:
                                await s.execute(
                                    update(Job)
                                    .where(Job.id == item.id)
                                    .values(lease_until=datetime.now(UTC) - timedelta(seconds=1))
                                )
                        if action == "expire":
                            await worker.execute(item, expired=True)
                finally:
                    release.set()
                    await asyncio.wait_for(task, 10)
                result = await service.get(owner, wid, row.id)
                expected = {
                    "cancel": "USER_CANCELED",
                    "demote": "ACCESS_REVOKED",
                    "expire": "LEASE_EXPIRED",
                }
                assert result.error_code == expected[action]
                assert result.result is None and result.usage_uncertain
                assert result.call_attempts == 1
                await worker.execute(item)
                assert provider.calls == 1
        finally:
            await engine.dispose()

    asyncio.run(check(), loop_factory=loop_factory)


def test_concurrent_review_requests_share_one_run_and_job(analysis_setup, db):
    data = analysis_setup
    analysis = start(data)
    asyncio.run(execute(data[1]), loop_factory=loop_factory)

    async def check():
        settings = data[1].model_copy(update={"ai_enabled": True})
        engine = build_engine(settings.database_url.get_secret_value())
        service = ReviewService(engine, settings)
        try:
            rows = await asyncio.gather(
                *[
                    service.start(data[6][0][0], UUID(data[2]), UUID(analysis["id"]), True, None)
                    for _ in range(4)
                ]
            )
            assert len({row.id for row in rows}) == 1
        finally:
            await engine.dispose()

    asyncio.run(check(), loop_factory=loop_factory)
    with Session(db) as s:
        assert len(s.scalars(select(ReviewRun)).all()) == 1
        assert len(s.scalars(select(Job).where(Job.kind == "EXPLAIN_FINDINGS")).all()) == 1
