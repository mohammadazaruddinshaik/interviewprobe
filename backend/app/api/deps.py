import logging

from fastapi import Depends
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
from app.redis.idempotency import IdempotencyStore
from app.redis.rate_limit import AnswerRateLimiter
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
) -> EvaluationService:
    # A sibling of `get_interview_service`, not built on top of it: it
    # shares the same request-scoped repository/DB session, but needs no
    # `InterviewWorkflow`/knowledge service — evaluation is a single
    # structured LLM call over a finished transcript, not an adaptive
    # graph turn.
    return EvaluationService(repository, llm_provider)


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
