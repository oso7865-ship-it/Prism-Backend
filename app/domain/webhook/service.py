from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncEngine

from app.domain.pull_request.api import request_event_sync
from app.domain.repository.api import RepositoryEvents
from app.domain.webhook import repository as store
from app.domain.webhook.exceptions import WebhookRejected
from app.domain.webhook.verifier import Event
from app.shared.database.engine import transaction
from app.shared.exception.base import AppException
from app.shared.jobs import store as jobs
from app.shared.jobs.store import Claim


async def receive(engine: AsyncEngine, event: Event) -> int:
    async with transaction(engine) as s:
        existing = await store.by_delivery(s, event.delivery_id)
        if existing:
            if existing.body_digest != event.digest or existing.event != event.event:
                raise WebhookRejected("WEBHOOK_DELIVERY_MISMATCH")
            return 200
        repo = None
        if event.event == "pull_request":
            assert event.repository_id
            try:
                repo = await RepositoryEvents(s).mapped(event.installation_id, event.repository_id)
            except AppException:
                return 204
            if repo is None:
                return 204
        did = uuid4()
        inserted = await store.add(s, did, event, repo)
        if inserted is None:
            previous = await store.by_delivery(s, event.delivery_id)
            assert previous
            if previous.body_digest != event.digest or previous.event != event.event:
                raise WebhookRejected("WEBHOOK_DELIVERY_MISMATCH")
            return 200
        await jobs.enqueue(s, "PROCESS_WEBHOOK", did, repo.workspace_id if repo else None)
    return 202


class WebhookWorker:
    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine

    async def execute(self, c: Claim, expired: bool = False) -> None:
        # No network work here. Domain work and delivery/job completion commit together.
        async with transaction(self.engine) as s:
            row = await store.get(s, c.aggregate_id)
            if row is None:
                return
            access = RepositoryEvents(s)
            code = None
            targets = []
            if row.event == "pull_request":
                assert (
                    row.workspace_id and row.repository_connection_id and row.connection_generation
                )
                try:
                    await access.require(
                        row.workspace_id, row.repository_connection_id, row.connection_generation
                    )
                except AppException:
                    code = "CONNECTION_CHANGED"
            else:
                targets = await access.lock_affected(
                    row.installation_id,
                    row.affected_repository_ids
                    if row.event == "installation_repositories"
                    else None,
                    row.received_at,
                )
            row = await store.get(s, row.id, lock=True)
            assert row
            job = await jobs.fence(s, c, expired)
            if not job:
                return
            if code:
                jobs.finish(job, code)
                job.state = "CANCELED"
                job.attempt_history = [
                    *job.attempt_history[:-1],
                    {**job.attempt_history[-1], "outcome": "CANCELED"},
                ]
                row.status, row.error_code = "CANCELED", code
                row.processed_at = datetime.now(UTC)
                return
            if expired:
                code = "LEASE_EXPIRED"
            elif row.event == "pull_request":
                assert (
                    row.workspace_id
                    and row.repository_connection_id
                    and row.connection_generation
                    and row.pr_number
                )
                sid = await request_event_sync(
                    s,
                    row.workspace_id,
                    row.repository_connection_id,
                    row.connection_generation,
                    row.pr_number,
                )
                if sid is None:
                    code = "SYNC_IN_PROGRESS"
            else:
                await access.suspend_locked(targets)
            state = jobs.finish(
                job, code, retry=bool(code), delay=30 if code == "SYNC_IN_PROGRESS" else 5
            )
            row.status = "PENDING" if state == "READY" else "FAILED" if code else "PROCESSED"
            row.error_code = code
            row.processed_at = None if state == "READY" else datetime.now(UTC)
