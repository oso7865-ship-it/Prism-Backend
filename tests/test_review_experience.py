import asyncio
import base64
from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx
import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, select, update
from sqlalchemy.orm import Session
from test_analysis import analysis_setup as analysis_setup
from test_auth import KEY
from test_auth import auth_settings as auth_settings
from test_repository_sync import app_settings as app_settings

from app.domain.repository.models import RepositoryConnection
from app.domain.review.context import source
from app.domain.review.context_selection import enrich
from app.domain.review.feedback import prior_feedback
from app.domain.review.models import ReviewFeedback, ReviewRun
from app.domain.review.policy import MAX_INPUT, POLICY, PROMPT, issue_key, prepare
from app.shared.config.settings import Settings
from app.shared.database.engine import build_engine, transaction
from app.shared.database.event_loop import loop_factory
from app.shared.github.client import GitHubClient
from app.shared.security.token_codec import encode_access


def test_feedback_permissions_persistence_and_latest_sync(analysis_setup, db, monkeypatch):
    c, settings, wid, rid, pid, headers, users = analysis_setup
    item = {"file_path": "x.js", "line": 1, "title": "경계 검사", "basis": "SUPPORTED"}
    key, review_id = issue_key(item), uuid4()
    with Session(db) as s, s.begin():
        repo = s.get(RepositoryConnection, UUID(rid))
        s.add(
            ReviewRun(
                id=review_id,
                workspace_id=UUID(wid),
                analysis_id=uuid4(),
                pr_id=UUID(pid),
                repository_connection_id=UUID(rid),
                connection_generation=repo.connection_generation,
                requested_by=users[0][0],
                head_sha="b" * 40,
                model="test",
                prompt_version=PROMPT,
                policy_version=POLICY,
                execution_key="e" * 64,
                status="COMPLETED",
                consented_at=datetime.now(UTC),
                finished_at=datetime.now(UTC),
                result={
                    "issues": [item],
                    "coverage": {"files": [{"file_id": "f1", "file_path": "x.js"}]},
                },
            )
        )
    url = f"/api/v1/workspaces/{wid}/reviews/{review_id}"
    assert c.get(url + "/feedback", headers=headers).json() == {"items": []}
    assert (
        c.put(
            url + "/feedback/" + key,
            headers=headers,
            json={"state": "INTENDED", "note": "문서 락 사용"},
        ).status_code
        == 200
    )
    assert (
        c.put(
            url + "/feedback/" + key,
            headers=headers,
            json={"state": "PLANNED", "note": "검증 추가"},
        ).status_code
        == 200
    )
    assert c.get(url + "/feedback", headers=headers).json()["items"][0]["state"] == "PLANNED"
    with Session(db) as s:
        assert len(s.scalars(select(ReviewFeedback)).all()) == 1
    other = {"Authorization": "Bearer " + encode_access(users[1][0], KEY)}
    for path in ("/feedback", "/source/" + key, "/source-files/f1"):
        assert c.get(url + path, headers=other).status_code == 404
        assert c.get(url + path).status_code == 401
    assert c.put(url + "/feedback/" + key, headers=other, json={"state": "OPEN"}).status_code == 404
    assert (
        c.put(url + "/feedback/" + "f" * 64, headers=headers, json={"state": "OPEN"}).status_code
        == 404
    )
    assert (
        c.put(url + "/feedback/" + key, headers=headers, json={"state": "RESOLVED"}).status_code
        == 422
    )
    assert (
        c.put(
            url + "/feedback/" + key,
            headers=headers,
            json={"state": "OPEN", "note": "password='secret_value'"},
        ).status_code
        == 422
    )
    latest = f"/api/v1/workspaces/{wid}/repositories/{rid}/syncs/latest"
    assert c.get(latest, headers=headers).json()["status"] == "COMPLETED"
    assert c.get(latest, headers=other).status_code == 404
    members = c.get(f"/api/v1/workspaces/{wid}/members", headers=headers).json()["items"]
    assert members[0]["login"]
    response = c.get(url + "/source/" + key, headers=headers)
    assert response.status_code == 200
    assert response.json()["head_sha"] == "b" * 40
    assert response.json()["lines"][0] == "var x = 1;"
    assert "no-store" in response.headers["cache-control"]
    file_url = url + "/source-files/f1"
    assert c.get(file_url, headers=headers).json()["lines"] == response.json()["lines"]
    assert c.get(url + "/source-files/not-allowed", headers=headers).status_code == 404
    for invalid_line in (0, -1, 200001, "no"):
        assert c.get(file_url, headers=headers, params={"line": invalid_line}).status_code == 422
    assert c.get(file_url, headers=headers, params={"line": 999}).status_code == 422
    from app.domain.review import source_view

    async def long_file(*args):
        return ["a" * 400 if i == 80 else f"line {i + 1}" for i in range(165)]

    with monkeypatch.context() as patch:
        patch.setattr(source_view, "source", long_file)
        page = c.get(file_url, headers=headers, params={"line": 81}).json()
        assert page["start_line"] == 81 and page["total_lines"] == 165
        assert len(page["lines"]) == 80 and len(page["lines"][0]) == 300
        assert page["truncated"]
        last = c.get(file_url, headers=headers, params={"line": 161}).json()
        assert last["lines"][-1] == "line 165" and len(last["lines"]) == 5
    with Session(db) as s, s.begin():
        # Reviewed files remain readable when there are no findings.
        s.execute(
            update(ReviewRun)
            .where(ReviewRun.id == review_id)
            .values(
                result={
                    "issues": [],
                    "questions": [],
                    "coverage": {"files": [{"file_id": "f1", "file_path": "x.js"}]},
                }
            )
        )
    assert c.get(file_url, headers=headers).status_code == 200
    with Session(db) as s, s.begin():
        s.execute(
            update(ReviewRun)
            .where(ReviewRun.id == review_id)
            .values(
                result={
                    "issues": [item],
                    "coverage": {"files": [{"file_id": "f1", "file_path": "x.js"}]},
                }
            )
        )

    async def previous():
        engine = build_engine(settings.database_url.get_secret_value())
        try:
            async with transaction(engine) as s:
                current = ReviewRun(
                    id=uuid4(), workspace_id=UUID(wid), pr_id=UUID(pid), requested_by=users[0][0]
                )
                assert (await prior_feedback(s, current))[0]["note"] == "검증 추가"
                current.requested_by = users[1][0]
                assert await prior_feedback(s, current) == []
        finally:
            await engine.dispose()

    asyncio.run(previous(), loop_factory=loop_factory)
    original = GitHubClient.request

    async def revoke_during_source(self, method, path, token, **kwargs):
        response = await original(self, method, path, token, **kwargs)
        if "/contents/" in path:
            with Session(db) as s, s.begin():
                s.execute(
                    update(RepositoryConnection)
                    .where(RepositoryConnection.id == UUID(rid))
                    .values(connection_generation=2)
                )
        return response

    monkeypatch.setattr(GitHubClient, "request", revoke_during_source)
    rejected = c.get(url + "/source/" + key, headers=headers)
    assert rejected.status_code == 409 and "var x" not in rejected.text
    assert c.get(latest, headers=headers).json() is None
    assert c.get(url + "/source/" + key, headers=headers).status_code == 409
    assert c.get(file_url, headers=headers).status_code == 409


