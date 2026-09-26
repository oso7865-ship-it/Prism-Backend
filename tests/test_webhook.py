import asyncio
import hashlib
import hmac
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from test_auth import auth_settings as auth_settings
from test_repository_sync import app_settings as app_settings
from test_repository_sync import client, connect, provider, run_one
from test_workspace import users

from app.domain.pull_request.models import PullRequestSyncRun
from app.domain.repository.models import RepositoryConnection
from app.domain.webhook.models import WebhookDelivery
from app.domain.webhook.service import WebhookWorker
from app.shared.database.engine import build_engine, transaction
from app.shared.database.event_loop import loop_factory
from app.shared.jobs.models import Job
from app.shared.jobs.store import claim

SECRET = "webhook-test-only-" * 3


@pytest.fixture
def hook_settings(app_settings):
    return app_settings.model_copy(update={"github_webhook_secret": SecretStr(SECRET)})


def payload(action="opened", **extra):
    return {
        "action": action,
        "installation": {"id": 80},
        "repository": {"id": 300},
        "number": 1,
        "body": "private-canary",
        **extra,
    }


def send(c, data, delivery="test-delivery-1", event="pull_request", signature=None):
    raw = json.dumps(data).encode()
    sig = "sha256=" + hmac.new(SECRET.encode(), raw, hashlib.sha256).hexdigest()
    return c.post(
        "/webhooks/github",
        content=raw,
        headers={
            "X-Hub-Signature-256": signature or sig,
            "X-GitHub-Delivery": delivery,
            "X-GitHub-Event": event,
        },
    )


async def work(settings, expired=False):
    engine = build_engine(settings.database_url.get_secret_value())
    try:
        async with transaction(engine) as s:
            item = await claim(s, "hook-worker", ["PROCESS_WEBHOOK"])
        assert item
        if expired:
            async with transaction(engine) as s:
                await s.execute(
                    update(Job)
                    .where(Job.id == item.id)
                    .values(lease_until=datetime.now(UTC) - timedelta(seconds=1))
                )
        await WebhookWorker(engine).execute(item, expired)
        return item
    finally:
        await engine.dispose()


def setup(c, db):
    u = users(db)
    wid, headers, _, response = connect(c, u[0][0])
    assert response.status_code in (302, 303)
    return wid, headers


def test_webhook_raw_signature_bounds_and_minimal_storage(db, hook_settings):
    with client(hook_settings) as c:
        setup(c, db)
        assert send(c, payload(), signature="sha256=" + "0" * 64).status_code == 401
        assert send(c, payload(number=True)).status_code == 422
        assert send(c, payload(), event="push").status_code == 204
        assert c.post("/webhooks/github", content=b"x" * (1024 * 1024 + 1)).status_code == 413
        assert send(c, payload()).status_code == 202
        assert send(c, payload()).status_code == 200
        assert send(c, payload(action="closed")).status_code == 409
    with Session(db) as s:
        row = s.scalars(select(WebhookDelivery)).one()
        assert "private-canary" not in repr(row.__dict__)
        assert len(s.scalars(select(Job).where(Job.kind == "PROCESS_WEBHOOK")).all()) == 1


def test_webhook_concurrent_delivery(db, hook_settings):
    with client(hook_settings) as c:
        setup(c, db)

    def post(_):
        with client(hook_settings) as c:
            return send(c, payload()).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(post, range(2))) == [200, 202]


def test_webhook_unmapped_and_wrong_installation(db, hook_settings):
    with client(hook_settings) as c:
        setup(c, db)
        assert send(c, payload(installation={"id": 999})).status_code == 204
        assert send(c, payload(repository={"id": 999})).status_code == 204
    with Session(db) as s:
        assert not s.scalars(select(WebhookDelivery)).all()


def test_event_sync_system_actor_and_current_remote_state(db, hook_settings):
    with client(hook_settings) as c:
        setup(c, db)
        asyncio.run(run_one(hook_settings), loop_factory=loop_factory)
        assert send(c, payload(action="closed")).status_code == 202
    asyncio.run(work(hook_settings), loop_factory=loop_factory)
    with Session(db) as s:
        run = s.scalars(
            select(PullRequestSyncRun).where(PullRequestSyncRun.actor_type == "SYSTEM")
        ).one()
        assert run.requested_by is None and run.requested_pr_number == 1
        assert s.scalars(select(WebhookDelivery)).one().status == "PROCESSED"

    def remote(request):
        if request.url.path == "/repos/octo/sample/pulls/1":
            response = provider(
                httpx.Request("GET", "https://api.github.com/repos/octo/sample/pulls?per_page=30")
            )
            return httpx.Response(200, json=response.json()[0])
        return provider(request)

    asyncio.run(run_one(hook_settings, remote), loop_factory=loop_factory)
    with Session(db) as s:
        assert (
            s.scalars(select(PullRequestSyncRun).where(PullRequestSyncRun.actor_type == "SYSTEM"))
            .one()
            .status
            == "COMPLETED"
        )


