from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from app.domain.auth.api import AuthAPI
from app.domain.auth.github import GitHubOAuth
from app.domain.auth.router import auth_router
from app.domain.auth.service import AuthService
from app.domain.user.router import user_router
from app.shared.config.settings import Settings
from app.shared.database.engine import build_engine
from app.shared.exception.handlers import register_handlers
from app.shared.observability.health import ReadinessCheck, database_ready, health_router


def create_app(
    settings: Settings | None = None,
    readiness_check: ReadinessCheck | None = None,
    github_transport: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
    settings = settings or Settings()
    engine = (
        build_engine(settings.database_url.get_secret_value()) if settings.database_url else None
    )
    github_client = httpx.AsyncClient(transport=github_transport, trust_env=False)
    auth = AuthService(engine, settings, GitHubOAuth(settings, github_client))

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        await github_client.aclose()
        if engine is not None:
            await engine.dispose()

    async def check() -> bool:
        return await database_ready(engine)

    app = FastAPI(title="PRism API", version="0.1.0", lifespan=lifespan)
    register_handlers(app)

    @app.middleware("http")
    async def private_api(request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "private, no-store"
            response.headers["Referrer-Policy"] = "no-referrer"
            response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    app.include_router(health_router(readiness_check or check))
    app.include_router(auth_router(auth, settings))
    app.include_router(user_router(AuthAPI(auth)))
    return app
