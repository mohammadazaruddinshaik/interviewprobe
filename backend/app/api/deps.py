import logging
import uuid

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.orm import Session

from app.auth.exceptions import AuthenticationRequiredError
from app.auth.google import GoogleIdentityVerifier, get_configured_google_verifier
from app.auth.service import AuthService
from app.core.config import settings
from app.db.session import get_db
from app.evaluation.service import EvaluationService
from app.knowledge.exceptions import KnowledgeError
from app.knowledge.factory import get_knowledge_retrieval_service as _get_configured_knowledge_retrieval_service
from app.knowledge.retrieval_service import KnowledgeRetrievalService
from app.llm.base import LLMProvider
from app.models.user import User
from app.llm.factory import get_llm_provider as _get_configured_llm_provider
from app.investigation.investigator import ClaimInvestigator, LLMClaimInvestigator
from app.planning.planner import InterviewPlanner, LLMInterviewPlanner
from app.redis.client import get_redis_client
from app.redis.exceptions import RateLimitExceededError
from app.redis.idempotency import IdempotencyStore
from app.redis.keys import InterviewRedisKeys
from app.redis.rate_limit import AnswerRateLimiter, FixedWindowRateLimiter
from app.redis.runtime_state_service import RuntimeStateService
from app.repositories.dashboard_repository import DashboardRepository
from app.repositories.interview_repository import InterviewRepository
from app.resume.service import ResumeService
from app.services.dashboard_service import DashboardService
from app.services.interview_service import InterviewNotFoundError, InterviewService
from app.services.result_service import ResultService
from app.voice.base import SttAuthProvider, TTSProvider
from app.voice.factory import get_stt_auth_provider as _get_configured_stt_auth_provider
from app.voice.factory import get_tts_provider as _get_configured_tts_provider
from app.voice.service import SttAuthService, TTSService
from app.workflows.interview.graph import InterviewWorkflow

logger = logging.getLogger(__name__)


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db, settings.session_lifetime_seconds)


def get_google_verifier() -> GoogleIdentityVerifier:
    # Thin wrapper so tests can override just this dependency with a fake.
    return get_configured_google_verifier()


def get_current_user(request: Request, auth_service: AuthService = Depends(get_auth_service)) -> User:
    """The single authentication dependency: session cookie -> hashed-token
    lookup -> active (non-expired, non-revoked) session -> user. Raises
    AuthenticationRequiredError (HTTP 401) otherwise. User identity comes
    only from this server-side session, never from request data."""
    return auth_service.get_user_for_token(request.cookies.get(settings.session_cookie_name))


def get_interview_repository(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> InterviewRepository:
    # Owner-scoped: every session lookup made through this repository is
    # filtered by `user_id = current_user.id`, so another user's interview is
    # indistinguishable from a nonexistent one (404), and new interviews are
    # stamped with the current user.
    return InterviewRepository(db, owner_id=current_user.id)


def get_dashboard_service(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> DashboardService:
    # Scoped to the authenticated user only — the id never comes from the request.
    return DashboardService(DashboardRepository(db, current_user.id))


def require_owned_interview(
    session_id: uuid.UUID, repository: InterviewRepository = Depends(get_interview_repository)
) -> uuid.UUID:
    """Route-level guard, resolved before any handler body: rejects (404)
    interviews the current user does not own BEFORE Redis locks, idempotency
    lookups or rate limiting are touched for that session id."""
    if repository.get_session(session_id) is None:
        raise InterviewNotFoundError(f"Interview session {session_id} was not found.")
    return session_id


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


def get_interview_planner(
    llm_provider: LLMProvider = Depends(get_llm_provider),
) -> InterviewPlanner:
    return LLMInterviewPlanner(llm_provider)


def get_claim_investigator(
    llm_provider: LLMProvider = Depends(get_llm_provider),
) -> ClaimInvestigator:
    return LLMClaimInvestigator(llm_provider)


def get_interview_service(
    repository: InterviewRepository = Depends(get_interview_repository),
    workflow: InterviewWorkflow = Depends(get_interview_workflow),
    planner: InterviewPlanner = Depends(get_interview_planner),
    investigator: ClaimInvestigator = Depends(get_claim_investigator),
) -> InterviewService:
    return InterviewService(repository, workflow, planner=planner, investigator=investigator)


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


def get_resume_service(
    repository: InterviewRepository = Depends(get_interview_repository),
    llm_provider: LLMProvider = Depends(get_llm_provider),
) -> ResumeService:
    # A sibling of get_interview_service/get_evaluation_service, sharing
    # the same request-scoped repository — needs the LLM provider for
    # structured resume parsing (app.resume.parser.LLMResumeParser) but no
    # InterviewWorkflow/knowledge service, same reasoning as
    # get_evaluation_service above.
    return ResumeService(repository, llm_provider, settings.resume_max_file_size_bytes)


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


async def enforce_resume_upload_rate_limit(
    request: Request, redis_client: Redis = Depends(get_redis_client)
) -> None:
    await _enforce_client_rate_limit(
        request,
        redis_client,
        namespace="resume:upload",
        limit=settings.resume_upload_rate_limit,
        window_seconds=settings.resume_upload_rate_window_seconds,
        message="Too many resume upload requests. Please try again later.",
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