@pytest.mark.parametrize(
    "event,action,extra",
    [
        ("installation", "deleted", {}),
        ("installation", "suspend", {}),
        ("installation_repositories", "removed", {"repositories_removed": [{"id": 300}]}),
    ],
)
def test_revocation(db, hook_settings, event, action, extra):
    with client(hook_settings) as c:
        setup(c, db)
        assert send(c, payload(action, **extra), event=event).status_code == 202
    asyncio.run(work(hook_settings), loop_factory=loop_factory)
    with Session(db) as s:
        assert s.scalars(select(RepositoryConnection)).one().status == "SUSPENDED"
        assert s.scalars(select(WebhookDelivery)).one().status == "PROCESSED"

    # Previously queued user sync must be blocked before any GitHub HTTP.
    def no_http(_):
        raise AssertionError("revoked connection performed HTTP")

    asyncio.run(run_one(hook_settings, no_http), loop_factory=loop_factory)


def test_old_delivery_does_not_suspend_reconnection(db, hook_settings):
    with client(hook_settings) as c:
        setup(c, db)
        assert send(c, payload("deleted"), event="installation").status_code == 202
    with Session(db) as s, s.begin():
        r = s.scalars(select(RepositoryConnection)).one()
        r.connection_generation += 1
        r.connected_at = datetime.now(UTC) + timedelta(seconds=1)
    asyncio.run(work(hook_settings), loop_factory=loop_factory)
    with Session(db) as s:
        assert s.scalars(select(RepositoryConnection)).one().status == "ACTIVE"


def test_stale_pr_delivery_is_canceled(db, hook_settings):
    with client(hook_settings) as c:
        setup(c, db)
        assert send(c, payload()).status_code == 202
    with Session(db) as s, s.begin():
        s.scalars(select(RepositoryConnection)).one().connection_generation += 1
    asyncio.run(work(hook_settings), loop_factory=loop_factory)
    with Session(db) as s:
        assert s.scalars(select(WebhookDelivery)).one().status == "CANCELED"
        assert s.scalars(select(Job).where(Job.kind == "PROCESS_WEBHOOK")).one().state == "CANCELED"


def test_busy_retry_and_expired_lease_are_atomic(db, hook_settings):
    with client(hook_settings) as c:
        setup(c, db)
        assert send(c, payload()).status_code == 202
    item = asyncio.run(work(hook_settings), loop_factory=loop_factory)
    with Session(db) as s, s.begin():
        row = s.get(Job, item.id)
        assert row.state == "READY" and row.error_code == "SYNC_IN_PROGRESS"
        row.available_at = datetime.now(UTC) - timedelta(seconds=1)
    stale = asyncio.run(work(hook_settings, expired=True), loop_factory=loop_factory)

    async def stale_complete():
        engine = build_engine(hook_settings.database_url.get_secret_value())
        try:
            await WebhookWorker(engine).execute(stale)
        finally:
            await engine.dispose()

    asyncio.run(stale_complete(), loop_factory=loop_factory)
    with Session(db) as s:
        assert s.get(Job, item.id).state == "READY"
        assert s.scalars(select(WebhookDelivery)).one().status == "PENDING"


def test_webhook_migration_roundtrip(db):
    import importlib.util

    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import inspect

    spec = importlib.util.spec_from_file_location(
        "webhook_migration", "migrations/versions/0004_webhook_deliveries.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with db.begin() as conn, Operations.context(MigrationContext.configure(conn)):
        module.downgrade()
        assert "webhook_deliveries" not in inspect(conn).get_table_names()
        module.upgrade()
        assert inspect(conn).get_foreign_keys("webhook_deliveries") == []


def test_enqueue_failure_rolls_back_delivery(db, hook_settings, monkeypatch):
    from app.domain.webhook import service

    with client(hook_settings) as c:
        setup(c, db)

        async def fail(*args, **kwargs):
            raise RuntimeError("simulated persistence failure")

        monkeypatch.setattr(service.jobs, "enqueue", fail)
        with pytest.raises(RuntimeError):
            send(c, payload())
    with Session(db) as s:
        assert not s.scalars(select(WebhookDelivery)).all()
        assert not s.scalars(select(Job).where(Job.kind == "PROCESS_WEBHOOK")).all()


def test_signature_covers_raw_whitespace_and_missing_headers(db, hook_settings):
    with client(hook_settings) as c:
        raw = json.dumps(payload()).encode()
        sig = "sha256=" + hmac.new(SECRET.encode(), raw, hashlib.sha256).hexdigest()
        assert c.post("/webhooks/github", content=raw).status_code == 401
        assert (
            c.post(
                "/webhooks/github",
                content=raw + b" ",
                headers={
                    "X-Hub-Signature-256": sig,
                    "X-GitHub-Event": "pull_request",
                    "X-GitHub-Delivery": "changed-body",
                },
            ).status_code
            == 401
        )


def test_failed_delivery_retry_exhaustion(db, hook_settings):
    with client(hook_settings) as c:
        setup(c, db)
        assert send(c, payload()).status_code == 202
    for attempt in range(3):
        item = asyncio.run(work(hook_settings, expired=True), loop_factory=loop_factory)
        with Session(db) as s, s.begin():
            job = s.get(Job, item.id)
            if attempt < 2:
                assert job.state == "READY"
                job.available_at = datetime.now(UTC) - timedelta(seconds=1)
            else:
                assert job.state == "DEAD" and job.attempts == 3
                assert s.scalars(select(WebhookDelivery)).one().status == "FAILED"
