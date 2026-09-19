"""Genuine integration test against a real Redis server.

Unlike tests/test_redis_runtime_state.py (which uses an in-memory fake so
unit tests don't require Redis), this test opens a real connection. If no
Redis server is reachable at REDIS_URL, it skips cleanly with the actual
connection error rather than faking a pass — the same honesty standard
already established for PostgreSQL in tests/test_db.py.
"""

import uuid

import pytest
import pytest_asyncio
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import settings
from app.domain.enums import Difficulty, InterviewStatus, InterviewTopic
from app.redis.idempotency import IdempotencyRecord, IdempotencyStore, fingerprint_request
from app.redis.keys import InterviewRedisKeys
from app.redis.lock import InterviewLock
from app.redis.rate_limit import AnswerRateLimiter
from app.redis.runtime_state import InterviewRuntimeNode, InterviewRuntimeState


@pytest_asyncio.fixture()
async def real_redis_client():
    client = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await client.ping()
    except RedisError as exc:
        await client.aclose()
        pytest.skip(f"Redis is not reachable at {settings.redis_url}: {exc}")
    yield client
    await client.aclose()


@pytest.mark.asyncio
async def test_real_redis_set_get_delete_roundtrip(real_redis_client: Redis):
    session_id = uuid.uuid4()
    key = InterviewRedisKeys.state(session_id)
    state = InterviewRuntimeState(
        session_id=session_id,
        status=InterviewStatus.IN_PROGRESS,
        current_node=InterviewRuntimeNode.WAITING_FOR_ANSWER,
        question_number=1,
        question_limit=5,
        current_topic=InterviewTopic.RAG,
        current_question_id=uuid.uuid4(),
        difficulty=Difficulty.MEDIUM,
        last_action=None,
        version=1,
    )

    try:
        await real_redis_client.set(key, state.model_dump_json(), ex=60)

        raw = await real_redis_client.get(key)
        assert raw is not None
        assert InterviewRuntimeState.model_validate_json(raw) == state

        ttl = await real_redis_client.ttl(key)
        assert 0 < ttl <= 60
    finally:
        await real_redis_client.delete(key)


@pytest.mark.asyncio
async def test_real_redis_lock_mutual_exclusion_and_ownership(real_redis_client: Redis):
    session_id = uuid.uuid4()
    key = InterviewRedisKeys.lock(session_id)
    lock_a = InterviewLock(real_redis_client, session_id, ttl_seconds=30)
    lock_b = InterviewLock(real_redis_client, session_id, ttl_seconds=30)

    try:
        assert await lock_a.acquire() is True
        assert await lock_b.acquire() is False  # genuinely still held in real Redis

        await lock_b.release()  # B never owned it -> must not remove A's lock
        assert await real_redis_client.exists(key) == 1  # A's lock is untouched

        await lock_a.release()
        assert await real_redis_client.exists(key) == 0  # genuinely removed

        assert await lock_b.acquire() is True  # now free
    finally:
        await lock_a.release()
        await lock_b.release()
        await real_redis_client.delete(key)


@pytest.mark.asyncio
async def test_real_redis_rate_limiter_enforces_limit(real_redis_client: Redis):
    session_id = uuid.uuid4()
    limiter = AnswerRateLimiter(real_redis_client, limit=3, window_seconds=60)
    key = InterviewRedisKeys.rate_limit(session_id)

    try:
        for _ in range(3):
            allowed, _ = await limiter.check_and_increment(session_id)
            assert allowed is True

        allowed, retry_after = await limiter.check_and_increment(session_id)
        assert allowed is False
        assert retry_after > 0
    finally:
        await real_redis_client.delete(key)


@pytest.mark.asyncio
async def test_real_redis_idempotency_store_roundtrip_and_ttl(real_redis_client: Redis):
    session_id = uuid.uuid4()
    store = IdempotencyStore(real_redis_client, ttl_seconds=60)
    key = InterviewRedisKeys.idempotency(session_id, "abc123")

    record = IdempotencyRecord(
        fingerprint=fingerprint_request({"question_id": "q1", "answer": "Answer A"}),
        status_code=200,
        body={"data": {"status": "IN_PROGRESS"}},
    )

    try:
        assert await store.get(session_id, "abc123") is None

        await store.set(session_id, "abc123", record)
        fetched = await store.get(session_id, "abc123")
        assert fetched == record

        ttl = await real_redis_client.ttl(key)
        assert 0 < ttl <= 60
    finally:
        await real_redis_client.delete(key)
