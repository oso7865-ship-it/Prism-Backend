import asyncio
import logging
from collections.abc import Awaitable, Callable
from contextlib import suppress
from uuid import uuid4

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.shared.database.engine import transaction
from app.shared.jobs.store import Claim, claim, expired, heartbeat

Handler = Callable[[Claim, bool], Awaitable[None]]


async def renew(engine: AsyncEngine, item: Claim) -> None:
    while True:
        await asyncio.sleep(15)
        async with transaction(engine) as session:
            if not await heartbeat(session, item):
                return


async def cycle(engine: AsyncEngine, handlers: dict[str, Handler], worker: str) -> None:
    async with transaction(engine) as s:
        stale = await expired(s, list(handlers))
    for stale_item in stale:
        try:
            await handlers[stale_item.kind](stale_item, True)
        except Exception:
            logging.getLogger(__name__).error("JOB_RECOVERY_FAILED")
    async with transaction(engine) as s:
        item = await claim(s, worker, list(handlers))
    if item:
        renewal = asyncio.create_task(renew(engine, item))
        try:
            await handlers[item.kind](item, False)
        except Exception:
            logging.getLogger(__name__).error("JOB_HANDLER_FAILED")
        finally:
            renewal.cancel()
            with suppress(asyncio.CancelledError, SQLAlchemyError):
                await renewal
    else:
        await asyncio.sleep(2)


async def run(engine: AsyncEngine, handlers: dict[str, Handler]) -> None:
    worker = uuid4().hex
    while True:
        try:
            await cycle(engine, handlers, worker)
        except SQLAlchemyError:
            logging.getLogger(__name__).error("JOB_DATABASE_UNAVAILABLE")
            await asyncio.sleep(2)
