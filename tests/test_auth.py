import asyncio
import base64
import hashlib
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import httpx
import jwt
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import Session

from app.domain.auth.exceptions import ProviderUnavailable, SessionExpired
from app.domain.auth.github import GitHubOAuth
from app.domain.auth.models import LoginAttempt, RefreshSession
from app.domain.auth.service import AuthService
from app.domain.user.models import User
from app.main import create_app
from app.shared.config.settings import Settings
from app.shared.database.event_loop import loop_factory
from app.shared.security.hashing import token_hash
from app.shared.security.token_codec import decode_access, encode_access

CSRF = {"Origin": "http://localhost:5173", "X-PRism-CSRF": "1"}
KEY = "test-only-signing-value-" * 3


def settings(**overrides):
    return Settings(
        _env_file=None,
        **(
            {
                "auth_enabled": True,
                "database_url": None,
                "github_oauth_client_id": "test-client",
                "github_oauth_client_secret": "test-secret",
                "jwt_signing_key": KEY,
            }
            | overrides
        ),
    )


def provider(request):
    if request.url.path == "/login/oauth/access_token":
        data = parse_qs(request.content.decode())
        assert data["redirect_uri"] == ["http://localhost:8000/api/v1/auth/github/callback"]
        assert len(data["code_verifier"][0]) == 43
        return httpx.Response(
            200,
            json={
                "access_token": "provider-canary",
                "token_type": "bearer",
                "refresh_token": "discard-this-provider-refresh",
            },
        )
    assert str(request.url) == "https://api.github.com/user"
    assert request.headers["authorization"] == "Bearer provider-canary"
    return httpx.Response(200, json={"id": 1234, "login": "octocat", "name": "Test User"})


@pytest.fixture
def auth_settings(db):
    with db.connect() as connection:
        schema = connection.scalar(text("select current_schema()"))
    url = db.url.update_query_dict({"options": f"-csearch_path={schema}"})
    return settings(database_url=url.render_as_string(hide_password=False))


@pytest.fixture
def client(auth_settings):
    with TestClient(
        create_app(auth_settings, github_transport=httpx.MockTransport(provider)),
        base_url="http://localhost:8000",
        follow_redirects=False,
        backend_options={"loop_factory": loop_factory},
    ) as client:
        yield client


def login(client):
    start = client.get("/api/v1/auth/github/start")
    assert start.status_code == 302
    params = parse_qs(urlsplit(start.headers["location"]).query)
    binding = client.cookies.get("prism_oauth_binding")
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(binding.encode()).digest()).decode().rstrip("=")
    )
    assert params["code_challenge"] == [challenge]
    assert params["scope"] == ["read:user"]
    assert "HttpOnly" in start.headers["set-cookie"]
    assert "SameSite=lax" in start.headers["set-cookie"]
    callback = client.get(
        "/api/v1/auth/github/callback", params={"code": "test-code", "state": params["state"][0]}
    )
    assert callback.status_code == 302
    assert callback.headers["location"] == "http://localhost:5173/"
    assert "no-store" in callback.headers["cache-control"]
    return params["state"][0], binding


def test_jwt_and_local_config():
    user_id = uuid4()
    access = encode_access(user_id, KEY)
    assert decode_access(access, KEY) == user_id
    with pytest.raises(jwt.InvalidTokenError):
        decode_access(access, "wrong-" * 8)
    for patch in [{"exp": 1}, {"aud": "elsewhere"}, {"iss": "elsewhere"}, {"type": "refresh"}]:
        payload = jwt.decode(access, KEY, algorithms=["HS256"], audience="prism-api") | patch
        with pytest.raises((jwt.InvalidTokenError, ValueError)):
            decode_access(jwt.encode(payload, KEY, algorithm="HS256"), KEY)
    with pytest.raises(jwt.InvalidTokenError):
        decode_access(jwt.encode({"sub": str(user_id)}, KEY, algorithm="HS512"), KEY)
    for overrides in [
        {"jwt_signing_key": "short"},
        {"public_app_origin": "http://evil.example"},
        {"public_api_origin": "http://127.0.0.1:8000"},
        {"app_env": "production"},
    ]:
        with pytest.raises(ValidationError):
            settings(**overrides)
    assert "test-secret" not in repr(settings()) and KEY not in repr(settings())


