import asyncio
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select, update
from sqlalchemy.orm import Session
from test_auth import KEY
from test_auth import auth_settings as auth_settings
from test_workspace import users

from app.domain.pull_request.models import PullRequest, PullRequestSyncRun
from app.domain.pull_request.service import SyncWorker
from app.domain.repository.models import RepositoryConnection, RuleConfigVersion
from app.main import create_app
from app.shared.database.engine import build_engine, transaction
from app.shared.database.event_loop import loop_factory
from app.shared.github.client import GitHubClient
from app.shared.jobs.models import Job
from app.shared.jobs.store import claim
from app.shared.security.token_codec import encode_access


@pytest.fixture
def app_settings(auth_settings):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ).decode()
    return auth_settings.model_copy(
        update={
            "github_app_id": 42,
            "github_app_slug": "prism-test",
            "github_app_client_id": "test-app",
            "github_app_client_secret": __import__("pydantic").SecretStr("test-secret"),
            "github_app_private_key": __import__("pydantic").SecretStr(pem),
        }
    )


def provider(request):
    path = request.url.path
    repo = {
        "id": 300,
        "name": "sample",
        "owner": {"login": "octo"},
        "private": True,
        "default_branch": "main",
        "permissions": {"admin": True},
    }
    if path == "/login/oauth/access_token":
        return httpx.Response(200, json={"access_token": "app-user-canary"})
    if path == "/user":
        return httpx.Response(200, json={"id": 100})
    if path == "/repos/octo/sample":
        return httpx.Response(200, json=repo)
    if path == "/repos/octo/sample/installation":
        return httpx.Response(
            200,
            json={
                "id": 80,
                "app_id": 42,
                "permissions": {"contents": "read", "pull_requests": "read", "issues": "read"},
                "suspended_at": None,
            },
        )
    if path == "/user/installations/80/repositories":
        return httpx.Response(200, json={"repositories": [repo]})
    if path == "/app/installations/80/access_tokens":
        assert '"repository_ids":[300]' in request.content.decode()
        return httpx.Response(201, json={"token": "installation-canary"})
    if path == "/repos/octo/sample/pulls":
        assert request.url.params["per_page"] == "30"
        return httpx.Response(
            200,
            json=[
                {
                    "id": 400,
                    "number": 1,
                    "title": "Example",
                    "user": {"id": 100, "login": "octo"},
                    "state": "open",
                    "draft": False,
                    "base": {"ref": "main", "sha": "a" * 40},
                    "head": {"ref": "topic", "sha": "b" * 40},
                    "created_at": "2026-09-01T00:00:00Z",
                    "updated_at": "2026-09-02T00:00:00Z",
                }
            ],
        )
    if path == "/repos/octo/sample/pulls/1/reviews":
        return httpx.Response(
            200,
            json=[
                {
                    "id": 9,
                    "user": {"login": "reviewer"},
                    "state": "APPROVED",
                    "body": "secret-canary",
                    "diff_hunk": "private-source",
                }
            ],
        )
    raise AssertionError(path)


def client(settings, transport=provider):
    return TestClient(
        create_app(settings, github_transport=httpx.MockTransport(transport)),
        base_url="http://localhost:8000",
        follow_redirects=False,
        backend_options={"loop_factory": loop_factory},
    )


def connect(c, uid):
    headers = {"Authorization": "Bearer " + encode_access(uid, KEY)}
    wid = c.post("/api/v1/workspaces", headers=headers, json={"name": "Repo Team"}).json()["id"]
    response = c.post(
        f"/api/v1/workspaces/{wid}/repositories/connect",
        headers=headers,
        json={"full_name": "octo/sample"},
    )
    assert response.status_code == 200, response.text
    state = parse_qs(urlsplit(response.json()["authorization_url"]).query)["state"][0]
    result = c.get("/api/v1/github-app/callback", params={"code": "test-code", "state": state})
    return wid, headers, state, result


async def run_one(settings, transport=provider):
    engine = build_engine(settings.database_url.get_secret_value())
    try:
        async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as http:
            async with transaction(engine) as s:
                job = await claim(s, "test-worker", ["SYNC_PULL_REQUESTS"])
            if job:
                await SyncWorker(engine, GitHubClient(settings, http)).execute(job)
            return job
    finally:
        await engine.dispose()


