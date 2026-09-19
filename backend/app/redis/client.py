from collections.abc import AsyncGenerator

from fastapi import Request
from redis.asyncio import ConnectionPool, Redis

from app.core.config import settings


def create_redis_pool() -> ConnectionPool:
    """Build a connection pool from configuration.

    Does not open a connection — `redis.asyncio.ConnectionPool` connects
    lazily on first use. Called once at application startup (see the
    `lifespan` handler in `app.main`) and stored on `app.state`, not at
    import time.
    """
    return ConnectionPool.from_url(settings.redis_url, decode_responses=True)


async def get_redis_client(request: Request) -> AsyncGenerator[Redis, None]:
    """FastAPI dependency yielding a pooled Redis client for one request."""
    client = Redis(connection_pool=request.app.state.redis_pool)
    try:
        yield client
    finally:
        await client.aclose()
