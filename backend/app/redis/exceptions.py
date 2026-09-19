class RedisProtectionUnavailableError(Exception):
    """Redis is required for a concurrency/safety guarantee (lock, rate
    limit, idempotency) and is currently unavailable.

    Unlike `RuntimeStateUnavailableError` (Task 11), which is deliberately
    tolerated because runtime-state mirroring is best-effort, this error
    means a required *safety* check could not be performed — the caller
    must not proceed as if the guarantee were satisfied. Maps to 503.
    """


class InterviewLockBusyError(Exception):
    """Another request currently holds the interview's mutation lock."""


class RateLimitExceededError(Exception):
    """The answer-submission rate limit for this interview session was
    exceeded. Carries the number of seconds until the window resets so the
    API layer can set a `Retry-After` header."""

    def __init__(self, retry_after_seconds: int):
        self.retry_after_seconds = retry_after_seconds
        super().__init__("Too many answer submissions. Please try again shortly.")


class IdempotencyKeyReusedError(Exception):
    """The same Idempotency-Key was reused with a materially different
    request payload."""
