import asyncio
import os

import pytest
from sqlalchemy import text

from app.shared.database.engine import build_engine, transaction


@pytest.mark.integration
def test_real_postgresql_transaction_rollback() -> None:
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required for the real PostgreSQL test")

    async def scenario() -> None:
        engine = build_engine(url)
        try:
            # A temporary table exists only for this connection and cannot affect domain data.
            async with engine.connect() as connection:
                await connection.execute(text("CREATE TEMP TABLE prism_probe (value integer)"))
                await connection.commit()
                transaction_scope = await connection.begin()
                await connection.execute(text("INSERT INTO prism_probe VALUES (1)"))
                await transaction_scope.rollback()
                assert (
                    await connection.execute(text("SELECT count(*) FROM prism_probe"))
                ).scalar() == 0
            async with transaction(engine) as session:
                assert (await session.execute(text("SELECT 1"))).scalar() == 1
        finally:
            await engine.dispose()

    asyncio.run(scenario())
