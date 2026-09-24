from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.shared.config.settings import Settings
from app.shared.database.engine import build_engine
from app.shared.observability.health import ReadinessCheck, database_ready, health_router


def create_app(
    settings: Settings | None = None, readiness_check: ReadinessCheck | None = None
) -> FastAPI:
    settings = settings or Settings()
    engine = (
        build_engine(settings.database_url.get_secret_value()) if settings.database_url else None
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        if engine is not None:
            await engine.dispose()

    async def check() -> bool:
        return await database_ready(engine)

    app = FastAPI(title="PRism API", version="0.1.0", lifespan=lifespan)
    app.include_router(health_router(readiness_check or check))
    return app
