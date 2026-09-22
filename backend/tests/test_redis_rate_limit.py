import asyncio
import uuid

import pytest

from app.redis.exceptions import RedisProtectionUnavailableError
from app.redis.keys import InterviewRedisKeys
from app.redis.rate_limit import AnswerRateLimiter, FixedWindowRateLimiter
from tests.fakes import FailingAsyncRedis, FakeAsyncRedis


@pytest.fixture()
def fake_redis() -> FakeAsyncRedis:
    return FakeAsyncRedis()


@pytest.mark.asyncio
async def test_first_ten_requests_are_allowed(fake_redis: FakeAsyncRedis):
    limiter = AnswerRateLimiter(fake_redis, limit=10, window_seconds=60)
    session_id = uuid.uuid4()

    for _ in range(10):
        allowed, _ = await limiter.check_and_increment(session_id)
        assert allowed is True


@pytest.mark.asyncio
async def test_eleventh_request_is_rejected(fake_redis: FakeAsyncRedis):
    limiter = AnswerRateLimiter(fake_redis, limit=10, window_seconds=60)
    session_id = uuid.uuid4()

    for _ in range(10):
        await limiter.check_and_increment(session_id)

    allowed, retry_after = await limiter.check_and_increment(session_id)

    assert allowed is False
    assert retry_after > 0


@pytest.mark.asyncio
async def test_sessions_are_rate_limited_independently(fake_redis: FakeAsyncRedis):
    limiter = AnswerRateLimiter(fake_redis, limit=2, window_seconds=60)
    session_a = uuid.uuid4()
    session_b = uuid.uuid4()

    await limiter.check_and_increment(session_a)
    await limiter.check_and_increment(session_a)
    allowed_a, _ = await limiter.check_and_increment(session_a)

    allowed_b, _ = await limiter.check_and_increment(session_b)

    assert allowed_a is False
    assert allowed_b is True


@pytest.mark.asyncio
async def test_window_expiration_resets_the_counter(fake_redis: FakeAsyncRedis):
    limiter = AnswerRateLimiter(fake_redis, limit=2, window_seconds=60)
    session_id = uuid.uuid4()

    await limiter.check_and_increment(session_id)
    await limiter.check_and_increment(session_id)
    allowed, _ = await limiter.check_and_increment(session_id)
    assert allowed is False

    fake_redis.force_expire(InterviewRedisKeys.rate_limit(session_id))

    allowed_after_reset, _ = await limiter.check_and_increment(session_id)
    assert allowed_after_reset is True


@pytest.mark.asyncio
async def test_ttl_is_set_only_on_the_first_increment_of_a_window(fake_redis: FakeAsyncRedis):
    limiter = AnswerRateLimiter(fake_redis, limit=10, window_seconds=60)
    session_id = uuid.uuid4()
    key = InterviewRedisKeys.rate_limit(session_id)

    await limiter.check_and_increment(session_id)
    first_ttl = fake_redis.ttls[key]

    await limiter.check_and_increment(session_id)
    second_ttl = fake_redis.ttls[key]

    assert first_ttl == 60
    assert second_ttl == 60  # not re-armed/extended by the second increment


@pytest.mark.asyncio
async def test_concurrent_increments_do_not_exceed_or_undercount(fake_redis: FakeAsyncRedis):
    """20 'concurrent' requests against a limit of 10 must yield exactly 10
    allowed and 10 rejected — no double-counting or lost increments from
    interleaving (FakeAsyncRedis yields via asyncio.sleep(0) on every call,
    so this genuinely exercises interleaved execution, not just sequential
    calls that happen to be awaited one after another)."""
    limiter = AnswerRateLimiter(fake_redis, limit=10, window_seconds=60)
    session_id = uuid.uuid4()

    results = await asyncio.gather(*[limiter.check_and_increment(session_id) for _ in range(20)])

    allowed_count = sum(1 for allowed, _ in results if allowed)
    assert allowed_count == 10


@pytest.mark.asyncio
async def test_redis_failure_is_surfaced_explicitly():
    limiter = AnswerRateLimiter(FailingAsyncRedis(), limit=10, window_seconds=60)

    with pytest.raises(RedisProtectionUnavailableError):
        await limiter.check_and_increment(uuid.uuid4())


# ---------------------------------------------------------------------------
# FixedWindowRateLimiter (Task 46) — the generic primitive AnswerRateLimiter
# above now delegates to, and the per-client limiters in app/api/deps.py are
# built on. Exercised directly here over an arbitrary string key, since it
# no longer knows anything about sessions/UUIDs.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generic_limiter_allows_up_to_the_limit_then_rejects(fake_redis: FakeAsyncRedis):
    limiter = FixedWindowRateLimiter(fake_redis, limit=3, window_seconds=60)

    for _ in range(3):
        allowed, _ = await limiter.check_and_increment("voice:tts:127.0.0.1")
        assert allowed is True

    allowed, retry_after = await limiter.check_and_increment("voice:tts:127.0.0.1")
    assert allowed is False
    assert retry_after > 0


@pytest.mark.asyncio
async def test_generic_limiter_keys_are_independent(fake_redis: FakeAsyncRedis):
    limiter = FixedWindowRateLimiter(fake_redis, limit=1, window_seconds=60)

    allowed_a, _ = await limiter.check_and_increment("voice:tts:1.1.1.1")
    allowed_a_again, _ = await limiter.check_and_increment("voice:tts:1.1.1.1")
    allowed_b, _ = await limiter.check_and_increment("voice:stt-token:1.1.1.1")

    assert allowed_a is True
    assert allowed_a_again is False  # same key, budget already spent
    assert allowed_b is True  # different namespace, independent budget


@pytest.mark.asyncio
async def test_generic_limiter_redis_failure_is_surfaced_explicitly():
    limiter = FixedWindowRateLimiter(FailingAsyncRedis(), limit=10, window_seconds=60)

    with pytest.raises(RedisProtectionUnavailableError):
        await limiter.check_and_increment("interview:create:127.0.0.1")


def test_client_rate_limit_key_is_namespaced_by_endpoint_and_client():
    create_key = InterviewRedisKeys.client_rate_limit("interview:create", "127.0.0.1")
    start_key = InterviewRedisKeys.client_rate_limit("interview:start", "127.0.0.1")

    assert create_key == "interview:create:127.0.0.1"
    assert start_key == "interview:start:127.0.0.1"
    assert create_key != start_key  # same client, different endpoint -> different bucket
