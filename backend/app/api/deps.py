import logging

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.evaluation.service import EvaluationService
from app.knowledge.exceptions import KnowledgeError
from app.knowledge.factory import get_knowledge_retrieval_service as _get_configured_knowledge_retrieval_service
from app.knowledge.retrieval_service import KnowledgeRetrievalService
from app.llm.base import LLMProvider
from app.llm.factory import get_llm_provider as _get_configured_llm_provider
from app.redis.client import get_redis_client
from app.redis.exceptions import RateLimitExceededError
from app.redis.idempotency import IdempotencyStore
from app.redis.keys import InterviewRedisKeys
from app.redis.rate_limit import AnswerRateLimiter, FixedWindowRateLimiter
from app.redis.runtime_state_service import RuntimeStateService
from app.repositories.interview_repository import InterviewRepository
from app.services.interview_service import InterviewService
from app.services.result_service import ResultService
from app.voice.base import SttAuthProvider, TTSProvider
from app.voice.factory import get_stt_auth_provider as _get_configured_stt_auth_provider
from app.voice.factory import get_tts_provider as _get_configured_tts_provider
from app.voice.service import SttAuthService, TTSService
from app.workflows.interview.graph import InterviewWorkflow

logger = logging.getLogger(__name__)


def get_interview_repository(db: Session = Depends(get_db)) -> InterviewRepository:
    return InterviewRepository(db)


def get_llm_provider() -> LLMProvider:
    # A thin FastAPI-dependency wrapper around the module-level factory
    # singleton — kept separate so tests can override just this dependency
    # (e.g. with a `FakeLLMProvider`) without touching `app.llm.factory`.
    return _get_configured_llm_provider()


def get_knowledge_retrieval_service() -> KnowledgeRetrievalService | None:
    """A thin FastAPI-dependency wrapper around the module-level factory
    singleton (mirrors `get_llm_provider`) — kept separate so tests can
    override just this dependency (e.g. with a fake-backed service, or
    `None`) without touching `app.knowledge.factory`.

    Returns `None` — never raises — if the knowledge layer isn't
    configured (e.g. no `EMBEDDING_API_KEY`): question generation must
    keep working ungrounded rather than fail every `/start`/`/answers`
    request just because RAG isn't set up. Qdrant connectivity itself is
    never checked here either way — it stays lazy (Task 19), only
    attempted when a graph turn actually retrieves.
    """
    try:
        return _get_configured_knowledge_retrieval_service()
    except KnowledgeError:
        logger.warning(
            "Knowledge retrieval service is not configured; question generation will proceed ungrounded."
        )
        return None


def get_interview_workflow(
    repository: InterviewRepository = Depends(get_interview_repository),
    llm_provider: LLMProvider = Depends(get_llm_provider),
    knowledge_service: KnowledgeRetrievalService | None = Depends(get_knowledge_retrieval_service),
) -> InterviewWorkflow:
    # Built fresh per request: it closes over this request's `repository`
    # (and therefore its DB session), which must not be shared across
    # requests. `llm_provider`/`knowledge_service` are still the shared
    # singleton clients — only the graph wiring is rebuilt per request,
    # never a new LLM/embedding/Qdrant client.
    return InterviewWorkflow(
        repository=repository,
        llm_provider=llm_provider,
        knowledge_service=knowledge_service,
        knowledge_retrieval_limit=settings.knowledge_retrieval_limit,
    )


def get_interview_service(
    repository: InterviewRepository = Depends(get_interview_repository),
    workflow: InterviewWorkflow = Depends(get_interview_workflow),
) -> InterviewService:
    return InterviewService(repository, workflow)


def get_evaluation_service(
    repository: InterviewRepository = Depends(get_interview_repository),
    llm_provider: LLMProvider = Depends(get_llm_provider),
    redis_client: Redis = Depends(get_redis_client),
) -> EvaluationService:
    # A sibling of `get_interview_service`, not built on top of it: it
    # shares the same request-scoped repository/DB session, but needs no
    # `InterviewWorkflow`/knowledge service — evaluation is a single
    # structured LLM call over a finished transcript, not an adaptive
    # graph turn. `redis_client` backs its evaluation-generation lock
    # (Task 53). No dedicated `redis_evaluation_lock_ttl_seconds` setting:
    # evaluation generation is bounded by the same one structured LLM
    # call as an interview turn, so `redis_interview_lock_ttl_seconds`'s
    # existing 30s bound already fits without inventing a new knob for it.
    return EvaluationService(
        repository, llm_provider, redis_client, settings.redis_interview_lock_ttl_seconds
    )


