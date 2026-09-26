from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.domain.auth.dto import LoginStart, SessionTokens
from app.domain.auth.router import auth_router
from app.main import create_app
from app.shared.config.settings import Settings

ORIGIN = "https://prism.example.com"


def production(**changes):
    values = dict(
        _env_file=None,
        app_env="production",
        public_app_origin=ORIGIN,
        public_api_origin=ORIGIN,
        auth_enabled=True,
        database_url="postgresql+psycopg://test:fake@db.example.com/prism?sslmode=verify-full",
        github_oauth_client_id="test",
        github_oauth_client_secret="fake",
        jwt_signing_key="test-only-signing-key-32-bytes-long",
        ai_enabled=False,
        sync_runner_enabled=False,
        analysis_runner_enabled=False,
        github_app_id=None,
        github_app_slug=None,
        github_app_client_id=None,
        github_app_client_secret=None,
        github_app_private_key=None,
    )
    values.update(changes)
    return Settings(**values)


@pytest.mark.parametrize(
    "changes",
    [
        {"public_app_origin": "http://prism.example.com"},
        {"public_api_origin": "https://api.example.com"},
        {"public_app_origin": "https://localhost"},
        {"public_app_origin": "https://127.0.0.1"},
        {"public_app_origin": "https://PRISM.example.com"},
        {"public_app_origin": "https://prism.example.com:443"},
        {"public_app_origin": "https://bad..example.com"},
        {"public_app_origin": "https://-bad.example.com"},
        {"public_app_origin": "https://prism.example.com?"},
        {"public_app_origin": "https://prism.example.com#"},
        {"public_app_origin": "https://replace.invalid"},
        {"auth_enabled": False},
        {"database_url": "postgresql+psycopg://test:fake@db.example.com/prism?sslmode=require"},
        {"sync_runner_enabled": True},
    ],
)
def test_production_rejects_unsafe_configuration(changes):
    with pytest.raises(ValidationError):
        production(**changes)


def test_secure_cookie_lifecycle_and_csrf():
    settings = production()
    service = AsyncMock()
    service.start.return_value = LoginStart("https://github.com/login/oauth/authorize", "binding")
    service.callback.return_value = service.refresh.return_value = SessionTokens(
        "access", "refresh", datetime.now(UTC) + timedelta(days=1)
    )
    app = FastAPI()
    app.include_router(auth_router(service, settings))
    with TestClient(app, base_url=ORIGIN, follow_redirects=False) as client:
        start = client.get("/api/v1/auth/github/start")
        assert "Secure" in start.headers["set-cookie"]
        assert "HttpOnly" in start.headers["set-cookie"]
        callback = client.get("/api/v1/auth/github/callback?code=test&state=test")
        for cookie in callback.headers.get_list("set-cookie"):
            assert "Secure" in cookie and "HttpOnly" in cookie and "SameSite=lax" in cookie
        assert callback.headers["location"] == ORIGIN + "/"
        csrf = {"Origin": ORIGIN, "X-PRism-CSRF": "1"}
        refreshed = client.post("/api/v1/auth/refresh", headers=csrf)
        assert refreshed.status_code == 200
        assert "Secure" in refreshed.headers["set-cookie"]
        logout = client.post("/api/v1/auth/logout", headers=csrf)
        assert logout.status_code == 204
        assert "Secure" in logout.headers["set-cookie"]
        assert "Max-Age=0" in logout.headers["set-cookie"]


def test_production_hides_docs_and_prevents_api_caching():
    app = create_app(production())
    with TestClient(app, base_url=ORIGIN) as client:
        for path in ("/docs", "/redoc", "/openapi.json"):
            assert client.get(path).status_code == 404
        response = client.get("/api/not-found")
        assert response.status_code == 404
        assert response.headers["cache-control"] == "private, no-store"
        assert response.headers["cdn-cache-control"] == "no-store"
        assert response.headers["vercel-cdn-cache-control"] == "no-store"
        assert response.headers["strict-transport-security"] == "max-age=31536000"
        assert response.headers["x-frame-options"] == "DENY"
