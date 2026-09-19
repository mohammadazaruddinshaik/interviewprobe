from uuid import UUID


class InterviewRedisKeys:
    """Centralized, deterministic Redis key construction for the interview
    runtime-state, locking, rate-limiting, and idempotency layers. No other
    module should build these key strings directly."""

    @staticmethod
    def state(session_id: UUID) -> str:
        return f"interview:{session_id}:state"

    @staticmethod
    def lock(session_id: UUID) -> str:
        return f"interview:{session_id}:lock"

    @staticmethod
    def rate_limit(session_id: UUID) -> str:
        return f"interview:{session_id}:rate"

    @staticmethod
    def idempotency(session_id: UUID, idempotency_key: str) -> str:
        return f"interview:{session_id}:idempotency:{idempotency_key}"
