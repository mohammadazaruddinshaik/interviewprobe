from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.interviews import router as interviews_router
from app.core.config import settings
from app.llm.exceptions import (
    LLMConfigurationError,
    LLMError,
    LLMInvalidResponseError,
    LLMProviderUnavailableError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from app.redis.client import create_redis_pool
from app.redis.exceptions import (
    IdempotencyKeyReusedError,
    InterviewLockBusyError,
    RateLimitExceededError,
    RedisProtectionUnavailableError,
)
from app.services.interview_service import (
    InterviewNotFoundError,
    InvalidInterviewStateError,
    InvalidQuestionError,
    InvalidRoleTopicSelectionError,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Created at startup, not at import time — see app/redis/client.py.
    app.state.redis_pool = create_redis_pool()
    try:
        yield
    finally:
        await app.state.redis_pool.disconnect()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

# Task 25A: the frontend (Vite dev server) and this API run on different
# origins/ports, so the browser requires CORS to allow the request at all.
# No cookies/session credentials are used by this flow, so
# `allow_credentials` stays at its default (False) — only the specific
# local dev origins, methods, and headers actually needed are allowed.
# `Idempotency-Key` (Task 26) is required on answer submissions.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Idempotency-Key"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


_SERVICE_ERROR_STATUS_CODES: dict[type[Exception], tuple[int, str]] = {
    InterviewNotFoundError: (404, "INTERVIEW_NOT_FOUND"),
    InvalidInterviewStateError: (409, "INVALID_INTERVIEW_STATE"),
    InvalidQuestionError: (409, "INVALID_QUESTION"),
    InvalidRoleTopicSelectionError: (422, "INVALID_ROLE_TOPIC"),
    InterviewLockBusyError: (409, "INTERVIEW_BUSY"),
    IdempotencyKeyReusedError: (409, "IDEMPOTENCY_KEY_REUSED"),
}


def _handle_interview_service_error(request: Request, exc: Exception) -> JSONResponse:
    status_code, code = _SERVICE_ERROR_STATUS_CODES[type(exc)]
    return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": str(exc)}})


for _exc_type in _SERVICE_ERROR_STATUS_CODES:
    app.add_exception_handler(_exc_type, _handle_interview_service_error)


def _handle_rate_limit_exceeded(request: Request, exc: RateLimitExceededError) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"error": {"code": "RATE_LIMITED", "message": str(exc)}},
        headers={"Retry-After": str(exc.retry_after_seconds)},
    )


app.add_exception_handler(RateLimitExceededError, _handle_rate_limit_exceeded)


def _handle_redis_protection_unavailable(request: Request, exc: RedisProtectionUnavailableError) -> JSONResponse:
    # Deliberately not str(exc) — that message can include internal Redis
    # key names, which must not leak to API clients.
    return JSONResponse(
        status_code=503,
        content={
            "error": {
                "code": "REDIS_UNAVAILABLE",
                "message": "A required concurrency-safety service is temporarily unavailable. Please try again.",
            }
        },
    )


app.add_exception_handler(RedisProtectionUnavailableError, _handle_redis_protection_unavailable)


# LangGraph/LLM failures (analysis, decision, or question generation) are
# translated into the same `{"error": {"code", "message"}}` envelope as
# every other domain error — never a raw 500, and never provider/prompt
# details. `LLMError` itself is registered too, as a catch-all for any
# subclass not listed individually (Starlette picks the most specific
# handler registered for an exception's MRO).
_LLM_ERROR_RESPONSES: dict[type[Exception], tuple[int, str, str]] = {
    LLMTimeoutError: (
        504,
        "AI_SERVICE_TIMEOUT",
        "The interview assistant took too long to respond. Please try again.",
    ),
    LLMRateLimitError: (
        429,
        "AI_SERVICE_RATE_LIMITED",
        "The interview assistant is temporarily rate limited. Please try again shortly.",
    ),
    LLMProviderUnavailableError: (
        503,
        "AI_SERVICE_UNAVAILABLE",
        "The interview assistant is temporarily unavailable. Please try again.",
    ),
    LLMInvalidResponseError: (
        502,
        "AI_SERVICE_INVALID_RESPONSE",
        "The interview assistant returned an unexpected response. Please try again.",
    ),
    LLMConfigurationError: (
        500,
        "AI_SERVICE_MISCONFIGURED",
        "The interview assistant is not configured correctly.",
    ),
    LLMError: (
        502,
        "AI_SERVICE_ERROR",
        "The interview assistant encountered an error. Please try again.",
    ),
}


def _handle_llm_error(request: Request, exc: LLMError) -> JSONResponse:
    # Deliberately not str(exc) — provider error messages can include
    # provider/model identifiers or other internals that must not reach
    # the candidate. Only the fixed, generic message for this error type.
    # Walks the MRO (rather than indexing by `type(exc)` directly) so any
    # `LLMError` subclass not individually listed still falls back to the
    # generic `LLMError` entry instead of raising a KeyError.
    for exc_type in type(exc).__mro__:
        response = _LLM_ERROR_RESPONSES.get(exc_type)
        if response is not None:
            status_code, code, message = response
            return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message}})
    raise AssertionError("unreachable: LLMError is always registered")  # pragma: no cover


for _exc_type in _LLM_ERROR_RESPONSES:
    app.add_exception_handler(_exc_type, _handle_llm_error)


app.include_router(interviews_router, prefix="/api/v1/interviews", tags=["interviews"])