def test_auth_disabled_and_safe_validation():
    with TestClient(create_app(settings(auth_enabled=False))) as client:
        assert client.get("/health/live").status_code == 200
        assert client.get("/api/v1/auth/github/start").status_code == 503
        response = client.get(
            "/api/v1/auth/github/start", params={"return_path": "secret-canary" * 200}
        )
        assert response.status_code == 422 and "secret-canary" not in response.text
        assert client.get("/api/v1/users/me").status_code == 401


@pytest.mark.parametrize("failure", ["timeout", "oversized", "invalid_profile"])
def test_provider_bounds(failure):
    def respond(request):
        if failure == "timeout":
            raise httpx.ReadTimeout("sensitive-provider-message")
        if failure == "oversized":
            return httpx.Response(200, content=b"x" * 32769)
        if request.url.path == "/login/oauth/access_token":
            return httpx.Response(200, json={"access_token": "x", "token_type": "bearer"})
        return httpx.Response(200, json={"id": True, "login": "invalid"})

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            with pytest.raises(ProviderUnavailable):
                await GitHubOAuth(settings(), client).identity("code", "v" * 43)

    asyncio.run(scenario(), loop_factory=loop_factory)


@pytest.mark.parametrize(
    "status,body",
    [
        (200, {"error": "bad_code"}),
        (302, {}),
        (500, {}),
        (200, {"access_token": "x", "token_type": "wrong"}),
    ],
)
def test_provider_rejects_errors_without_echo(status, body):
    async def scenario():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(status, json=body))
        ) as client:
            with pytest.raises(ProviderUnavailable) as error:
                await GitHubOAuth(settings(), client).identity("private-code", "v" * 43)
            assert "private-code" not in str(error.value)

    asyncio.run(scenario(), loop_factory=loop_factory)


@pytest.mark.integration
def test_login_profile_rotation_logout(client, db):
    login(client)
    original = client.cookies.get("prism_refresh")
    response = client.post("/api/v1/auth/refresh", headers=CSRF)
    assert response.status_code == 200
    assert (
        "HttpOnly" in response.headers["set-cookie"]
        and "Domain=" not in response.headers["set-cookie"]
    )
    assert client.cookies.get("prism_refresh") != original
    access = response.json()["access_token"]
    me = client.get("/api/v1/users/me", headers={"Authorization": "Bearer " + access})
    assert me.status_code == 200 and me.json()["login"] == "octocat"
    assert set(me.json()) == {"id", "github_user_id", "login", "display_name", "avatar_url"}
    with Session(db) as session:
        rows = session.scalars(select(RefreshSession)).all()
        assert len(rows) == 2 and rows[0].expires_at == rows[1].expires_at
        assert original not in [r.token_hash for r in rows]
        assert len(session.scalars(select(User)).all()) == 1
    assert client.post("/api/v1/auth/logout", headers=CSRF).status_code == 204
    assert client.cookies.get("prism_refresh") is None
    assert client.post("/api/v1/auth/refresh", headers=CSRF).status_code == 401


@pytest.mark.integration
def test_replay_revokes_new_session(client, db):
    login(client)
    old = client.cookies.get("prism_refresh")
    assert client.post("/api/v1/auth/refresh", headers=CSRF).status_code == 200
    new = client.cookies.get("prism_refresh")
    client.cookies.clear()
    response = client.post(
        "/api/v1/auth/refresh", headers=CSRF | {"Cookie": "prism_refresh=" + old}
    )
    assert response.status_code == 401
    assert (
        client.post(
            "/api/v1/auth/refresh", headers=CSRF | {"Cookie": "prism_refresh=" + new}
        ).status_code
        == 401
    )
    with Session(db) as session:
        assert all(r.revoked_at for r in session.scalars(select(RefreshSession)))


@pytest.mark.integration
def test_binding_expiry_reuse_and_redirect_validation(client, db):
    state, binding = login(client)
    response = client.get(
        "/api/v1/auth/github/callback",
        params={"code": "test-code", "state": state},
        headers={"Cookie": "prism_oauth_binding=" + binding},
    )
    assert "auth_error=failed" in response.headers["location"]
    assert (
        client.get(
            "/api/v1/auth/github/start", params={"return_path": "//evil.example"}
        ).status_code
        == 401
    )
    for expired in [False, True]:
        start = client.get("/api/v1/auth/github/start")
        state = parse_qs(urlsplit(start.headers["location"]).query)["state"][0]
        if expired:
            with db.begin() as connection:
                connection.execute(
                    update(LoginAttempt).values(
                        created_at=datetime.now(UTC) - timedelta(hours=2),
                        expires_at=datetime.now(UTC) - timedelta(hours=1),
                    )
                )
        else:
            client.cookies.clear()
        callback = client.get(
            "/api/v1/auth/github/callback", params={"code": "test-code", "state": state}
        )
        assert "auth_error=failed" in callback.headers["location"]