def get_result_service(
    repository: InterviewRepository = Depends(get_interview_repository),
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> ResultService:
    # Also a sibling, sharing the same request-scoped repository — assembles
    # the read-only result report on top of `EvaluationService`'s existing
    # idempotent generate-or-load behavior, never duplicating it.
    return ResultService(repository, evaluation_service)


def get_runtime_state_service(
    repository: InterviewRepository = Depends(get_interview_repository),
    redis_client: Redis = Depends(get_redis_client),
) -> RuntimeStateService:
    return RuntimeStateService(redis_client=redis_client, repository=repository)


def get_answer_rate_limiter(redis_client: Redis = Depends(get_redis_client)) -> AnswerRateLimiter:
    return AnswerRateLimiter(
        redis_client=redis_client,
        limit=settings.redis_interview_rate_limit,
        window_seconds=settings.redis_interview_rate_window_seconds,
    )


def _client_identity(request: Request) -> str:
    """Best-effort per-client identity for the IP-scoped rate limiters
    below. Deliberately uses only `request.client.host` — the actual TCP
    peer address Starlette/uvicorn observed — never a client-supplied
    header such as `X-Forwarded-For`: this deployment has no configured
    trusted-proxy chain that would make such a header authoritative rather
    than trivially spoofable by the caller itself. Never logged anywhere
    (see each rate-limit dependency below)."""
    return request.client.host if request.client is not None else "unknown"


async def _enforce_client_rate_limit(
    request: Request,
    redis_client: Redis,
    *,
    namespace: str,
    limit: int,
    window_seconds: int,
    message: str,
) -> None:
    """Shared implementation for the four per-client (IP-based) rate
    limiters below (Task 46) — endpoints reachable with no interview
    session yet to scope a limit by, on an application that has no
    authentication, so these are the only abuse protection available for
    them. Each of the four dependencies below is a thin, endpoint-specific
    wrapper over this one function so route handlers stay a single
    `Depends(...)` line each; none of this logic lives in a route handler.

    A `RedisProtectionUnavailableError` from `check_and_increment` is
    deliberately left to propagate rather than caught here — `app.main`
    already registers a global handler for it that returns the exact same
    503 `REDIS_UNAVAILABLE` response the rest of the app uses, so a Redis
    outage here fails the same way it does everywhere else: never silently
    treated as "allowed"."""
    limiter = FixedWindowRateLimiter(redis_client, limit=limit, window_seconds=window_seconds)
    key = InterviewRedisKeys.client_rate_limit(namespace, _client_identity(request))
    allowed, retry_after = await limiter.check_and_increment(key)
    if not allowed:
        raise RateLimitExceededError(retry_after_seconds=retry_after, message=message)


async def enforce_interview_creation_rate_limit(
    request: Request, redis_client: Redis = Depends(get_redis_client)
) -> None:
    await _enforce_client_rate_limit(
        request,
        redis_client,
        namespace="interview:create",
        limit=settings.interview_creation_rate_limit,
        window_seconds=settings.interview_creation_rate_window_seconds,
        message="Too many interview creation requests. Please try again later.",
    )


async def enforce_interview_start_rate_limit(
    request: Request, redis_client: Redis = Depends(get_redis_client)
) -> None:
    await _enforce_client_rate_limit(
        request,
        redis_client,
        namespace="interview:start",
        limit=settings.interview_start_rate_limit,
        window_seconds=settings.interview_start_rate_window_seconds,
        message="Too many interview start requests. Please try again later.",
    )


async def enforce_voice_tts_rate_limit(
    request: Request, redis_client: Redis = Depends(get_redis_client)
) -> None:
    await _enforce_client_rate_limit(
        request,
        redis_client,
        namespace="voice:tts",
        limit=settings.voice_tts_rate_limit,
        window_seconds=settings.voice_tts_rate_window_seconds,
        message="Too many text-to-speech requests. Please try again later.",
    )


async def enforce_voice_stt_token_rate_limit(
    request: Request, redis_client: Redis = Depends(get_redis_client)
) -> None:
    await _enforce_client_rate_limit(
        request,
        redis_client,
        namespace="voice:stt-token",
        limit=settings.voice_stt_token_rate_limit,
        window_seconds=settings.voice_stt_token_rate_window_seconds,
        message="Too many voice input requests. Please try again later.",
    )


def get_idempotency_store(redis_client: Redis = Depends(get_redis_client)) -> IdempotencyStore:
    return IdempotencyStore(redis_client=redis_client, ttl_seconds=settings.redis_idempotency_ttl_seconds)


def get_tts_provider() -> TTSProvider:
    # A thin FastAPI-dependency wrapper around the module-level factory
    # singleton (mirrors `get_llm_provider`) — kept separate so tests can
    # override just this dependency (e.g. with a fake provider) without
    # touching `app.voice.factory`. Unlike `get_knowledge_retrieval_service`,
    # this does not catch configuration errors: a misconfigured Azure
    # Speech setup must fail clearly (VOICE_SERVICE_MISCONFIGURED), never
    # degrade silently.
    return _get_configured_tts_provider()


def get_tts_service(provider: TTSProvider = Depends(get_tts_provider)) -> TTSService:
    return TTSService(provider)


def get_stt_auth_provider() -> SttAuthProvider:
    # Mirrors get_tts_provider exactly — never catches a configuration
    # error, so a missing DEEPGRAM_API_KEY fails clearly rather than
    # degrading silently.
    return _get_configured_stt_auth_provider()


def get_stt_auth_service(provider: SttAuthProvider = Depends(get_stt_auth_provider)) -> SttAuthService:
    return SttAuthService(provider)
