import asyncio
import base64
import hashlib
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select, update
from sqlalchemy.orm import Session
from test_auth import KEY
from test_auth import auth_settings as auth_settings
from test_repository_sync import app_settings as app_settings
from test_repository_sync import connect, provider, run_one
from test_workspace import users

from app.domain.analysis.models import AnalysisRun, Finding
from app.domain.analysis.worker import AnalysisWorker
from app.main import create_app
from app.shared.database.engine import build_engine, transaction
from app.shared.database.event_loop import loop_factory
from app.shared.github.client import GitHubClient
from app.shared.jobs.models import Job
from app.shared.jobs.store import claim
from app.shared.security.token_codec import encode_access

SOURCE = b"var x = 1;\ndebugger;\n"
BLOB = hashlib.sha1(b"blob " + str(len(SOURCE)).encode() + b"\0" + SOURCE).hexdigest()


def analysis_provider(req):
    path = req.url.path
    if path == "/repos/octo/sample/pulls/1":
        return httpx.Response(
            200, json={"base": {"sha": "a" * 40}, "head": {"sha": "b" * 40}, "changed_files": 1}
        )
    if path == "/repos/octo/sample/pulls/1/files":
        return httpx.Response(
            200,
            json=[
                {
                    "filename": "x.js",
                    "status": "added",
                    "additions": 2,
                    "deletions": 0,
                    "patch": "@@ -0,0 +1,2 @@\n+var x = 1;\n+debugger;",
                }
            ],
        )
    if path == "/repos/octo/sample/git/commits/" + "b" * 40:
        return httpx.Response(200, json={"tree": {"sha": "c" * 40}})
    if path == "/repos/octo/sample/git/trees/" + "c" * 40:
        return httpx.Response(
            200,
            json={
                "truncated": False,
                "tree": [
                    {
                        "path": "x.js",
                        "mode": "100644",
                        "type": "blob",
                        "sha": BLOB,
                        "size": len(SOURCE),
                    }
                ],
            },
        )
    if path == "/repos/octo/sample/git/blobs/" + BLOB:
        return httpx.Response(
            200, json={"encoding": "base64", "content": base64.b64encode(SOURCE).decode()}
        )
    return provider(req)


@pytest.fixture
def analysis_setup(db, app_settings, monkeypatch):
    async def idle(*args):
        await asyncio.Event().wait()

    monkeypatch.setattr("app.main.run_jobs", idle)
    settings = app_settings.model_copy(update={"analysis_runner_enabled": True})
    identities = users(db)
    with TestClient(
        create_app(settings, github_transport=httpx.MockTransport(analysis_provider)),
        follow_redirects=False,
        backend_options={"loop_factory": loop_factory},
    ) as c:
        wid, h, _, _ = connect(c, identities[0][0])
        asyncio.run(run_one(settings), loop_factory=loop_factory)
        repos = c.get(f"/api/v1/workspaces/{wid}/repositories", headers=h).json()["items"]
        rid = repos[0]["id"]
        pid = c.get(f"/api/v1/workspaces/{wid}/repositories/{rid}/pull-requests", headers=h).json()[
            "items"
        ][0]["id"]
        yield c, settings, wid, rid, pid, h, identities


async def execute(settings, transport=analysis_provider, expired=False, previous=None):
    engine = build_engine(settings.database_url.get_secret_value())
    try:
        async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as http:
            async with transaction(engine) as s:
                item = previous or await claim(s, "analysis-test", ["ANALYZE_PR"])
            if item:
                await AnalysisWorker(engine, GitHubClient(settings, http)).execute(item, expired)
            return item
    finally:
        await engine.dispose()


def start(data, **kwargs):
    c, _, wid, _, pid, h, _ = data
    r = c.post(f"/api/v1/workspaces/{wid}/analyses", headers=h, json={"pr_id": pid, **kwargs})
    assert r.status_code == 202, r.text
    return r.json()


def status(data, aid):
    c, _, wid, _, _, h, _ = data
    return c.get(f"/api/v1/workspaces/{wid}/analyses/{aid}", headers=h).json()


