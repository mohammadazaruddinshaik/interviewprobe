import hashlib
import json
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.redis.exceptions import RedisProtectionUnavailableError
from app.redis.keys import InterviewRedisKeys

MIN_IDEMPOTENCY_KEY_LENGTH = 1
MAX_IDEMPOTENCY_KEY_LENGTH = 128


class IdempotencyRecord(BaseModel):
    """Just enough to replay a prior response: the fingerprint of the
    request that produced it (to detect key reuse with a different
    payload), plus the HTTP status and JSON body to reproduce. Never the
    interview transcript, LLM prompts, or anything beyond one response."""

    fingerprint: str
    status_code: int
    body: dict[str, Any]


def fingerprint_request(payload: dict[str, Any]) -> str:
    """Deterministic hash of the parts of a request that must match for an
    Idempotency-Key to be reused safely."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class IdempotencyStore:
    """Redis-backed idempotent-response cache, keyed by
    `interview:{session_id}:idempotency:{idempotency_key}`."""

    def __init__(self, redis_client: Redis, ttl_seconds: int):
        self._redis = redis_client
        self._ttl_seconds = ttl_seconds

    async def get(self, session_id: UUID, idempotency_key: str) -> IdempotencyRecord | None:
        key = InterviewRedisKeys.idempotency(session_id, idempotency_key)
        try:
            raw = await self._redis.get(key)
        except RedisError as exc:
            raise RedisProtectionUnavailableError(
                f"Idempotency store unavailable for session {session_id}"
            ) from exc
        if raw is None:
            return None
        return IdempotencyRecord.model_validate_json(raw)

    async def set(self, session_id: UUID, idempotency_key: str, record: IdempotencyRecord) -> None:
        key = InterviewRedisKeys.idempotency(session_id, idempotency_key)
        try:
            await self._redis.set(key, record.model_dump_json(), ex=self._ttl_seconds)
        except RedisError as exc:
            raise RedisProtectionUnavailableError(
                f"Idempotency store unavailable for session {session_id}"
            ) from exc
