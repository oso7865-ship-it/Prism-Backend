"""Database-backed mode behavior. Skipped without TEST_DATABASE_URL, like the other review tests."""

import asyncio
import json
from uuid import UUID

import httpx
from test_analysis import analysis_provider, execute, start
from test_analysis import analysis_setup as analysis_setup
from test_auth import auth_settings as auth_settings
from test_repository_sync import app_settings as app_settings
from test_review import FakeProvider

from app.domain.review.service import ReviewService
from app.domain.review.worker import ReviewWorker
from app.domain.user.api import UserAPI
from app.shared.database.engine import build_engine, transaction
from app.shared.database.event_loop import loop_factory
from app.shared.github.client import GitHubClient
from app.shared.jobs.store import claim


class ModeProvider(FakeProvider):
    def __init__(self):
        self.seen: list[object] = []

    async def review(self, payload):
        self.seen.append(json.loads(payload).get("review_mode"))
        return await super().review(payload)

    async def recheck_empty(self, payload):
        self.seen.append(json.loads(payload).get("review_mode"))
        return await super().recheck_empty(payload)


async def scenario(settings, wid, aid, owner):
    engine = build_engine(settings.database_url.get_secret_value())
    enabled = settings.model_copy(update={"ai_enabled": True, "ai_daily_limit": 30})
    service = ReviewService(engine, enabled)
    provider = ModeProvider()
    try:
        async with transaction(engine) as s:
            await UserAPI(s).set_review_mode(owner, "JUNIOR")
        junior = await service.start(owner, wid, aid, True, None)
        assert junior.mode == "JUNIOR"
        # Same input and same mode keeps the existing idempotent reuse.
        assert (await service.start(owner, wid, aid, True, None)).id == junior.id
        async with httpx.AsyncClient(transport=httpx.MockTransport(analysis_provider)) as http:
            worker = ReviewWorker(engine, GitHubClient(enabled, http), provider)
            async with transaction(engine) as s:
                item = await claim(s, "modes", ["EXPLAIN_FINDINGS"])
            # A later profile change must not alter a run that is already queued.
            async with transaction(engine) as s:
                await UserAPI(s).set_review_mode(owner, "SENIOR")
            await worker.execute(item)
            done = await service.get(owner, wid, junior.id)
            assert done.status == "COMPLETED"
            assert done.result["harness"]["mode"] == "JUNIOR"
            assert provider.seen and set(provider.seen) == {"JUNIOR"}
            senior = await service.start(owner, wid, aid, True, junior.id)
            assert senior.mode == "SENIOR" and senior.id != junior.id
    finally:
        await engine.dispose()


def test_review_mode_is_fixed_on_the_run_and_selects_the_harness(analysis_setup):
    data = analysis_setup
    run = start(data)
    asyncio.run(execute(data[1]), loop_factory=loop_factory)
    asyncio.run(
        scenario(data[1], UUID(data[2]), UUID(run["id"]), data[6][0][0]),
        loop_factory=loop_factory,
    )