def test_analysis_success_idempotency_rerun_and_tenant(analysis_setup, db):
    d = analysis_setup
    c, settings, wid, rid, pid, h, u = d
    run = start(d)
    assert start(d)["id"] == run["id"]
    other = {"Authorization": "Bearer " + encode_access(u[1][0], KEY)}
    assert c.get(f"/api/v1/workspaces/{wid}/analyses/{run['id']}", headers=other).status_code == 404
    assert (
        c.post(f"/api/v1/workspaces/{wid}/analyses", headers=other, json={"pr_id": pid}).status_code
        == 404
    )
    asyncio.run(execute(settings), loop_factory=loop_factory)
    completed = status(d, run["id"])
    assert completed["status"] == "COMPLETED", completed
    assert completed["coverage_status"] == "FULL_SCOPE" and completed["finding_count"] == 2
    findings = c.get(f"/api/v1/workspaces/{wid}/analyses/{run['id']}/findings", headers=h).json()[
        "items"
    ]
    assert {f["rule_id"] for f in findings} == {"JS-001", "JS-003"}
    assert {f["scope_location"] for f in findings} == {"CHANGED"}
    assert SOURCE.decode() not in str(findings)
    rerun = start(d, rerun_of=run["id"])
    assert rerun["generation"] == 1 and rerun["id"] != run["id"]
    assert start(d)["id"] == run["id"]
    with Session(db) as s:
        assert (
            s.scalar(select(AnalysisRun).where(AnalysisRun.id == UUID(run["id"]))).head_sha
            == "b" * 40
        )
    assert all(
        not inspect(db).get_foreign_keys(t)
        for t in ("analysis_runs", "analysis_file_results", "findings")
    )


@pytest.mark.parametrize("leased", [False, True])
def test_cancel_stops_work_and_late_completion(analysis_setup, db, leased):
    d = analysis_setup
    c, settings, wid, _, _, h, _ = d
    run = start(d)

    async def acquire():
        e = build_engine(settings.database_url.get_secret_value())
        try:
            async with transaction(e) as s:
                return await claim(s, "late", ["ANALYZE_PR"])
        finally:
            await e.dispose()

    item = asyncio.run(acquire(), loop_factory=loop_factory) if leased else None
    assert (
        c.post(f"/api/v1/workspaces/{wid}/analyses/{run['id']}/cancel", headers=h).status_code
        == 202
    )

    def forbidden(req):
        raise AssertionError("Canceled work must not access GitHub")

    asyncio.run(execute(settings, forbidden, previous=item), loop_factory=loop_factory)
    assert status(d, run["id"])["status"] == "CANCELED"
    with Session(db) as s:
        assert not s.scalars(select(Finding)).all()


def test_snapshot_changed_and_revoked_connection(analysis_setup, db):
    d = analysis_setup
    c, settings, wid, rid, _, h, _ = d
    run = start(d)

    def moved(req):
        if req.url.path.endswith("/pulls/1"):
            return httpx.Response(
                200, json={"base": {"sha": "a" * 40}, "head": {"sha": "d" * 40}, "changed_files": 1}
            )
        return analysis_provider(req)

    asyncio.run(execute(settings, moved), loop_factory=loop_factory)
    assert status(d, run["id"])["error_code"] == "SNAPSHOT_CHANGED"
    second = start(d, rerun_of=run["id"])
    assert c.delete(f"/api/v1/workspaces/{wid}/repositories/{rid}", headers=h).status_code == 204

    def forbidden(req):
        raise AssertionError("Revoked work must not access GitHub")

    asyncio.run(execute(settings, forbidden), loop_factory=loop_factory)
    assert status(d, second["id"])["status"] == "CANCELED"