def test_connect_sync_and_scoped_queries(db, app_settings):
    u = users(db)
    with client(app_settings) as c:
        wid, h, state, result = connect(c, u[0][0])
        assert result.headers["location"].endswith("repository_result=connected")
        replay = c.get("/api/v1/github-app/callback", params={"code": "test", "state": state})
        assert replay.headers["location"].endswith("repository_result=failed")
        repos = c.get(f"/api/v1/workspaces/{wid}/repositories", headers=h).json()["items"]
        assert len(repos) == 1
        rid = repos[0]["id"]
        with Session(db) as s:
            assert len(s.scalars(select(Job)).all()) == 1
            assert len(s.scalars(select(RuleConfigVersion)).all()) == 1
            assert not s.scalars(select(PullRequest)).all()
        run = c.post(
            f"/api/v1/workspaces/{wid}/repositories/{rid}/syncs", headers=h, json={}
        ).json()
        conflict = c.post(
            f"/api/v1/workspaces/{wid}/repositories/{rid}/syncs", headers=h, json={"page": 2}
        )
        assert conflict.status_code == 409
        asyncio.run(run_one(app_settings), loop_factory=loop_factory)
        status = c.get(
            f"/api/v1/workspaces/{wid}/repositories/{rid}/syncs/{run['id']}", headers=h
        ).json()
        assert status["status"] == "COMPLETED", status
        prs = c.get(f"/api/v1/workspaces/{wid}/repositories/{rid}/pull-requests", headers=h).json()[
            "items"
        ]
        assert len(prs) == 1
        other = {"Authorization": "Bearer " + encode_access(u[1][0], KEY)}
        assert (
            c.get(
                f"/api/v1/workspaces/{wid}/pull-requests/{prs[0]['id']}", headers=other
            ).status_code
            == 404
        )
        review = c.get(
            f"/api/v1/workspaces/{wid}/pull-requests/{prs[0]['id']}/github-reviews", headers=h
        )
        assert review.status_code == 200
        assert "secret-canary" not in review.text and "private-source" not in review.text
        assert (
            c.delete(f"/api/v1/workspaces/{wid}/repositories/{rid}", headers=h).status_code == 204
        )
        assert (
            c.get(
                f"/api/v1/workspaces/{wid}/repositories/{rid}/pull-requests", headers=h
            ).status_code
            == 409
        )
    catalog = inspect(db)
    assert len(catalog.get_table_names()) == 16
    assert all(not catalog.get_foreign_keys(t) for t in catalog.get_table_names())


@pytest.mark.parametrize("failure", ["identity", "admin", "not_granted", "suspended", "wrong_app"])
def test_untrusted_install_flow_rejected(db, app_settings, failure):
    u = users(db)

    def bad(req):
        response = provider(req)
        data = response.json()
        if req.url.path == "/user" and failure == "identity":
            data["id"] = 999
        if req.url.path == "/repos/octo/sample" and failure == "admin":
            data["permissions"]["admin"] = False
        if req.url.path == "/user/installations/80/repositories" and failure == "not_granted":
            data["repositories"] = []
        if req.url.path.endswith("/installation") and failure == "suspended":
            data["suspended_at"] = "2026-09-01T00:00:00Z"
        if req.url.path.endswith("/installation") and failure == "wrong_app":
            data["app_id"] = 999
        return httpx.Response(response.status_code, json=data)

    with client(app_settings, bad) as c:
        _, _, _, result = connect(c, u[0][0])
        assert result.headers["location"].endswith("repository_result=failed")
    with Session(db) as s:
        assert (
            not s.scalars(select(RepositoryConnection)).all() and not s.scalars(select(Job)).all()
        )


