import asyncio
import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings

logger = logging.getLogger(__name__)

# Task 50 — GET /ready's dependency checks. Both reuse the application's
# existing DB session / Redis pool infrastructure (app.db.session.get_db,
# app.redis.client.get_redis_client) — there is no second connection
# mechanism here. Neither function ever raises: a failure or timeout is
# reported as `False`, which is what lets the route handler stay a
# simple, deterministic "both ok -> 200, anything else -> 503" without a
# try/except of its own.


async def check_database(db: Session) -> bool:
    """Smallest meaningful connectivity check: `SELECT 1` on the existing
    SQLAlchemy session. The app's DB layer is synchronous SQLAlchemy (not
    an async driver), so the actual query runs on a worker thread via
    `asyncio.to_thread` — it can never block the event loop — and the
    whole thing is bounded by `settings.readiness_timeout_seconds` via
    `asyncio.wait_for`, so a hung connection attempt (the realistic
    Postgres-unreachable failure mode, not just a fast connection-refused)
    can't hang this endpoint's response.

    Known limitation: because the check runs in a thread rather than
    through a natively cancellable async driver, a `wait_for` timeout
    stops *waiting* on the thread but cannot forcibly kill it — a
    genuinely hung connection attempt keeps running in the background
    until the OS/driver's own eventual timeout. Acceptable here because
    `/ready` is a low-frequency ops endpoint (a periodic platform health
    check, not a per-request hot path), unlike a provider call on the
    interview critical path.
    """

    def _select_1() -> bool:
        db.execute(text("SELECT 1"))
        return True

    try:
        return await asyncio.wait_for(asyncio.to_thread(_select_1), timeout=settings.readiness_timeout_seconds)
    except (SQLAlchemyError, TimeoutError, OSError) as exc:
        # Deliberately: which dependency, and the exception's class name
        # only — never the connection string, host, or the exception's
        # own message (which for a DB driver can include the DSN).
        logger.warning("readiness_check_failed dependency=database error=%s", exc.__class__.__name__)
        return False


async def check_redis(redis_client: Redis) -> bool:
    """Smallest meaningful connectivity check: `PING` on the existing
    pooled Redis client. `Redis.ping()` is a genuinely async, cancellable
    coroutine (unlike the DB check above), so `asyncio.wait_for` here
    cleanly aborts the in-flight connection attempt on timeout rather than
    leaving anything orphaned."""
    try:
        return bool(await asyncio.wait_for(redis_client.ping(), timeout=settings.readiness_timeout_seconds))
    except (RedisError, TimeoutError, OSError) as exc:
        # Deliberately: which dependency, and the exception's class name
        # only — never REDIS_URL or the exception's own message.
        logger.warning("readiness_check_failed dependency=redis error=%s", exc.__class__.__name__)
        return False