@pytest.mark.parametrize(
    "mode,expected",
    [
        ("symlink", "EXCLUDED"),
        ("large", "LIMIT_EXCEEDED"),
        ("truncated", "SOURCE_UNAVAILABLE"),
        ("badblob", "SOURCE_UNAVAILABLE"),
        ("parse", "PARSE_ERROR"),
    ],
)
def test_file_coverage_failures_are_not_clean_success(analysis_setup, mode, expected):
    d = analysis_setup
    c, settings, wid, _, _, h, _ = d
    run = start(d)
    badsource = b"function (( {"
    badsha = hashlib.sha1(b"blob " + str(len(badsource)).encode() + b"\0" + badsource).hexdigest()

    def broken(req):
        if "/git/blobs/" in req.url.path and mode in ("badblob", "parse"):
            return httpx.Response(
                200, json={"encoding": "base64", "content": base64.b64encode(badsource).decode()}
            )
        result = analysis_provider(req)
        if "/git/trees/" in req.url.path:
            data = result.json()
            if mode == "symlink":
                data["tree"][0]["mode"] = "120000"
            if mode == "large":
                data["tree"][0]["size"] = 300000
            if mode == "truncated":
                data["truncated"] = True
            if mode == "parse":
                data["tree"][0].update(sha=badsha, size=len(badsource))
            return httpx.Response(200, json=data)
        if "/git/blobs/" in req.url.path and mode in ("badblob", "parse"):
            return httpx.Response(
                200, json={"encoding": "base64", "content": base64.b64encode(badsource).decode()}
            )
        return result

    asyncio.run(execute(settings, broken), loop_factory=loop_factory)
    result = status(d, run["id"])
    assert result["status"] == "COMPLETED", result
    assert result["coverage_status"] == "NONE"
    files = c.get(f"/api/v1/workspaces/{wid}/analyses/{run['id']}/files", headers=h).json()["items"]
    assert files[0]["status"] == expected


def test_retry_exhaustion_keeps_run_identity(analysis_setup, db):
    d = analysis_setup
    run = start(d)
    settings = d[1]

    def unavailable(req):
        return httpx.Response(503, json={})

    for attempt in range(3):
        asyncio.run(execute(settings, unavailable), loop_factory=loop_factory)
        assert status(d, run["id"])["status"] == ("FAILED" if attempt == 2 else "PENDING")
        with Session(db) as s, s.begin():
            s.execute(
                update(Job)
                .where(Job.aggregate_id == UUID(run["id"]))
                .values(available_at=datetime.now(UTC) - timedelta(seconds=1))
            )
    with Session(db) as s:
        j = s.scalar(select(Job).where(Job.aggregate_id == UUID(run["id"])))
        assert len(j.attempt_history) == 3 and j.state == "DEAD"


def test_analysis_migration_roundtrip(db):
    import importlib.util

    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    spec = importlib.util.spec_from_file_location(
        "analysis_migration", "migrations/versions/0005_static_analysis.py"
    )
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with db.begin() as conn, Operations.context(MigrationContext.configure(conn)):
        migration.downgrade()
        assert "analysis_runs" not in inspect(conn).get_table_names()
        migration.upgrade()
        assert len(inspect(conn).get_table_names()) == 16


@pytest.mark.parametrize("change", ["cancel", "disconnect", "snapshot"])
def test_midflight_change_discards_all_results(analysis_setup, db, change):
    d = analysis_setup
    c, settings, wid, rid, _, h, _ = d
    run = start(d)
    changed = False

    def provider_with_change(req):
        nonlocal changed
        if "/git/blobs/" in req.url.path:
            changed = True
            if change == "cancel":
                assert (
                    c.post(
                        f"/api/v1/workspaces/{wid}/analyses/{run['id']}/cancel", headers=h
                    ).status_code
                    == 202
                )
            elif change == "disconnect":
                assert (
                    c.delete(f"/api/v1/workspaces/{wid}/repositories/{rid}", headers=h).status_code
                    == 204
                )
        if changed and change == "snapshot" and req.url.path.endswith("/pulls/1"):
            return httpx.Response(200, json={"base": {"sha": "d" * 40}})
        return analysis_provider(req)

    asyncio.run(execute(settings, provider_with_change), loop_factory=loop_factory)
    result = status(d, run["id"])
    assert changed
    assert result["status"] == ("FAILED" if change == "snapshot" else "CANCELED")
    with Session(db) as s:
        assert not s.scalars(select(Finding)).all()


def test_concurrent_requests_share_run(analysis_setup, db):
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=2) as pool:
        runs = list(pool.map(lambda _: start(analysis_setup), range(2)))
    assert runs[0]["id"] == runs[1]["id"]
    with Session(db) as s:
        assert len(s.scalars(select(AnalysisRun)).all()) == 1
        assert len(s.scalars(select(Job).where(Job.kind == "ANALYZE_PR")).all()) == 1