@pytest.mark.integration
@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Origin": "http://evil.example", "X-PRism-CSRF": "1"},
        {"Origin": "http://localhost:5173"},
    ],
)
def test_csrf_rejection_does_not_revoke(client, db, headers):
    login(client)
    assert client.post("/api/v1/auth/refresh", headers=headers).status_code == 403
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 403
    assert client.post("/api/v1/auth/refresh", headers=CSRF).status_code == 200


@pytest.mark.integration
def test_inactive_user_rejected(client, db):
    login(client)
    access = client.post("/api/v1/auth/refresh", headers=CSRF).json()["access_token"]
    with db.begin() as connection:
        connection.execute(update(User).values(status="INACTIVE"))
    assert (
        client.get("/api/v1/users/me", headers={"Authorization": "Bearer " + access}).status_code
        == 401
    )
    assert client.post("/api/v1/auth/refresh", headers=CSRF).status_code == 401
    start = client.get("/api/v1/auth/github/start")
    state = parse_qs(urlsplit(start.headers["location"]).query)["state"][0]
    assert (
        "auth_error=failed"
        in client.get("/api/v1/auth/github/callback", params={"code": "x", "state": state}).headers[
            "location"
        ]
    )


@pytest.mark.integration
def test_expired_refresh_rejected(client, db):
    login(client)
    with db.begin() as connection:
        connection.execute(
            update(RefreshSession).values(
                created_at=datetime.now(UTC) - timedelta(days=8),
                expires_at=datetime.now(UTC) - timedelta(days=1),
            )
        )
    assert client.post("/api/v1/auth/refresh", headers=CSRF).status_code == 401


@pytest.mark.integration
def test_concurrent_logins_and_refresh(auth_settings, db):
    async def scenario():
        engine = create_async_engine(
            auth_settings.database_url.get_secret_value(), hide_parameters=True
        )
        async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as http:
            service = AuthService(engine, auth_settings, GitHubOAuth(auth_settings, http))
            try:
                first, second = await asyncio.gather(service.start("/"), service.start("/"))

                async def finish(attempt):
                    state = parse_qs(urlsplit(attempt.url).query)["state"][0]
                    return await service.callback("x", state, attempt.binding)

                tokens = await asyncio.gather(finish(first), finish(second))
                results = await asyncio.gather(
                    service.refresh(tokens[0].refresh_token),
                    service.refresh(tokens[0].refresh_token),
                    return_exceptions=True,
                )
                assert sum(isinstance(r, SessionExpired) for r in results) == 1
                successful = next(r for r in results if not isinstance(r, Exception))
                with pytest.raises(SessionExpired):
                    await service.refresh(successful.refresh_token)
                # A separate login family is unaffected by replay of the first family.
                await service.refresh(tokens[1].refresh_token)
            finally:
                await engine.dispose()

    asyncio.run(scenario(), loop_factory=loop_factory)
    with Session(db) as session:
        assert len(session.scalars(select(User)).all()) == 1


@pytest.mark.integration
def test_external_failure_consumes_state(auth_settings, db):
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"error": "canary"}))
    with TestClient(
        create_app(auth_settings, github_transport=transport),
        base_url="http://localhost:8000",
        follow_redirects=False,
        backend_options={"loop_factory": loop_factory},
    ) as client:
        start = client.get("/api/v1/auth/github/start")
        state = parse_qs(urlsplit(start.headers["location"]).query)["state"][0]
        response = client.get(
            "/api/v1/auth/github/callback", params={"code": "secret-code", "state": state}
        )
        assert response.headers["location"] == "http://localhost:5173/?auth_error=failed"
        assert "secret-code" not in response.text and "canary" not in response.text
        with Session(db) as session:
            assert session.scalar(
                select(LoginAttempt).where(LoginAttempt.state_hash == token_hash(state))
            ).consumed_at
            assert session.scalars(select(User)).all() == []
