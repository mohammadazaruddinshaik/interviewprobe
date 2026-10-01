import logging
import uuid

from fastapi import APIRouter, Depends, File, Header, Response, UploadFile, status
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from app.api.deps import (
    enforce_interview_creation_rate_limit,
    enforce_interview_start_rate_limit,
    enforce_resume_upload_rate_limit,
    get_answer_rate_limiter,
    get_evaluation_service,
    get_idempotency_store,
    get_interview_service,
    get_result_service,
    get_resume_service,
    get_runtime_state_service,
    require_owned_interview,
)
from app.core.config import settings
from app.domain.enums import InterviewStatus
from app.evaluation.service import EvaluationService
from app.redis.client import get_redis_client
from app.redis.exceptions import (
    IdempotencyKeyReusedError,
    InterviewLockBusyError,
    RateLimitExceededError,
    RedisProtectionUnavailableError,
)
from app.redis.idempotency import (
    MAX_IDEMPOTENCY_KEY_LENGTH,
    MIN_IDEMPOTENCY_KEY_LENGTH,
    IdempotencyRecord,
    IdempotencyStore,
    fingerprint_request,
)
from app.redis.lock import InterviewLock
from app.redis.rate_limit import AnswerRateLimiter
from app.redis.runtime_state_service import RuntimeStateService, RuntimeStateUnavailableError
from app.schemas.common import DataResponse
from app.schemas.interview import (
    CompleteInterviewResponse,
    CreateInterviewRequest,
    CreateInterviewResponse,
    InterviewCatalogResponse,
    EvaluationResponse,
    InterviewResponse,
    InterviewResultResponse,
    InterviewTopicResponse,
    QuestionResponse,
    ResultInterviewResponse,
    ResultQuestionResponse,
    ResumeResponse,
    StartInterviewResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
)
from app.resume.service import ResumeService
from app.services.interview_catalog import build_interview_catalog
from app.services.interview_service import InterviewService
from app.services.result_service import ResultService

logger = logging.getLogger(__name__)

router = APIRouter()

# Resolved before each handler body: 404s interviews the current user does not own
# (and 401s unauthenticated callers) before locks/idempotency/rate limits are touched.
_OWNED = [Depends(require_owned_interview)]


def _to_question_response(question, lead_in: str | None = None) -> QuestionResponse:
    return QuestionResponse(
        id=question.id,
        sequence=question.sequence_number,
        text=question.question_text,
        topic=question.topic,
        difficulty=question.difficulty,
        type=question.question_type,
        lead_in=lead_in,
    )


def _error_response(status_code: int, code: str, message: str, headers: dict | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code, content={"error": {"code": code, "message": message}}, headers=headers
    )


async def _mirror_runtime_state(
    runtime_state_service: RuntimeStateService, session, last_action: str | None
) -> None:
    """Write the post-transaction runtime state to Redis.

    PostgreSQL has already committed by the time this runs. A Redis
    failure here must not fail the request or roll back anything — it is
    logged explicitly (never silently ignored) and the durable interview
    state in PostgreSQL remains correct and reconstructible later via
    `RuntimeStateService.get_or_rebuild_state`.
    """
    try:
        state = runtime_state_service.build_state(session=session, last_action=last_action)
        await runtime_state_service.set_state(state)
    except RuntimeStateUnavailableError:
        logger.warning(
            "Failed to mirror runtime state to Redis for session %s; "
            "PostgreSQL state is unaffected and remains authoritative.",
            session.id,
        )


@router.post("", response_model=DataResponse[CreateInterviewResponse], status_code=status.HTTP_201_CREATED)
def create_interview(
    payload: CreateInterviewRequest,
    service: InterviewService = Depends(get_interview_service),
    _rate_limit: None = Depends(enforce_interview_creation_rate_limit),
) -> DataResponse[CreateInterviewResponse]:
    session = service.create_interview(role=payload.role)
    # A new interview has no topics (the planner picks them at start) and its session difficulty /
    # question_limit are internal placeholders, so none of them is reported.
    response = CreateInterviewResponse(
        id=session.id,
        role=session.role,
        difficulty=None,
        topics=[],
        question_limit=None,
        status=session.status,
    )
    return DataResponse(data=response)


@router.get("/catalog", response_model=DataResponse[InterviewCatalogResponse])
def get_interview_catalog(response: Response) -> DataResponse[InterviewCatalogResponse]:
    """Public, read-only: the supported roles. Static application configuration (no user data), so no
    session is required. Topics, difficulty and length are planner decisions and are not exposed.
    Declared before the `/{session_id}` routes so "catalog" is never parsed as an interview id."""
    response.headers["Cache-Control"] = "public, max-age=3600"
    return DataResponse(data=build_interview_catalog())