def test_pinned_related_context_budget_and_secret_rejection():
    calls = []

    def transport(req):
        calls.append(str(req.url))
        if "/git/commits/" in req.url.path:
            return httpx.Response(200, json={"tree": {"sha": "b" * 40}})
        if "/git/trees/" in req.url.path:
            return httpx.Response(
                200,
                json={
                    "tree": [
                        {"path": "A.java", "type": "blob", "mode": "100644"},
                        {"path": "Document.java", "type": "blob", "mode": "100644"},
                        {"path": "private/Document.java", "type": "blob", "mode": "100644"},
                    ]
                },
            )
        text = (
            "class Document {}"
            if req.url.path.endswith("Document.java")
            else "// before\nDocument x = new Document();\n// after"
        )
        return httpx.Response(
            200,
            json={
                "type": "file",
                "encoding": "base64",
                "size": len(text),
                "content": base64.b64encode(text.encode()).decode(),
            },
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as http:
            github = GitHubClient(Settings(_env_file=None), http)
            bundle = prepare(
                [{"filename": "A.java", "patch": "@@ -2 +2 @@\n+Document x = new Document();"}],
                [],
                [],
            )
            bundle = await enrich(bundle, github, "test", "/repos/a/b", "b" * 40, ["private/*"])
            assert len(bundle.payload.encode()) <= MAX_INPUT
            assert "A.java" not in bundle.payload and "Document.java" not in bundle.payload
            assert bundle.anchors["f1"][1] == {1, 2, 3}
            assert len(bundle.anchors) == 2
            assert bundle.coverage["files"][1]["role"] == "related"
            assert all("b" * 40 in url for url in calls)
            with pytest.raises(ValueError):
                await source(github, "test", "/repos/a/b", "main", "A.java")
            with pytest.raises(ValueError):
                await source(github, "test", "/repos/a/b", "b" * 40, "../A.java")

    asyncio.run(run())


def test_feedback_migration_can_roll_back_without_touching_reviews(db):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "feedback", "migrations/versions/0007_review_feedback.py"
    )
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with db.begin() as c:
        with Operations.context(MigrationContext.configure(c)):
            migration.downgrade()
            assert "review_feedback" not in inspect(c).get_table_names()
            assert "review_runs" in inspect(c).get_table_names()
            migration.upgrade()
            assert inspect(c).get_foreign_keys("review_feedback") == []
