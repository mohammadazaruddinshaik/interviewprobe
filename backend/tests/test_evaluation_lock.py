"""Task 53 — `EvaluationLock`/`EvaluationRedisKeys` in isolation, mirroring
tests/test_redis_lock.py's coverage of `InterviewLock` exactly: same
non-blocking SET NX EX + ownership-safe release primitive, reused
unchanged (`_RELEASE_IF_OWNER_SCRIPT`), just under its own
`evaluation:{session_id}:lock` key namespace so it never collides with
`InterviewLock`'s `interview:{session_id}:lock`.
"""

import uuid

import pytest

from app.redis.exceptions import RedisProtectionUnavailableError
from app.redis.keys import EvaluationRedisKeys, InterviewRedisKeys
from app.redis.lock import EvaluationLock
from tests.fakes import FailingAsyncRedis, FakeAsyncRedis


@pytest.fixture()
def fake_redis() -> FakeAsyncRedis:
    return FakeAsyncRedis()


def test_key_namespace_is_distinct_from_the_interview_lock():
    session_id = uuid.uuid4()

    assert EvaluationRedisKeys.lock(session_id) == f"evaluation:{session_id}:lock"
    assert EvaluationRedisKeys.lock(session_id) != InterviewRedisKeys.lock(session_id)


@pytest.mark.asyncio
async def test_acquire_succeeds_when_free(fake_redis: FakeAsyncRedis):
    session_id = uuid.uuid4()
    lock = EvaluationLock(fake_redis, session_id, ttl_seconds=30)

    assert await lock.acquire() is True
    assert EvaluationRedisKeys.lock(session_id) in fake_redis.store


@pytest.mark.asyncio
async def test_second_acquisition_fails_while_held(fake_redis: FakeAsyncRedis):
    session_id = uuid.uuid4()
    lock_a = EvaluationLock(fake_redis, session_id, ttl_seconds=30)
    lock_b = EvaluationLock(fake_redis, session_id, ttl_seconds=30)

    assert await lock_a.acquire() is True
    assert await lock_b.acquire() is False


@pytest.mark.asyncio
async def test_locks_for_different_sessions_are_independent(fake_redis: FakeAsyncRedis):
    lock_a = EvaluationLock(fake_redis, uuid.uuid4(), ttl_seconds=30)
    lock_b = EvaluationLock(fake_redis, uuid.uuid4(), ttl_seconds=30)

    assert await lock_a.acquire() is True
    assert await lock_b.acquire() is True


@pytest.mark.asyncio
async def test_an_interview_lock_on_the_same_session_does_not_block_the_evaluation_lock(fake_redis: FakeAsyncRedis):
    """The whole point of the separate `evaluation:` namespace (Task 53):
    an in-flight interview mutation lock must never block, or be blocked
    by, evaluation generation for the same session."""
    from app.redis.lock import InterviewLock

    session_id = uuid.uuid4()
    interview_lock = InterviewLock(fake_redis, session_id, ttl_seconds=30)
    evaluation_lock = EvaluationLock(fake_redis, session_id, ttl_seconds=30)

    assert await interview_lock.acquire() is True
    assert await evaluation_lock.acquire() is True


@pytest.mark.asyncio
async def test_owner_can_release_and_lock_becomes_available(fake_redis: FakeAsyncRedis):
    session_id = uuid.uuid4()
    lock_a = EvaluationLock(fake_redis, session_id, ttl_seconds=30)
    lock_b = EvaluationLock(fake_redis, session_id, ttl_seconds=30)

    await lock_a.acquire()
    await lock_a.release()

    assert await lock_b.acquire() is True


@pytest.mark.asyncio
async def test_non_owner_cannot_release_a_lock_it_does_not_hold(fake_redis: FakeAsyncRedis):
    """Simulates request B's lock expiring and being re-acquired by request
    C, then B's delayed release() call arriving — B must not delete C's
    still-valid lock."""
    session_id = uuid.uuid4()
    key = EvaluationRedisKeys.lock(session_id)

    lock_b = EvaluationLock(fake_redis, session_id, ttl_seconds=30)
    await lock_b.acquire()

    fake_redis.force_expire(key)
    lock_c = EvaluationLock(fake_redis, session_id, ttl_seconds=30)
    assert await lock_c.acquire() is True

    await lock_b.release()

    assert await fake_redis.exists(key) == 1
    lock_d = EvaluationLock(fake_redis, session_id, ttl_seconds=30)
    assert await lock_d.acquire() is False  # still held by C


@pytest.mark.asyncio
async def test_release_without_acquire_is_a_noop(fake_redis: FakeAsyncRedis):
    lock = EvaluationLock(fake_redis, uuid.uuid4(), ttl_seconds=30)
    await lock.release()  # must not raise


@pytest.mark.asyncio
async def test_redis_failure_on_acquire_is_surfaced_explicitly():
    lock = EvaluationLock(FailingAsyncRedis(), uuid.uuid4(), ttl_seconds=30)

    with pytest.raises(RedisProtectionUnavailableError):
        await lock.acquire()


@pytest.mark.asyncio
async def test_redis_failure_on_release_is_surfaced_explicitly(fake_redis: FakeAsyncRedis):
    session_id = uuid.uuid4()
    lock = EvaluationLock(fake_redis, session_id, ttl_seconds=30)
    await lock.acquire()

    lock._redis = FailingAsyncRedis()  # simulate Redis going down mid-request

    with pytest.raises(RedisProtectionUnavailableError):
        await lock.release()