def test_sync_retries_and_access_revocation(db, app_settings):
    u = users(db)
    with client(app_settings) as c:
        wid, h, _, _ = connect(c, u[0][0])

    def unavailable(req):
        return httpx.Response(503)

    asyncio.run(run_one(app_settings, unavailable), loop_factory=loop_factory)
    with Session(db) as s, s.begin():
        job = s.scalars(select(Job)).one()
        assert job.state == "READY" and job.attempts == 1
        job.available_at = datetime.now(UTC) - timedelta(seconds=1)

    def revoked(req):
        return httpx.Response(403)

    asyncio.run(run_one(app_settings, revoked), loop_factory=loop_factory)
    with Session(db) as s:
        assert s.scalars(select(Job)).one().state == "DEAD"
        assert s.scalars(select(PullRequestSyncRun)).one().status == "FAILED"
        assert s.scalars(select(RepositoryConnection)).one().status == "SUSPENDED"


def test_lease_recovery_and_stale_completion(db, app_settings):
    u = users(db)
    with client(app_settings) as c:
        connect(c, u[0][0])

    async def scenario():
        e = build_engine(app_settings.database_url.get_secret_value())
        try:
            async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as http:
                worker = SyncWorker(e, GitHubClient(app_settings, http))
                async with transaction(e) as s:
                    first = await claim(s, "old", ["SYNC_PULL_REQUESTS"])
                async with transaction(e) as s:
                    second = await claim(s, "other", ["SYNC_PULL_REQUESTS"])
                assert first and not second
                async with transaction(e) as s:
                    await s.execute(
                        update(Job).values(lease_until=datetime.now(UTC) - timedelta(seconds=1))
                    )
                await worker.execute(first, True)
                async with transaction(e) as s:
                    await s.execute(
                        update(Job).values(available_at=datetime.now(UTC) - timedelta(seconds=1))
                    )
                async with transaction(e) as s:
                    new = await claim(s, "new", ["SYNC_PULL_REQUESTS"])
                assert new and new.generation == 2
                await worker.complete(first, [])
                await worker.execute(new)
        finally:
            await e.dispose()

    asyncio.run(scenario(), loop_factory=loop_factory)
    with Session(db) as s:
        job = s.scalars(select(Job)).one()
        assert job.state == "SUCCEEDED" and job.attempts == 2
        assert len(job.attempt_history) == 2


def test_duplicate_connection_and_binding_tamper(db, app_settings):
    u = users(db)
    with client(app_settings) as c:
        wid, h, _, result = connect(c, u[0][0])
        assert result.headers["location"].endswith("connected")
        _, _, _, result = connect(c, u[0][0])
        assert result.headers["location"].endswith("failed")
        start = c.post(
            f"/api/v1/workspaces/{wid}/repositories/connect",
            headers=h,
            json={"full_name": "octo/sample"},
        )
        state = parse_qs(urlsplit(start.json()["authorization_url"]).query)["state"][0]
        c.cookies.clear()
        assert (
            c.get("/api/v1/github-app/callback", params={"state": state, "code": "x"})
            .headers["location"]
            .endswith("failed")
        )
        for target in ["octo/..", "octo/.", "https://evil.example/a", "octo/sample?x=1"]:
            assert (
                c.post(
                    f"/api/v1/workspaces/{wid}/repositories/connect",
                    headers=h,
                    json={"full_name": target},
                ).status_code
                == 422
            )
    with Session(db) as s:
        assert len(s.scalars(select(RepositoryConnection)).all()) == 1
        assert len(s.scalars(select(Job)).all()) == 1


def test_etag_reuse_and_stale_updates(db, app_settings):
    u = users(db)

    def cached(req):
        response = provider(req)
        if req.url.path == "/repos/octo/sample/pulls":
            if req.headers.get("if-none-match") == '"v1"':
                return httpx.Response(304)
            return httpx.Response(200, json=response.json(), headers={"ETag": '"v1"'})
        return response

    with client(app_settings, cached) as c:
        wid, h, _, _ = connect(c, u[0][0])
        rid = c.get(f"/api/v1/workspaces/{wid}/repositories", headers=h).json()["items"][0]["id"]
        asyncio.run(run_one(app_settings, cached), loop_factory=loop_factory)
        url = f"/api/v1/workspaces/{wid}/repositories/{rid}/syncs"
        c.post(url, headers=h, json={})
        asyncio.run(run_one(app_settings, cached), loop_factory=loop_factory)
        with Session(db) as s:
            assert len(s.scalars(select(PullRequest)).all()) == 1
            runs = s.scalars(select(PullRequestSyncRun)).all()
            assert all(row.status == "COMPLETED" for row in runs)
            assert all(row.next_cursor is None for row in runs)

        def stale(req):
            response = provider(req)
            if req.url.path == "/repos/octo/sample/pulls":
                data = response.json()
                data[0]["updated_at"] = "2026-09-01T00:00:00Z"
                data[0]["title"] = "stale"
                return httpx.Response(200, json=data)
            return response

        c.post(url, headers=h, json={})
        asyncio.run(run_one(app_settings, stale), loop_factory=loop_factory)
        with Session(db) as s:
            assert s.scalars(select(PullRequest)).one().title == "Example"


