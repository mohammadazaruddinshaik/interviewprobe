import logging
import time
import uuid

from redis.asyncio import Redis
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.enums import InterviewStatus, MessageRole
from app.evaluation.models import EvaluationContext, EvaluationQuestionAnswer, EvaluationResult
from app.evaluation.prompts import build_evaluation_messages
from app.evaluation.validator import validate_and_normalize
from app.llm.base import LLMProvider
from app.models.evaluation import Evaluation
from app.models.interview_session import InterviewSession
from app.redis.exceptions import EvaluationLockBusyError, RedisProtectionUnavailableError
from app.redis.lock import EvaluationLock
from app.repositories.interview_repository import InterviewRepository
from app.services.interview_service import InterviewNotFoundError, InvalidInterviewStateError

logger = logging.getLogger(__name__)


class EvaluationService:
    """Generates and persists the structured evaluation for a completed
    interview.

    A sibling to `InterviewService`, not a subordinate of it — both share
    the request-scoped `InterviewRepository` (and therefore the same DB
    session), but this service owns its own transaction boundary and
    never mutates any interview-lifecycle field (status, current
    question, topics, Redis runtime state, ...). Its only durable
    mutation is creating the `evaluations` row.

    Deliberately has no LangGraph, no RAG: a one-shot structured LLM call
    over a finished transcript needs none of the interview workflow's
    adaptive orchestration. It does have one Redis dependency (Task 53):
    `EvaluationLock`, a distributed lock serializing evaluation
    *generation* (the expensive LLM call + persistence) per session, so
    N concurrent first-time requests for the same session pay for at
    most one LLM call rather than one each. The DB's unique constraint
    on `evaluations.session_id` (Task 52) remains the final authority on
    *persistence* uniqueness either way — the lock exists purely to avoid
    paying for redundant LLM calls, not to replace that constraint.
    """

    def __init__(
        self,
        repository: InterviewRepository,
        llm_provider: LLMProvider,
        redis_client: Redis,
        lock_ttl_seconds: int,
    ):
        self.repository = repository
        self.llm_provider = llm_provider
        self._redis_client = redis_client
        self._lock_ttl_seconds = lock_ttl_seconds

    @property
    def _db(self) -> Session:
        return self.repository.session

    async def get_or_create_evaluation(self, session_id: uuid.UUID) -> Evaluation:
        """Idempotent: a persisted evaluation is returned as-is, without
        invoking the LLM again or touching Redis at all. Only a genuinely
        new evaluation acquires the evaluation-generation lock and reaches
        the LLM call.

        Ordering (Task 53): check DB (no lock) -> if missing, acquire the
        per-session evaluation lock -> check DB again (a concurrent
        request may have finished generating while this one waited on the
        lock) -> only then call the LLM -> validate -> persist -> release.
        `EvaluationLock.acquire()` is non-blocking (a single atomic
        SET NX EX): a Redis outage raises `RedisProtectionUnavailableError`
        before any LLM call is made (fails closed — handled by the same
        global 503 handler every other Redis-backed guard in this app
        uses), and a lock already held by another request raises
        `EvaluationLockBusyError` (mapped to 409) rather than waiting or
        polling, exactly like `InterviewLock`/`InterviewLockBusyError`.
        """
        session = self._get_session_or_raise(session_id)

        existing = self.repository.get_evaluation(session_id)
        if existing is not None:
            return existing

        if session.status != InterviewStatus.COMPLETED:
            raise InvalidInterviewStateError(
                f"Interview session {session_id} must be COMPLETED to evaluate "
                f"(current status: {session.status})."
            )

        lock = EvaluationLock(self._redis_client, session_id, self._lock_ttl_seconds)
        acquired = await lock.acquire()
        if not acquired:
            raise EvaluationLockBusyError(
                f"Evaluation for interview session {session_id} is already being generated. "
                "Please retry shortly."
            )

        try:
            # Re-check now that we hold the lock: a concurrent request may
            # have already generated and persisted the evaluation while
            # this one was waiting to acquire — return it rather than
            # paying for a second LLM call.
            existing = self.repository.get_evaluation(session_id)
            if existing is not None:
                return existing

            # ---- Build evidence and call the LLM OUTSIDE any write transaction ----
            started = time.monotonic()
            context = self._build_context(session_id, session)
            response = await self.llm_provider.generate_structured(
                build_evaluation_messages(context), EvaluationResult
            )
            valid_question_ids = {turn.question_id for turn in context.turns}
            validated = validate_and_normalize(response.data, valid_question_ids)

            # ---- Short durable-mutation transaction ----
            try:
                # Defense in depth, not the primary guarantee: the lock
                # above is what actually prevents a second LLM call, but a
                # stale/expired lock (TTL elapsed mid-generation) could
                # still let two writers reach this point, so the recheck
                # and IntegrityError handling stay as the final backstop
                # on top of Task 52's DB-level unique constraint.
                existing = self.repository.get_evaluation(session_id)
                if existing is not None:
                    return existing

                evaluation = Evaluation(
                    session_id=session_id,
                    technical_knowledge_score=validated.technical_knowledge_score,
                    reasoning_score=validated.reasoning_score,
                    depth_score=validated.depth_score,
                    communication_score=validated.communication_score,
                    overall_score=validated.overall_score,
                    strengths=validated.strengths,
                    weaknesses=validated.weaknesses,
                    evidence=validated.evidence,
                )
                self.repository.create_evaluation(evaluation)
                self._db.commit()
            except IntegrityError:
                # Lost the race to a concurrent evaluator — `evaluations
                # .session_id` is uniquely constrained, so this can only mean
                # someone else's evaluation won. Recover by loading it rather
                # than failing the request.
                self._db.rollback()
                evaluation = self.repository.get_evaluation(session_id)
                if evaluation is None:
                    raise
            except Exception:
                self._db.rollback()
                raise

            logger.info(
                "evaluation_generated session_id=%s duration_ms=%d",
                session_id,
                int((time.monotonic() - started) * 1000),
            )
            return evaluation
        finally:
            # Quiet on Redis failure, matching InterviewLock's release
            # sites at the API layer (see `_release_lock_quietly` in
            # app.api.routes.interviews): a failure here must not mask
            # whatever the `try` block above just did (a successful
            # generation, or a real LLM/validation failure already being
            # raised) — the lock still self-expires via its TTL either
            # way, so this is logged, not re-raised.
            try:
                await lock.release()
            except RedisProtectionUnavailableError:
                logger.warning(
                    "Failed to release evaluation lock for session %s; it will expire via TTL.",
                    session_id,
                )

    def _get_session_or_raise(self, session_id: uuid.UUID) -> InterviewSession:
        session = self.repository.get_session(session_id)
        if session is None:
            raise InterviewNotFoundError(f"Interview session {session_id} was not found.")
        return session

    def _build_context(self, session_id: uuid.UUID, session: InterviewSession) -> EvaluationContext:
        questions = self.repository.get_questions(session_id)
        messages = self.repository.get_messages(session_id)
        topics = self.repository.get_topics(session_id)

        candidate_answers_by_question_id = {
            message.question_id: message.content
            for message in messages
            if message.role == MessageRole.CANDIDATE and message.question_id is not None
        }
        turns = [
            EvaluationQuestionAnswer(
                question_id=question.id,
                sequence=question.sequence_number,
                topic=question.topic,
                difficulty=question.difficulty,
                question_type=question.question_type,
                question_text=question.question_text,
                candidate_answer=candidate_answers_by_question_id.get(question.id),
            )
            for question in questions
        ]
        return EvaluationContext(
            session_id=session_id,
            role=session.role,
            difficulty=session.difficulty,
            topics=[topic_entry.topic for topic_entry in topics],
            question_limit=session.question_limit,
            turns=turns,
        )
