import uuid

import pytest

from app.redis.exceptions import RedisProtectionUnavailableError
from app.redis.keys import InterviewRedisKeys
from app.redis.lock import InterviewLock
from tests.fakes import FailingAsyncRedis, FakeAsyncRedis


@pytest.fixture()
def fake_redis() -> FakeAsyncRedis:
    return FakeAsyncRedis()


@pytest.mark.asyncio
async def test_acquire_succeeds_when_free(fake_redis: FakeAsyncRedis):
    session_id = uuid.uuid4()
    lock = InterviewLock(fake_redis, session_id, ttl_seconds=30)

    assert await lock.acquire() is True
    assert InterviewRedisKeys.lock(session_id) in fake_redis.store


@pytest.mark.asyncio
async def test_second_acquisition_fails_while_held(fake_redis: FakeAsyncRedis):
    session_id = uuid.uuid4()
    lock_a = InterviewLock(fake_redis, session_id, ttl_seconds=30)
    lock_b = InterviewLock(fake_redis, session_id, ttl_seconds=30)

    assert await lock_a.acquire() is True
    assert await lock_b.acquire() is False


@pytest.mark.asyncio
async def test_locks_for_different_sessions_are_independent(fake_redis: FakeAsyncRedis):
    lock_a = InterviewLock(fake_redis, uuid.uuid4(), ttl_seconds=30)
    lock_b = InterviewLock(fake_redis, uuid.uuid4(), ttl_seconds=30)

    assert await lock_a.acquire() is True
    assert await lock_b.acquire() is True


@pytest.mark.asyncio
async def test_owner_can_release_and_lock_becomes_available(fake_redis: FakeAsyncRedis):
    session_id = uuid.uuid4()
    lock_a = InterviewLock(fake_redis, session_id, ttl_seconds=30)
    lock_b = InterviewLock(fake_redis, session_id, ttl_seconds=30)

    await lock_a.acquire()
    await lock_a.release()

    assert await lock_b.acquire() is True


@pytest.mark.asyncio
async def test_each_acquisition_uses_a_unique_ownership_token(fake_redis: FakeAsyncRedis):
    session_id = uuid.uuid4()
    lock_a = InterviewLock(fake_redis, session_id, ttl_seconds=30)
    await lock_a.acquire()
    token_a = fake_redis.store[InterviewRedisKeys.lock(session_id)]
    await lock_a.release()

    lock_b = InterviewLock(fake_redis, session_id, ttl_seconds=30)
    await lock_b.acquire()
    token_b = fake_redis.store[InterviewRedisKeys.lock(session_id)]

    assert token_a != token_b


@pytest.mark.asyncio
async def test_non_owner_cannot_release_a_lock_it_does_not_hold(fake_redis: FakeAsyncRedis):
    """Simulates request B's lock expiring and being re-acquired by request
    C, then B's delayed release() call arriving — B must not delete C's
    still-valid lock."""
    session_id = uuid.uuid4()
    key = InterviewRedisKeys.lock(session_id)

    lock_b = InterviewLock(fake_redis, session_id, ttl_seconds=30)
    await lock_b.acquire()

    # Simulate B's lock expiring and C acquiring a fresh one.
    fake_redis.force_expire(key)
    lock_c = InterviewLock(fake_redis, session_id, ttl_seconds=30)
    assert await lock_c.acquire() is True

    # B's late release() must not remove C's lock.
    await lock_b.release()

    assert await fake_redis.exists(key) == 1
    lock_d = InterviewLock(fake_redis, session_id, ttl_seconds=30)
    assert await lock_d.acquire() is False  # still held by C


@pytest.mark.asyncio
async def test_release_without_acquire_is_a_noop(fake_redis: FakeAsyncRedis):
    lock = InterviewLock(fake_redis, uuid.uuid4(), ttl_seconds=30)
    await lock.release()  # must not raise


@pytest.mark.asyncio
async def test_expired_lock_can_eventually_be_acquired(fake_redis: FakeAsyncRedis):
    session_id = uuid.uuid4()
    key = InterviewRedisKeys.lock(session_id)
    lock_a = InterviewLock(fake_redis, session_id, ttl_seconds=30)
    await lock_a.acquire()

    fake_redis.force_expire(key)

    lock_b = InterviewLock(fake_redis, session_id, ttl_seconds=30)
    assert await lock_b.acquire() is True


@pytest.mark.asyncio
async def test_redis_failure_on_acquire_is_surfaced_explicitly():
    lock = InterviewLock(FailingAsyncRedis(), uuid.uuid4(), ttl_seconds=30)

    with pytest.raises(RedisProtectionUnavailableError):
        await lock.acquire()


@pytest.mark.asyncio
async def test_redis_failure_on_release_is_surfaced_explicitly(fake_redis: FakeAsyncRedis):
    session_id = uuid.uuid4()
    lock = InterviewLock(fake_redis, session_id, ttl_seconds=30)
    await lock.acquire()

    lock._redis = FailingAsyncRedis()  # simulate Redis going down mid-request

    with pytest.raises(RedisProtectionUnavailableError):
        await lock.release()
