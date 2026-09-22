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

    @staticmethod
    def client_rate_limit(namespace: str, client_id: str) -> str:
        """Key for a per-client (not per-session) rate limiter — used for
        endpoints reachable before any interview session exists (creation,
        voice synthesis/token issuance) where there is no session_id to
        scope by. `namespace` identifies the protected endpoint (e.g.
        "interview:create", "voice:tts") so different endpoints never
        share a bucket even for the same client."""
        return f"{namespace}:{client_id}"


class EvaluationRedisKeys:
    """Centralized Redis key construction for evaluation-generation
    concurrency control (Task 53).

    Deliberately its own class/namespace rather than another method on
    `InterviewRedisKeys` above: evaluation generation is a sibling of the
    interview lifecycle, not a mutation of it (see `EvaluationService`'s
    docstring), so its lock lives under its own `evaluation:` prefix
    rather than sharing `interview:{session_id}:lock` — an in-flight
    evaluation must not block, or be blocked by, unrelated interview
    mutations.
    """

    @staticmethod
    def lock(session_id: UUID) -> str:
        return f"evaluation:{session_id}:lock"