@router.post("/{session_id}/start", response_model=DataResponse[StartInterviewResponse], dependencies=_OWNED)
async def start_interview(
    session_id: uuid.UUID,
    service: InterviewService = Depends(get_interview_service),
    runtime_state_service: RuntimeStateService = Depends(get_runtime_state_service),
    redis_client: Redis = Depends(get_redis_client),
    _rate_limit: None = Depends(enforce_interview_start_rate_limit),
):
    lock = InterviewLock(redis_client, session_id, settings.redis_interview_lock_ttl_seconds)
    try:
        acquired = await lock.acquire()
    except RedisProtectionUnavailableError:
        return _error_response(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "REDIS_UNAVAILABLE",
            "A required concurrency-safety service is temporarily unavailable. Please try again.",
        )
    if not acquired:
        raise InterviewLockBusyError("This interview is currently being updated. Please retry.")

    try:
        session, question, lead_in = await service.start_interview(session_id)

        await _mirror_runtime_state(runtime_state_service, session=session, last_action=None)

        response = StartInterviewResponse(
            session_id=session.id,
            status=session.status,
            question=_to_question_response(question, lead_in),
        )
        return DataResponse(data=response)
    finally:
        await _release_lock_quietly(lock)


@router.post("/{session_id}/answers", response_model=DataResponse[SubmitAnswerResponse], dependencies=_OWNED)
async def submit_answer(
    session_id: uuid.UUID,
    payload: SubmitAnswerRequest,
    service: InterviewService = Depends(get_interview_service),
    runtime_state_service: RuntimeStateService = Depends(get_runtime_state_service),
    rate_limiter: AnswerRateLimiter = Depends(get_answer_rate_limiter),
    idempotency_store: IdempotencyStore = Depends(get_idempotency_store),
    redis_client: Redis = Depends(get_redis_client),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    # --- Request-level validation (no Redis) ---------------------------
    if not idempotency_key:
        return _error_response(
            status.HTTP_400_BAD_REQUEST,
            "MISSING_IDEMPOTENCY_KEY",
            "The Idempotency-Key header is required.",
        )
    if not (MIN_IDEMPOTENCY_KEY_LENGTH <= len(idempotency_key) <= MAX_IDEMPOTENCY_KEY_LENGTH):
        return _error_response(
            status.HTTP_400_BAD_REQUEST,
            "INVALID_IDEMPOTENCY_KEY",
            f"Idempotency-Key must be {MIN_IDEMPOTENCY_KEY_LENGTH}-{MAX_IDEMPOTENCY_KEY_LENGTH} characters.",
        )

    fingerprint = fingerprint_request(
        {"question_id": str(payload.question_id), "answer": payload.answer}
    )

    # --- Idempotency check BEFORE rate limiting -------------------------
    # A retry of an already-completed request should not consume a rate-
    # limit slot — see Task 12 report for the full rationale. Only requests
    # that are genuinely new (no stored record yet) reach the rate limiter.
    try:
        existing = await idempotency_store.get(session_id, idempotency_key)
    except RedisProtectionUnavailableError:
        return _redis_unavailable_response()
    if existing is not None:
        return _replay_or_conflict(existing, fingerprint)

    # --- Rate limit only genuinely new attempts -------------------------
    try:
        allowed, retry_after = await rate_limiter.check_and_increment(session_id)
    except RedisProtectionUnavailableError:
        return _redis_unavailable_response()
    if not allowed:
        raise RateLimitExceededError(retry_after_seconds=retry_after)

    # --- Acquire the interview lock for the whole mutation sequence -----
    lock = InterviewLock(redis_client, session_id, settings.redis_interview_lock_ttl_seconds)
    try:
        acquired = await lock.acquire()
    except RedisProtectionUnavailableError:
        return _redis_unavailable_response()
    if not acquired:
        raise InterviewLockBusyError("This interview is currently being updated. Please retry.")

    try:
        # Re-check idempotency now that we hold the lock: a concurrent
        # request using the same key may have raced past the first check
        # above and already completed the mutation while we were waiting.
        # This double-check is what guarantees "one key -> at most one
        # mutation" under concurrency, not the first check alone.
        try:
            existing = await idempotency_store.get(session_id, idempotency_key)
        except RedisProtectionUnavailableError:
            return _redis_unavailable_response()
        if existing is not None:
            return _replay_or_conflict(existing, fingerprint)

        session, next_question, lead_in = await service.submit_answer(
            session_id, payload.question_id, payload.answer, idempotency_key=idempotency_key
        )

        if next_question is not None:
            await _mirror_runtime_state(
                runtime_state_service, session=session, last_action=next_question.question_type.value
            )
            response = SubmitAnswerResponse(
                session_id=session.id,
                status=session.status,
                action=next_question.question_type.value,
                question=_to_question_response(next_question, lead_in),
            )
        else:
            await _mirror_runtime_state(runtime_state_service, session=session, last_action="END")
            response = SubmitAnswerResponse(
                session_id=session.id,
                status=session.status,
                action="END",
                question=None,
                evaluation_status="NOT_STARTED",
            )

        response_body = {"data": response.model_dump(mode="json")}

        # Store the idempotent record on a best-effort basis: the mutation
        # already succeeded in PostgreSQL, so a failure here must not fail
        # the request (nothing left to protect against) — only logged. A
        # subsequent retry with the same key would simply re-run this
        # (now state-mismatched) request and fail with a normal domain
        # error, which is an acceptable degraded mode without Redis.
        try:
            await idempotency_store.set(
                session_id,
                idempotency_key,
                IdempotencyRecord(fingerprint=fingerprint, status_code=200, body=response_body),
            )
        except RedisProtectionUnavailableError:
            logger.warning(
                "Failed to store idempotency record for session %s, key %s; "
                "the answer was still recorded in PostgreSQL.",
                session_id,
                idempotency_key,
            )

        return DataResponse(data=response)
    finally:
        await _release_lock_quietly(lock)


def _redis_unavailable_response() -> JSONResponse:
    return _error_response(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "REDIS_UNAVAILABLE",
        "A required concurrency-safety service is temporarily unavailable. Please try again.",
    )


def _replay_or_conflict(existing: IdempotencyRecord, fingerprint: str) -> JSONResponse:
    if existing.fingerprint != fingerprint:
        raise IdempotencyKeyReusedError(
            "The idempotency key was already used with a different request."
        )
    return JSONResponse(status_code=existing.status_code, content=existing.body)


async def _release_lock_quietly(lock: InterviewLock) -> None:
    """Release the lock without letting a Redis failure here mask the
    request's real response or in-flight exception — it is logged, and if
    genuinely unreleased the lock still self-expires via its TTL."""
    try:
        await lock.release()
    except RedisProtectionUnavailableError:
        logger.warning("Failed to release interview lock; it will expire via TTL.")


def _planner_owned(session, value):
    """difficulty / question_limit are planner decisions; a CREATED session only holds internal placeholders
    (see InterviewService.create_interview), which must not be presented as real values."""
    return None if session.status is InterviewStatus.CREATED else value


@router.get("/{session_id}", response_model=DataResponse[InterviewResponse], dependencies=_OWNED)
def get_interview(
    session_id: uuid.UUID,
    service: InterviewService = Depends(get_interview_service),
) -> DataResponse[InterviewResponse]:
    session, current_topic, questions_answered, topics, current_question = service.get_interview_state(
        session_id
    )
    response = InterviewResponse(
        session_id=session.id,
        role=session.role,
        difficulty=_planner_owned(session, session.difficulty),
        status=session.status,
        question_limit=_planner_owned(session, session.question_limit),
        current_topic=current_topic,
        current_question_number=session.current_question_number,
        questions_answered=questions_answered,
        topics=[
            InterviewTopicResponse(
                topic=topic.topic, sequence_number=topic.sequence_number, status=topic.status
            )
            for topic in topics
        ],
        current_question=_to_question_response(current_question) if current_question is not None else None,
    )
    return DataResponse(data=response)


def _to_resume_response(resume) -> ResumeResponse:
    return ResumeResponse(
        session_id=resume.session_id,
        original_filename=resume.original_filename,
        content_type=resume.content_type,
        file_size=resume.file_size,
        status=resume.extraction_status,
        extraction_error=resume.extraction_error,
    )


@router.post("/{session_id}/resume", response_model=DataResponse[ResumeResponse], dependencies=_OWNED)
async def upload_resume(
    session_id: uuid.UUID,
    resume: UploadFile = File(...),
    service: ResumeService = Depends(get_resume_service),
    _rate_limit: None = Depends(enforce_resume_upload_rate_limit),
) -> DataResponse[ResumeResponse]:
    # Resume upload is entirely optional and never blocks the interview
    # (Phase 2 brief) — this endpoint's own failure modes reflect that:
    # a bad request (wrong file type/size/session state) is a normal 4xx,
    # raised before any row is created (see ResumeService._validate_request
    # via app.main's registered exception handlers); a bad FILE (corrupted,
    # unreadable, or an LLM hiccup while structuring it) is never a 5xx —
    # ResumeService always persists that as a FAILED row and returns it
    # here with a normal 200, for the Setup page's existing "couldn't read
    # this resume" UI to render.
    data = await resume.read()
    saved = await service.upload_resume(
        session_id=session_id,
        filename=resume.filename or "resume",
        content_type=resume.content_type or "",
        data=data,
    )
    return DataResponse(data=_to_resume_response(saved))


@router.post("/{session_id}/complete", response_model=DataResponse[CompleteInterviewResponse], dependencies=_OWNED)
async def complete_interview(
    session_id: uuid.UUID,
    service: InterviewService = Depends(get_interview_service),
    runtime_state_service: RuntimeStateService = Depends(get_runtime_state_service),
    redis_client: Redis = Depends(get_redis_client),
):
    lock = InterviewLock(redis_client, session_id, settings.redis_interview_lock_ttl_seconds)
    try:
        acquired = await lock.acquire()
    except RedisProtectionUnavailableError:
        return _redis_unavailable_response()
    if not acquired:
        raise InterviewLockBusyError("This interview is currently being updated. Please retry.")

    try:
        session = service.complete_interview(session_id)

        await _mirror_runtime_state(runtime_state_service, session=session, last_action="COMPLETED")

        response = CompleteInterviewResponse(
            session_id=session.id,
            status=session.status,
            evaluation_status="NOT_STARTED",
        )
        return DataResponse(data=response)
    finally:
        await _release_lock_quietly(lock)


@router.get("/{session_id}/evaluation", response_model=DataResponse[EvaluationResponse], dependencies=_OWNED)
async def get_interview_evaluation(
    session_id: uuid.UUID,
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> DataResponse[EvaluationResponse]:
    # Idempotent: a persisted evaluation is returned as-is; a completed
    # interview without one yet has it generated, validated, and
    # persisted here. Incomplete interviews raise InvalidInterviewStateError
    # (409) — see EvaluationService.get_or_create_evaluation.
    evaluation = await evaluation_service.get_or_create_evaluation(session_id)
    response = EvaluationResponse(
        session_id=evaluation.session_id,
        technical_knowledge_score=float(evaluation.technical_knowledge_score),
        reasoning_score=float(evaluation.reasoning_score),
        depth_score=float(evaluation.depth_score),
        communication_score=float(evaluation.communication_score),
        overall_score=float(evaluation.overall_score),
        strengths=evaluation.strengths,
        weaknesses=evaluation.weaknesses,
        evidence=evaluation.evidence,
    )
    return DataResponse(data=response)


@router.get("/{session_id}/result", response_model=DataResponse[InterviewResultResponse], dependencies=_OWNED)
async def get_interview_result(
    session_id: uuid.UUID,
    result_service: ResultService = Depends(get_result_service),
) -> DataResponse[InterviewResultResponse]:
    # Deterministic once an evaluation exists: ResultService only reads
    # persisted state plus EvaluationService's existing idempotent
    # generate-or-load behavior — it never generates questions, reruns
    # adaptive decisions, retrieves RAG context, or mutates interview
    # status/topics. See ResultService.get_result / EvaluationService
    # .get_or_create_evaluation for the (409 for CREATED/IN_PROGRESS/FAILED,
    # 404 for an unknown session) validation this reuses rather than
    # duplicates.
    result = await result_service.get_result(session_id)
    response = InterviewResultResponse(
        interview=ResultInterviewResponse(
            session_id=result.session.id,
            role=result.session.role,
            difficulty=result.session.difficulty,
            status=result.session.status,
            question_limit=result.session.question_limit,
            started_at=result.session.started_at,
            completed_at=result.session.completed_at,
            created_at=result.session.created_at,
        ),
        topics=[
            InterviewTopicResponse(topic=t.topic, sequence_number=t.sequence_number, status=t.status)
            for t in result.topics
        ],
        questions=[
            ResultQuestionResponse(
                id=qwa.question.id,
                sequence=qwa.question.sequence_number,
                text=qwa.question.question_text,
                topic=qwa.question.topic,
                difficulty=qwa.question.difficulty,
                type=qwa.question.question_type,
                candidate_answer=qwa.candidate_answer,
            )
            for qwa in result.questions
        ],
        evaluation=EvaluationResponse(
            session_id=result.evaluation.session_id,
            technical_knowledge_score=float(result.evaluation.technical_knowledge_score),
            reasoning_score=float(result.evaluation.reasoning_score),
            depth_score=float(result.evaluation.depth_score),
            communication_score=float(result.evaluation.communication_score),
            overall_score=float(result.evaluation.overall_score),
            strengths=result.evaluation.strengths,
            weaknesses=result.evaluation.weaknesses,
            evidence=result.evaluation.evidence,
        ),
    )
    return DataResponse(data=response)
