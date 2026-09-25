"""Psycopg-compatible asyncio entrypoint, including Windows local development."""

import asyncio


def loop_factory() -> asyncio.AbstractEventLoop:
    """Uvicorn custom loop provider; do not mutate the process-wide loop policy."""
    return asyncio.SelectorEventLoop()
