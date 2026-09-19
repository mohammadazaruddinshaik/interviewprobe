import uuid

import pytest

from app.redis.exceptions import RedisProtectionUnavailableError
from app.redis.idempotency import IdempotencyRecord, IdempotencyStore, fingerprint_request
from app.redis.keys import InterviewRedisKeys
from tests.fakes import FailingAsyncRedis, FakeAsyncRedis


@pytest.fixture()
def fake_redis() -> FakeAsyncRedis:
    return FakeAsyncRedis()


@pytest.fixture()
def store(fake_redis: FakeAsyncRedis) -> IdempotencyStore:
    return IdempotencyStore(fake_redis, ttl_seconds=86400)


def sample_record(**overrides) -> IdempotencyRecord:
    defaults = dict(
        fingerprint=fingerprint_request({"question_id": "q1", "answer": "Answer A"}),
        status_code=200,
        body={"data": {"status": "IN_PROGRESS"}},
    )
    defaults.update(overrides)
    return IdempotencyRecord(**defaults)


# ---------------------------------------------------------------------------
# Fingerprint
# ---------------------------------------------------------------------------


def test_fingerprint_is_deterministic_for_identical_payloads():
    a = fingerprint_request({"question_id": "q1", "answer": "Answer A"})
    b = fingerprint_request({"question_id": "q1", "answer": "Answer A"})

    assert a == b


def test_fingerprint_differs_for_different_payloads():
    a = fingerprint_request({"question_id": "q1", "answer": "Answer A"})
    b = fingerprint_request({"question_id": "q1", "answer": "Different answer"})

    assert a != b


def test_fingerprint_is_independent_of_key_order():
    a = fingerprint_request({"question_id": "q1", "answer": "Answer A"})
    b = fingerprint_request({"answer": "Answer A", "question_id": "q1"})

    assert a == b


# ---------------------------------------------------------------------------
# Set / get
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_returns_none_when_not_set(store: IdempotencyStore):
    assert await store.get(uuid.uuid4(), "abc123") is None


@pytest.mark.asyncio
async def test_set_then_get_returns_identical_record(store: IdempotencyStore):
    session_id = uuid.uuid4()
    record = sample_record()

    await store.set(session_id, "abc123", record)
    fetched = await store.get(session_id, "abc123")

    assert fetched == record


@pytest.mark.asyncio
async def test_keys_are_scoped_by_session_and_idempotency_key(store: IdempotencyStore):
    record = sample_record()
    session_a, session_b = uuid.uuid4(), uuid.uuid4()

    await store.set(session_a, "abc123", record)

    assert await store.get(session_a, "abc123") == record
    assert await store.get(session_b, "abc123") is None
    assert await store.get(session_a, "different-key") is None


@pytest.mark.asyncio
async def test_stored_under_the_deterministic_key_format(
    store: IdempotencyStore, fake_redis: FakeAsyncRedis
):
    session_id = uuid.uuid4()
    await store.set(session_id, "abc123", sample_record())

    key = InterviewRedisKeys.idempotency(session_id, "abc123")
    assert key in fake_redis.store
    assert key == f"interview:{session_id}:idempotency:abc123"


@pytest.mark.asyncio
async def test_set_applies_configured_ttl(fake_redis: FakeAsyncRedis):
    store = IdempotencyStore(fake_redis, ttl_seconds=86400)
    session_id = uuid.uuid4()

    await store.set(session_id, "abc123", sample_record())

    key = InterviewRedisKeys.idempotency(session_id, "abc123")
    assert fake_redis.ttls[key] == 86400


# ---------------------------------------------------------------------------
# Redis failure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_redis_failure_on_get_is_surfaced_explicitly():
    store = IdempotencyStore(FailingAsyncRedis(), ttl_seconds=86400)

    with pytest.raises(RedisProtectionUnavailableError):
        await store.get(uuid.uuid4(), "abc123")


@pytest.mark.asyncio
async def test_redis_failure_on_set_is_surfaced_explicitly():
    store = IdempotencyStore(FailingAsyncRedis(), ttl_seconds=86400)

    with pytest.raises(RedisProtectionUnavailableError):
        await store.set(uuid.uuid4(), "abc123", sample_record())
