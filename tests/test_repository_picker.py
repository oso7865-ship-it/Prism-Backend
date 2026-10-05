"""Choose-from-GitHub repository connection: list everything, connect only what was chosen."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
from sqlalchemy import select, text, update
from sqlalchemy.orm import Session
from test_auth import KEY
from test_auth import auth_settings as auth_settings
from test_repository_sync import app_settings as app_settings
from test_repository_sync import client, connect_flow, provider
from test_workspace import users

from app.domain.repository.github import collect
from app.domain.repository.models import RepositoryCandidateSet, RepositoryConnection
from app.shared.database.event_loop import loop_factory
from app.shared.github.client import GitHubClient, GitHubFailure
from app.shared.jobs.models import Job
from app.shared.security.token_codec import encode_access


def repo(number, admin=True, name=None, owner="octo", private=True):
    return {
        "id": number,
        "name": name or f"repo{number}",
        "owner": {"login": owner},
        "private": private,
        "default_branch": "main",
        "permissions": {"admin": admin},
    }


def installation(number, app_id=42, suspended=None, permissions=None):
    return {
        "id": number,
        "app_id": app_id,
        "suspended_at": suspended,
        "permissions": permissions
        if permissions is not None
        else {"contents": "read", "pull_requests": "read", "issues": "read"},
    }


def github_with(installations, repositories):
    """Mock GitHub: installations plus repositories per installation id (paged by 100)."""

    def handler(request):
        path = request.url.path
        if path == "/login/oauth/access_token":
            return httpx.Response(200, json={"access_token": "app-user-canary"})
        if path == "/user":
            return httpx.Response(200, json={"id": 100})
        if path == "/user/installations":
            return httpx.Response(200, json={"installations": installations})
        if path.startswith("/user/installations/") and path.endswith("/repositories"):
            number = int(path.split("/")[3])
            page = int(request.url.params.get("page", "1"))
            items = repositories.get(number, [])[(page - 1) * 100 : page * 100]
            return httpx.Response(200, json={"repositories": items})
        raise AssertionError(path)

    return handler


def run_collect(settings, handler, user=100):
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return await collect(GitHubClient(settings, http), "code", "b" * 43, user)

    return asyncio.run(go(), loop_factory=loop_factory)


def test_collect_uses_only_valid_installations_and_dedupes(app_settings):
    handler = github_with(
        [
            installation(80),
            installation(81, app_id=999),
            installation(82, suspended="2026-09-01T00:00:00Z"),
            installation(83, permissions={"contents": "read"}),
            {"id": "bad"},
        ],
        {
            80: [repo(1), repo(2, admin=False), {"id": 3, "name": "bad name!"}, repo(1)],
            81: [repo(10)],
            82: [repo(11)],
            83: [repo(12)],
        },
    )
    found = run_collect(app_settings, handler)
    assert [(i.github_repository_id, i.admin) for i in found.items] == [(1, True), (2, False)]
    assert found.skipped_installations == 4 and not found.truncated
    assert all(i.installation_id == 80 for i in found.items)


def test_collect_caps_the_list_and_says_so(app_settings):
    handler = github_with(
        [installation(80), installation(81)],
        {80: [repo(n) for n in range(1, 201)], 81: [repo(n) for n in range(1001, 1201)]},
    )
    found = run_collect(app_settings, handler)
    assert len(found.items) == 300 and found.truncated


def test_collect_rejects_another_users_token(app_settings):
    try:
        run_collect(app_settings, github_with([], {}), user=999)
    except GitHubFailure as error:
        assert error.code == "GITHUB_USER_MISMATCH"
    else:
        raise AssertionError("must reject a token that belongs to someone else")


def three_repos(db_unused=None):
    return github_with(
        [installation(80)],
        {80: [repo(300, name="sample"), repo(301, admin=False, name="readonly"), repo(302)]},
    )


def test_only_chosen_repositories_are_connected_and_synced(db, app_settings):
    u = users(db)
    with client(app_settings, three_repos()) as c:
        wid, h, _, callback, _ = connect_flow(c, u[0][0], ids=[])
        assert f"team={wid}" in callback.headers["location"]
        listing = c.get(f"/api/v1/workspaces/{wid}/repositories/candidates", headers=h).json()
        assert [(i["repository_name"], i["state"]) for i in listing["items"]] == [
            ("readonly", "ADMIN_REQUIRED"),
            ("repo302", "AVAILABLE"),
            ("sample", "AVAILABLE"),
        ]
        assert listing["installation_url"].endswith("/apps/prism-test/installations/new")
        # Listing alone creates nothing.
        with Session(db) as s:
            assert not s.scalars(select(RepositoryConnection)).all()
            assert not s.scalars(select(Job)).all()
        chosen = c.post(
            f"/api/v1/workspaces/{wid}/repositories/connect-selected",
            headers=h,
            json={"github_repository_ids": [300, 301, 999, 302]},
        ).json()["results"]
        assert [r["status"] for r in chosen] == [
            "CONNECTED",
            "ADMIN_REQUIRED",
            "NOT_IN_LIST",
            "CONNECTED",
        ]
        assert chosen[2]["owner_login"] is None
        after = c.get(f"/api/v1/workspaces/{wid}/repositories/candidates", headers=h).json()
        assert {i["repository_name"]: i["state"] for i in after["items"]} == {
            "readonly": "ADMIN_REQUIRED",
            "repo302": "CONNECTED",
            "sample": "CONNECTED",
        }
    with Session(db) as s:
        connected = {r.github_repository_id for r in s.scalars(select(RepositoryConnection))}
        assert connected == {300, 302}
        assert len(s.scalars(select(Job)).all()) == 2


def test_list_is_private_to_the_requester_and_never_holds_tokens(db, app_settings):
    u = users(db)
    with client(app_settings, three_repos()) as c:
        wid, h, _, _, _ = connect_flow(c, u[0][0], ids=[])
        stranger = {"Authorization": "Bearer " + encode_access(u[1][0], KEY)}
        url = f"/api/v1/workspaces/{wid}/repositories/candidates"
        assert c.get(url, headers=stranger).status_code == 404
        assert c.get(url).status_code == 401
        assert (
            c.post(
                f"/api/v1/workspaces/{wid}/repositories/connect-selected",
                headers=stranger,
                json={"github_repository_ids": [300]},
            ).status_code
            == 404
        )
        # A second callback replaces the list instead of adding another one.
        connect_flow(c, u[0][0], wid=wid, ids=[])
    with Session(db) as s:
        rows = s.scalars(select(RepositoryCandidateSet)).all()
        assert len(rows) == 1 and rows[0].user_id == u[0][0] and rows[0].workspace_id == UUID(wid)
        stored = str(rows[0].items)
        assert "app-user-canary" not in stored and "token" not in stored.lower()
        assert not s.scalars(select(RepositoryConnection)).all()


def test_expired_list_cannot_be_read_or_used(db, app_settings):
    u = users(db)
    with client(app_settings, three_repos()) as c:
        wid, h, _, _, _ = connect_flow(c, u[0][0], ids=[])
        past = datetime.now(UTC) - timedelta(hours=1)
        with Session(db) as s, s.begin():
            s.execute(
                update(RepositoryCandidateSet).values(
                    created_at=past - timedelta(minutes=15), expires_at=past
                )
            )
        gone = c.get(f"/api/v1/workspaces/{wid}/repositories/candidates", headers=h)
        assert gone.status_code == 404 and gone.json()["error"]["code"] == "CANDIDATES_NOT_FOUND"
        used = c.post(
            f"/api/v1/workspaces/{wid}/repositories/connect-selected",
            headers=h,
            json={"github_repository_ids": [300]},
        )
        assert used.status_code == 404
        # Starting again produces a fresh list and removes the expired one.
        connect_flow(c, u[0][0], wid=wid, ids=[])
    with Session(db) as s:
        assert s.scalar(text("select count(*) from repository_candidate_sets")) == 1
        assert not s.scalars(select(RepositoryConnection)).all()


def test_empty_grant_returns_an_empty_list_with_install_link(db, app_settings):
    u = users(db)
    with client(app_settings, github_with([], {})) as c:
        wid, h, _, callback, _ = connect_flow(c, u[0][0])
        assert "repository_result=choose" in callback.headers["location"]
        body = c.get(f"/api/v1/workspaces/{wid}/repositories/candidates", headers=h).json()
        assert body["items"] == [] and body["installation_url"]


def test_start_needs_no_body_and_a_team_manager(db, app_settings):
    u = users(db)
    with client(app_settings, provider) as c:
        wid, h, _, _, _ = connect_flow(c, u[0][0])
        outsider = {"Authorization": "Bearer " + encode_access(u[1][0], KEY)}
        assert (
            c.post(f"/api/v1/workspaces/{wid}/repositories/connect", headers=outsider).status_code
            == 404
        )
        assert (
            c.post(f"/api/v1/workspaces/{wid}/repositories/connect", headers=h).status_code == 200
        )