def test_disconnect_blocks_queued_sync_and_reconnect_generation(db, app_settings):
    u = users(db)
    with client(app_settings) as c:
        wid, h, _, _ = connect(c, u[0][0])
        rid = c.get(f"/api/v1/workspaces/{wid}/repositories", headers=h).json()["items"][0]["id"]
        c.delete(f"/api/v1/workspaces/{wid}/repositories/{rid}", headers=h)
        asyncio.run(run_one(app_settings), loop_factory=loop_factory)
        with Session(db) as s:
            assert s.scalars(select(PullRequestSyncRun)).one().status == "FAILED"
            assert not s.scalars(select(PullRequest)).all()
        start = c.post(
            f"/api/v1/workspaces/{wid}/repositories/connect",
            headers=h,
            json={"full_name": "octo/sample"},
        )
        state = parse_qs(urlsplit(start.json()["authorization_url"]).query)["state"][0]
        result = c.get("/api/v1/github-app/callback", params={"state": state, "code": "x"})
        assert result.headers["location"].endswith("connected")
        with Session(db) as s:
            repo = s.scalars(select(RepositoryConnection)).one()
            assert str(repo.id) == rid and repo.connection_generation == 2


def test_new_schema_matches_metadata_and_roundtrip(db):
    import importlib.util

    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    from app.shared.database.base import Base

    with db.connect() as conn:
        assert compare_metadata(MigrationContext.configure(conn), Base.metadata) == []
    spec = importlib.util.spec_from_file_location(
        "sync_migration", "migrations/versions/0003_repository_sync.py"
    )
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with db.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            migration.downgrade()
            assert len(inspect(conn).get_table_names()) == 11  # remaining domain tables
            migration.upgrade()
            assert len(inspect(conn).get_table_names()) == 16


def test_retry_exhaustion_and_atomic_failure(db, app_settings):
    u = users(db)
    with client(app_settings) as c:
        connect(c, u[0][0])

    def broken(req):
        return httpx.Response(503)

    for attempt in range(3):
        asyncio.run(run_one(app_settings, broken), loop_factory=loop_factory)
        with Session(db) as s, s.begin():
            job = s.scalars(select(Job)).one()
            assert job.attempts == attempt + 1
            if attempt < 2:
                assert job.state == "READY"
                job.available_at = datetime.now(UTC) - timedelta(seconds=1)
    with Session(db) as s:
        job = s.scalars(select(Job)).one()
        assert job.state == "DEAD" and len(job.attempt_history) == 3
        assert s.scalars(select(PullRequestSyncRun)).one().status == "FAILED"
        assert not s.scalars(select(PullRequest)).all()


def test_revoked_actor_prevents_external_work(db, app_settings):
    from app.domain.workspace.models import WorkspaceMember

    u = users(db)
    with client(app_settings) as c:
        connect(c, u[0][0])
    with Session(db) as s, s.begin():
        m = s.scalars(select(WorkspaceMember)).one()
        m.status = "REMOVED"
        m.ended_at = datetime.now(UTC)

    def no_http(req):
        raise AssertionError("revoked actor must not call GitHub")

    asyncio.run(run_one(app_settings, no_http), loop_factory=loop_factory)
    with Session(db) as s:
        assert s.scalars(select(Job)).one().state == "DEAD"
        assert s.scalars(select(PullRequestSyncRun)).one().error_code == "WORKSPACE_NOT_FOUND"
