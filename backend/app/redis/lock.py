import uuid
from uuid import UUID

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.redis.exceptions import RedisProtectionUnavailableError
from app.redis.keys import EvaluationRedisKeys, InterviewRedisKeys

# Compare-and-delete: only removes the key if it still holds the token this
# instance acquired. Plain `DEL` would be unsafe — by the time a slow
# request gets around to releasing, its lock may have already expired and
# been re-acquired by a different request, and a bare DEL would destroy
# that other request's lock instead of its own.
_RELEASE_IF_OWNER_SCRIPT = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("DEL", KEYS[1])
else
    return 0
end
"""


class InterviewLock:
    """Redis-backed distributed lock over one interview session's mutation
    sequence (`interview:{session_id}:lock`).

    Non-blocking: `acquire()` makes a single atomic `SET NX EX` attempt and
    returns immediately, never waiting for the lock to free up — callers
    that fail to acquire should surface a 409 rather than retry internally
    (see Task 12: "do not wait indefinitely").
    """

    def __init__(self, redis_client: Redis, session_id: UUID, ttl_seconds: int):
        self._redis = redis_client
        self._key = InterviewRedisKeys.lock(session_id)
        self._ttl_seconds = ttl_seconds
        self._token: str | None = None

    async def acquire(self) -> bool:
        token = uuid.uuid4().hex
        try:
            acquired = await self._redis.set(self._key, token, nx=True, ex=self._ttl_seconds)
        except RedisError as exc:
            raise RedisProtectionUnavailableError(
                f"Failed to acquire interview lock ({self._key})"
            ) from exc
        if acquired:
            self._token = token
            return True
        return False

    async def release(self) -> None:
        """No-op if this instance never held the lock (acquire() failed or
        was never called)."""
        if self._token is None:
            return
        token, self._token = self._token, None
        try:
            await self._redis.eval(_RELEASE_IF_OWNER_SCRIPT, 1, self._key, token)
        except RedisError as exc:
            raise RedisProtectionUnavailableError(
                f"Failed to release interview lock ({self._key})"
            ) from exc


class EvaluationLock:
    """Redis-backed distributed lock over one session's evaluation
    generation (`evaluation:{session_id}:lock`) — Task 53.

    Reuses the exact same non-blocking SET NX EX + compare-and-delete
    `_RELEASE_IF_OWNER_SCRIPT` primitive as `InterviewLock` above
    (imported, not reimplemented), and the same non-blocking semantics:
    `acquire()` makes one atomic attempt and returns immediately, never
    waiting for the lock to free up — a caller that fails to acquire
    should surface a stable busy error rather than retry internally, same
    as `InterviewLock`.

    Kept as its own class/key namespace instead of reusing `InterviewLock`
    with `interview:{session_id}:lock`: evaluation generation is a
    sibling of the interview lifecycle, not a mutation of it, so coupling
    its concurrency guard to the interview mutation lock would mean an
    in-flight evaluation generation blocks (or is blocked by) unrelated
    interview mutations for no reason. `InterviewLock` itself is left
    untouched.
    """

    def __init__(self, redis_client: Redis, session_id: UUID, ttl_seconds: int):
        self._redis = redis_client
        self._key = EvaluationRedisKeys.lock(session_id)
        self._ttl_seconds = ttl_seconds
        self._token: str | None = None

    async def acquire(self) -> bool:
        token = uuid.uuid4().hex
        try:
            acquired = await self._redis.set(self._key, token, nx=True, ex=self._ttl_seconds)
        except RedisError as exc:
            raise RedisProtectionUnavailableError(
                f"Failed to acquire evaluation lock ({self._key})"
            ) from exc
        if acquired:
            self._token = token
            return True
        return False

    async def release(self) -> None:
        """No-op if this instance never held the lock (acquire() failed or
        was never called)."""
        if self._token is None:
            return
        token, self._token = self._token, None
        try:
            await self._redis.eval(_RELEASE_IF_OWNER_SCRIPT, 1, self._key, token)
        except RedisError as exc:
            raise RedisProtectionUnavailableError(
                f"Failed to release evaluation lock ({self._key})"
            ) from exc
