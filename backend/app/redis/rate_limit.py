from uuid import UUID

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.redis.exceptions import RedisProtectionUnavailableError
from app.redis.keys import InterviewRedisKeys

# Atomic fixed-window counter: INCR and the window-defining EXPIRE happen
# in one round trip, and EXPIRE is only applied on the first increment of
# a window (current == 1). A plain "INCR then EXPIRE" from Python would
# race under concurrency and could re-arm the TTL on every request,
# turning a fixed window into an ever-sliding one that never resets.
_INCR_AND_EXPIRE_SCRIPT = """
local current = redis.call("INCR", KEYS[1])
if current == 1 then
    redis.call("EXPIRE", KEYS[1], ARGV[1])
end
return current
"""


class AnswerRateLimiter:
    """Fixed-window rate limiter for answer submissions on one interview
    session (`interview:{session_id}:rate`)."""

    def __init__(self, redis_client: Redis, limit: int, window_seconds: int):
        self._redis = redis_client
        self._limit = limit
        self._window_seconds = window_seconds

    async def check_and_increment(self, session_id: UUID) -> tuple[bool, int]:
        """Increments the counter and returns `(allowed, retry_after_seconds)`.

        `retry_after_seconds` is only meaningful when `allowed` is False.
        """
        key = InterviewRedisKeys.rate_limit(session_id)
        try:
            current = await self._redis.eval(
                _INCR_AND_EXPIRE_SCRIPT, 1, key, self._window_seconds
            )
            current = int(current)
            if current > self._limit:
                ttl = await self._redis.ttl(key)
                retry_after = ttl if ttl and ttl > 0 else self._window_seconds
                return False, retry_after
            return True, 0
        except RedisError as exc:
            raise RedisProtectionUnavailableError(
                f"Rate limiter unavailable for session {session_id}"
            ) from exc
