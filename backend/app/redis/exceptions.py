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


class EvaluationLockBusyError(Exception):
    """Another request is currently generating this session's evaluation
    (Task 53). Non-blocking, same as `InterviewLockBusyError` — the
    caller must not wait internally, only surface a 409 so the client can
    retry."""


class RateLimitExceededError(Exception):
    """A rate limit was exceeded — originally answer submissions only, now
    also the per-client limiters in `app/api/deps.py` (Task 46). Carries
    the number of seconds until the window resets so the API layer can set
    a `Retry-After` header. `message` defaults to the original
    answer-submission wording so every existing call site is unaffected;
    other call sites pass an endpoint-appropriate message. Either way,
    `main.py`'s handler always maps this to the same `RATE_LIMITED` error
    code — only the message varies."""

    def __init__(self, retry_after_seconds: int, message: str = "Too many answer submissions. Please try again shortly."):
        self.retry_after_seconds = retry_after_seconds
        super().__init__(message)


class IdempotencyKeyReusedError(Exception):
    """The same Idempotency-Key was reused with a materially different
    request payload."""
