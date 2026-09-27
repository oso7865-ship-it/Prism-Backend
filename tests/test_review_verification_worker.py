import asyncio
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
import pytest
from sqlalchemy import update
from test_analysis import analysis_provider, execute, start
from test_analysis import analysis_setup as analysis_setup
from test_auth import auth_settings as auth_settings
from test_repository_sync import app_settings as app_settings
from test_review_harness import output

from app.domain.repository.models import RepositoryConnection
from app.domain.review.service import ReviewService
from app.domain.review.worker import ReviewWorker
from app.shared.database.engine import build_engine, transaction
from app.shared.database.event_loop import loop_factory
from app.shared.github.client import GitHubClient
from app.shared.jobs.models import Job
from app.shared.jobs.store import claim


@pytest.mark.parametrize(
    "mode", ["keep", "drop", "invalid", "timeout", "cancel", "revoke", "expire"]
)
def test_verification_is_reserved_fenced_and_never_replayed(analysis_setup, mode):
    data = analysis_setup
    analysis = start(data)
    asyncio.run(execute(data[1]), loop_factory=loop_factory)

    async def scenario():
        settings = data[1].model_copy(update={"ai_enabled": True})
        engine = build_engine(settings.database_url.get_secret_value())
        service = ReviewService(engine, settings)
        owner, wid = data[6][0][0], UUID(data[2])
        row = await service.start(owner, wid, UUID(analysis["id"]), True, None)

        class Provider:
            model = "deepseek-flash"
            calls = []

            async def review(self, payload):
                self.calls.append("draft")
                assert (await service.get(owner, wid, row.id)).call_attempts == 1
                if mode == "cancel":
                    await service.cancel(owner, wid, row.id)
                elif mode in {"revoke", "expire"}:
                    async with transaction(engine) as s:
                        if mode == "revoke":
                            await s.execute(
                                update(RepositoryConnection)
                                .where(RepositoryConnection.id == row.repository_connection_id)
                                .values(connection_generation=row.connection_generation + 1)
                            )
                        else:
                            await s.execute(
                                update(Job)
                                .where(Job.id == item.id)
                                .values(lease_until=datetime.now(UTC) - timedelta(seconds=1))
                            )
                return json.dumps(output([2])), 100, 40

            async def verify(self, payload):
                self.calls.append("verify")
                saved = await service.get(owner, wid, row.id)
                assert saved.call_attempts == 2 and saved.input_tokens == 100
                if mode == "timeout":
                    raise TimeoutError()
                decisions = (
                    []
                    if mode == "invalid"
                    else [
                        {
                            "index": 0,
                            "action": "DROP" if mode == "drop" else "KEEP",
                            "reason": "GUARDED_PATH" if mode == "drop" else "CONFIRMED",
                            "revised": None,
                            "checked_consequence": None
                            if mode == "drop"
                            else "제공 코드의 관찰 결과",
                        }
                    ]
                )
                return json.dumps({"decisions": decisions}), 120, 30

        provider = Provider()
        try:
            async with httpx.AsyncClient(transport=httpx.MockTransport(analysis_provider)) as http:
                worker = ReviewWorker(engine, GitHubClient(settings, http), provider)
                async with transaction(engine) as s:
                    item = await claim(s, "verify-test", ["EXPLAIN_FINDINGS"])
                await worker.execute(item)
                if mode == "expire":
                    await worker.execute(item, expired=True)
                result = await service.get(owner, wid, row.id)
                if mode in {"cancel", "revoke", "expire"}:
                    assert provider.calls == ["draft"] and result.result is None
                    assert result.status in {"FAILED", "CANCELED"}
                else:
                    assert provider.calls == ["draft", "verify"] and result.call_attempts == 2
                    assert result.input_tokens == (100 if mode == "timeout" else 220)
                    if mode in {"invalid", "timeout"}:
                        assert result.status == "FAILED" and result.result is None
                        assert result.usage_uncertain
                    else:
                        assert result.status == "COMPLETED" and not result.usage_uncertain
                        assert len(result.result["issues"]) == (0 if mode == "drop" else 1)
                before = list(provider.calls)
                await worker.execute(item)
                assert provider.calls == before
        finally:
            await engine.dispose()

    asyncio.run(scenario(), loop_factory=loop_factory)
