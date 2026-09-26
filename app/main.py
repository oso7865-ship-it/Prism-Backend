import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

import httpx
from fastapi import FastAPI, Request
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from app.domain.analysis.router import analysis_router
from app.domain.analysis.worker import AnalysisWorker
from app.domain.auth.api import AuthAPI
from app.domain.auth.github import GitHubOAuth
from app.domain.auth.router import auth_router
from app.domain.auth.service import AuthService
from app.domain.pull_request.router import pr_router
from app.domain.pull_request.service import SyncWorker
from app.domain.repository.router import repository_router
from app.domain.review.provider import DeepSeekProvider
from app.domain.review.router import review_router
from app.domain.review.worker import ReviewWorker
from app.domain.user.router import user_router
from app.domain.webhook.router import webhook_router
from app.domain.webhook.service import WebhookWorker
from app.domain.workspace.router import workspace_router
from app.domain.workspace.service import WorkspaceService
from app.shared.config.settings import Settings
from app.shared.database.engine import build_engine
from app.shared.exception.handlers import register_handlers
from app.shared.github.client import GitHubClient
from app.shared.jobs.runner import run as run_jobs
from app.shared.observability.health import ReadinessCheck, database_ready, health_router
from app.workflows.connect_repository import ConnectRepository
from app.workflows.github_router import github_router


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

    github_app = GitHubClient(settings, github_client)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        runner = None
        if engine is not None and (
            settings.sync_runner_enabled or settings.analysis_runner_enabled or settings.ai_enabled
        ):
            github_app.ready()
            worker = SyncWorker(engine, github_app)
            webhook_worker = WebhookWorker(engine)
            from app.shared.jobs.runner import Handler

            handlers: dict[str, Handler] = {}
            if settings.sync_runner_enabled:
                handlers.update(
                    SYNC_PULL_REQUESTS=worker.execute, PROCESS_WEBHOOK=webhook_worker.execute
                )
            if settings.analysis_runner_enabled:
                handlers["ANALYZE_PR"] = AnalysisWorker(engine, github_app).execute
            if settings.ai_enabled:
                handlers["EXPLAIN_FINDINGS"] = ReviewWorker(
                    engine, github_app, DeepSeekProvider(settings)
                ).execute
            runner = asyncio.create_task(
                run_jobs(
                    engine,
                    handlers,
                )
            )
        try:
            yield
        finally:
            if runner is not None:
                runner.cancel()
                with suppress(asyncio.CancelledError):
                    await runner
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
    app.include_router(webhook_router(engine, settings))
    app.include_router(auth_router(auth, settings))
    app.include_router(user_router(AuthAPI(auth)))
    app.include_router(workspace_router(WorkspaceService(engine), AuthAPI(auth)))
    app.include_router(repository_router(engine, AuthAPI(auth)))
    app.include_router(pr_router(engine, AuthAPI(auth), github_app))
    app.include_router(analysis_router(engine, AuthAPI(auth), settings.analysis_runner_enabled))
    app.include_router(review_router(engine, AuthAPI(auth), settings))
    app.include_router(
        github_router(ConnectRepository(engine, github_app), AuthAPI(auth), settings)
    )
    return app
