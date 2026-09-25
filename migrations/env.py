import asyncio

from alembic import context
from sqlalchemy.engine import Connection

from app.domain.auth.models import LoginAttempt, RefreshSession  # noqa: F401
from app.domain.user.models import User  # noqa: F401
from app.domain.workspace.models import Invitation, Workspace, WorkspaceMember  # noqa: F401
from app.shared.config.settings import Settings
from app.shared.database.base import Base
from app.shared.database.engine import build_engine
from app.shared.database.event_loop import loop_factory

settings = Settings()
if settings.database_url is None:
    raise RuntimeError("DATABASE_URL is required for migrations")
url = settings.database_url.get_secret_value()


def run_sync(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_online() -> None:
    engine = build_engine(url)
    try:
        async with engine.connect() as connection:
            await connection.run_sync(run_sync)
    finally:
        await engine.dispose()


if context.is_offline_mode():
    context.configure(url=url, target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(run_online(), loop_factory=loop_factory)
