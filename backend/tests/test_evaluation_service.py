"""Task 21 — `EvaluationService`: state validation, idempotency,
concurrency-safe persistence, transaction boundaries, and LLM-failure
propagation. Real SQLite-backed `InterviewRepository` (same pattern as
tests/test_interview_service.py), `FakeLLMProvider` — no real Postgres/LLM.
"""

import asyncio
import uuid

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.domain.enums import Difficulty, InterviewStatus, InterviewTopic, QuestionType, Role
from app.evaluation.models import EvaluationResult, EvidenceItem
from app.evaluation.service import EvaluationService
from app.llm.base import LLMProvider
from app.llm.exceptions import (
    LLMConfigurationError,
    LLMInvalidResponseError,
    LLMProviderUnavailableError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from app.llm.models import StructuredLLMResponse
from app.models.evaluation import Evaluation
from app.redis.exceptions import EvaluationLockBusyError, RedisProtectionUnavailableError
from app.redis.keys import EvaluationRedisKeys
from app.redis.lock import EvaluationLock
from app.repositories.interview_repository import InterviewRepository
from app.services.interview_service import InterviewNotFoundError, InterviewService, InvalidInterviewStateError
from app.workflows.interview.graph import InterviewWorkflow
from app.workflows.interview.models import AnswerAnalysis, GeneratedQuestion, NextAction
from tests.fakes import FailingAsyncRedis, FakeAsyncRedis, FakeLLMProvider

# Task 53: EvaluationService now requires a Redis client/lock TTL for its
# evaluation-generation lock. Every test in this file that isn't itself
# testing lock contention gets its own fresh FakeAsyncRedis (never shared
# across sessions) via this helper, so none of them need to care about
# the new constructor arguments individually. Tests that DO exercise the
# lock (see the "Concurrency" section below) construct `EvaluationLock`/
# pass an explicit `redis_client` directly instead of using this helper.
_TEST_LOCK_TTL_SECONDS = 30


def make_evaluation_service(repository, llm_provider, redis_client=None):
    return EvaluationService(
        repository, llm_provider, redis_client or FakeAsyncRedis(), _TEST_LOCK_TTL_SECONDS
    )


class _BlockingLLMProvider(LLMProvider):
    """An `LLMProvider` whose `generate_structured` pauses mid-call until
    the test releases it, for the one concurrency guarantee a purely
    sequential test cannot prove: that a second, genuinely concurrent
    request does not independently reach the LLM while the first is still
    inside its call. `started` lets a test `await` until the first
    request is provably inside `generate_structured` before attempting
    the second request; `release` is what the test sets once it has
    observed whatever it needed to (see tests/test_redis_lock.py's
    FakeAsyncRedis docstring for the same "prove real interleaving, don't
    assume it" philosophy applied to Redis instead of the LLM).
    """

    def __init__(self, result: EvaluationResult):
        super().__init__(provider_name="fake-blocking", model="fake-model", timeout_seconds=5, max_retries=0)
        self._result = result
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.calls = 0

    async def generate_text(self, messages):
        raise NotImplementedError("_BlockingLLMProvider.generate_text is not used by these tests")

    async def generate_structured(self, messages, output_schema):
        self.calls += 1
        self.started.set()
        await self.release.wait()
        return StructuredLLMResponse(data=self._result, model=self.model)


# Same sqlite-compatibility strategy as tests/test_interview_service.py.


@compiles(UUID, "sqlite")
def _compile_uuid_sqlite(element, compiler, **kw):
    return "CHAR(32)"


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(element, compiler, **kw):
    return "JSON"


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def repository(db_session: Session) -> InterviewRepository:
    return InterviewRepository(db_session)


def default_evaluation_result(**overrides) -> EvaluationResult:
    defaults = dict(
        technical_knowledge_score=7.0,
        reasoning_score=6.0,
        depth_score=5.0,
        communication_score=8.0,
        overall_score=1.0,  # deliberately wrong — backend must recompute
        strengths=["Explained retrieval clearly."],
        weaknesses=["Limited depth on reranking."],
        evidence=[],
    )
    defaults.update(overrides)
    return EvaluationResult(**defaults)


def interview_fake_llm() -> FakeLLMProvider:
    """Drives `InterviewService` deterministically to COMPLETED (always
    FOLLOW_UP until the question limit is hit)."""
    return FakeLLMProvider(
        structured_responses={
            "GeneratedQuestion": GeneratedQuestion(
                question="Tell me more.",
                topic=InterviewTopic.DATABASES,
                difficulty=Difficulty.MEDIUM,
                question_type=QuestionType.FOLLOW_UP,
            ),
            "AnswerAnalysis": AnswerAnalysis(
                understanding="BASIC", correctness=0.5, depth=0.4, concepts_demonstrated=[],
                concepts_missing=[], reasoning_quality="MODERATE", needs_follow_up=True,
            ),
            "NextAction": NextAction(
                action="FOLLOW_UP", topic=InterviewTopic.DATABASES, difficulty=Difficulty.MEDIUM, rationale="x"
            ),
        }
    )


async def create_completed_interview(repository: InterviewRepository, question_limit: int = 3) -> uuid.UUID:
    """Drives a real interview through InterviewService to COMPLETED,
    sharing `repository` (and therefore the DB session) with the
    EvaluationService under test — exactly like the API layer shares one
    repository across both services per request."""
    workflow = InterviewWorkflow(repository=repository, llm_provider=interview_fake_llm())
    interview_service = InterviewService(repository, workflow)

    session = interview_service.create_interview(
        role=Role.BACKEND_DEVELOPER, difficulty=Difficulty.MEDIUM, question_limit=question_limit,
        topics=[InterviewTopic.DATABASES],
    )
    _, question = await interview_service.start_interview(session.id)
    for i in range(question_limit):
        _, next_question = await interview_service.submit_answer(session.id, question.id, f"answer {i}")
        if next_question is not None:
            question = next_question
    return session.id


# ---------------------------------------------------------------------------
# State validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_created_interview_is_rejected(repository: InterviewRepository):
    workflow = InterviewWorkflow(repository=repository, llm_provider=FakeLLMProvider())
    interview_service = InterviewService(repository, workflow)
    session = interview_service.create_interview(
        role=Role.BACKEND_DEVELOPER, difficulty=Difficulty.MEDIUM, question_limit=3,
        topics=[InterviewTopic.DATABASES],
    )
    evaluation_service = make_evaluation_service(repository, FakeLLMProvider())

    with pytest.raises(InvalidInterviewStateError):
        await evaluation_service.get_or_create_evaluation(session.id)


@pytest.mark.asyncio
async def test_in_progress_interview_is_rejected(repository: InterviewRepository):
    workflow = InterviewWorkflow(repository=repository, llm_provider=interview_fake_llm())
    interview_service = InterviewService(repository, workflow)
    session = interview_service.create_interview(
        role=Role.BACKEND_DEVELOPER, difficulty=Difficulty.MEDIUM, question_limit=3,
        topics=[InterviewTopic.DATABASES],
    )
    await interview_service.start_interview(session.id)
    evaluation_service = make_evaluation_service(repository, FakeLLMProvider())

    with pytest.raises(InvalidInterviewStateError):
        await evaluation_service.get_or_create_evaluation(session.id)


@pytest.mark.asyncio
async def test_failed_interview_is_rejected(repository: InterviewRepository):
    workflow = InterviewWorkflow(repository=repository, llm_provider=interview_fake_llm())
    interview_service = InterviewService(repository, workflow)
    session = interview_service.create_interview(
        role=Role.BACKEND_DEVELOPER, difficulty=Difficulty.MEDIUM, question_limit=3,
        topics=[InterviewTopic.DATABASES],
    )
    # No lifecycle method sets FAILED — write it directly, matching how a
    # future failure-handling path would (out of this task's scope).
    interview_service.repository.update_session(session, status=InterviewStatus.FAILED)
    repository.session.commit()
    evaluation_service = make_evaluation_service(repository, FakeLLMProvider())

    with pytest.raises(InvalidInterviewStateError):
        await evaluation_service.get_or_create_evaluation(session.id)


@pytest.mark.asyncio
async def test_nonexistent_session_raises_not_found(repository: InterviewRepository):
    evaluation_service = make_evaluation_service(repository, FakeLLMProvider())

    with pytest.raises(InterviewNotFoundError):
        await evaluation_service.get_or_create_evaluation(uuid.uuid4())


@pytest.mark.asyncio
async def test_completed_interview_is_accepted_and_persists_all_four_scores(repository: InterviewRepository):
    session_id = await create_completed_interview(repository)
    evaluation_service = make_evaluation_service(repository, FakeLLMProvider(structured_responses={"EvaluationResult": default_evaluation_result()}))

    evaluation = await evaluation_service.get_or_create_evaluation(session_id)

    assert evaluation.session_id == session_id
    assert float(evaluation.technical_knowledge_score) == 7.0
    assert float(evaluation.reasoning_score) == 6.0
    assert float(evaluation.depth_score) == 5.0
    assert float(evaluation.communication_score) == 8.0
    assert evaluation.strengths == ["Explained retrieval clearly."]
    assert evaluation.weaknesses == ["Limited depth on reranking."]


@pytest.mark.asyncio
async def test_overall_score_is_backend_computed(repository: InterviewRepository):
    session_id = await create_completed_interview(repository)
    result = default_evaluation_result(
        technical_knowledge_score=4.0, reasoning_score=4.0, depth_score=4.0, communication_score=8.0,
        overall_score=0.0,
    )
    evaluation_service = make_evaluation_service(repository, FakeLLMProvider(structured_responses={"EvaluationResult": result}))

    evaluation = await evaluation_service.get_or_create_evaluation(session_id)

    assert float(evaluation.overall_score) == 5.0  # (4+4+4+8)/4, never the LLM's 0.0


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_second_call_returns_the_persisted_evaluation_without_calling_the_llm_again(
    repository: InterviewRepository,
):
    session_id = await create_completed_interview(repository)
    fake_llm = FakeLLMProvider(structured_responses={"EvaluationResult": default_evaluation_result()})
    evaluation_service = make_evaluation_service(repository, fake_llm)

    first = await evaluation_service.get_or_create_evaluation(session_id)
    assert len(fake_llm.calls) == 1

    second = await evaluation_service.get_or_create_evaluation(session_id)
    third = await evaluation_service.get_or_create_evaluation(session_id)

    assert second.id == first.id == third.id
    assert len(fake_llm.calls) == 1  # no additional LLM call


@pytest.mark.asyncio
async def test_at_most_one_evaluation_row_exists_per_session(repository: InterviewRepository, db_session: Session):
    session_id = await create_completed_interview(repository)
    evaluation_service = make_evaluation_service(
        repository, FakeLLMProvider(structured_responses={"EvaluationResult": default_evaluation_result()})
    )

    await evaluation_service.get_or_create_evaluation(session_id)
    await evaluation_service.get_or_create_evaluation(session_id)

    rows = db_session.execute(select(Evaluation).where(Evaluation.session_id == session_id)).scalars().all()
    assert len(rows) == 1


# ---------------------------------------------------------------------------
# Evaluation must not affect interview lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evaluation_does_not_mutate_the_interview_session(repository: InterviewRepository):
    session_id = await create_completed_interview(repository)
    session_before = repository.get_session(session_id)
    status_before, version_before, question_number_before = (
        session_before.status, session_before.version, session_before.current_question_number,
    )
    evaluation_service = make_evaluation_service(
        repository, FakeLLMProvider(structured_responses={"EvaluationResult": default_evaluation_result()})
    )

    await evaluation_service.get_or_create_evaluation(session_id)

    session_after = repository.get_session(session_id)
    assert session_after.status == status_before
    assert session_after.version == version_before
    assert session_after.current_question_number == question_number_before


@pytest.mark.asyncio
async def test_evaluation_does_not_mutate_topic_status(repository: InterviewRepository):
    session_id = await create_completed_interview(repository)
    topics_before = {t.topic: t.status for t in repository.get_topics(session_id)}
    evaluation_service = make_evaluation_service(
        repository, FakeLLMProvider(structured_responses={"EvaluationResult": default_evaluation_result()})
    )

    await evaluation_service.get_or_create_evaluation(session_id)

    topics_after = {t.topic: t.status for t in repository.get_topics(session_id)}
    assert topics_after == topics_before


# ---------------------------------------------------------------------------
# LLM failures propagate through the existing LLM exception hierarchy
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "error",
    [
        LLMTimeoutError("simulated timeout"),
        LLMRateLimitError("simulated rate limit"),
        LLMProviderUnavailableError("simulated outage"),
        LLMInvalidResponseError("simulated malformed response"),
        LLMConfigurationError("simulated misconfiguration"),
    ],
)
@pytest.mark.asyncio
async def test_llm_failure_propagates_and_persists_nothing(
    repository: InterviewRepository, db_session: Session, error: Exception
):
    session_id = await create_completed_interview(repository)
    evaluation_service = make_evaluation_service(repository, FakeLLMProvider(error=error))

    with pytest.raises(type(error)):
        await evaluation_service.get_or_create_evaluation(session_id)

    assert repository.get_evaluation(session_id) is None


@pytest.mark.asyncio
async def test_out_of_range_score_from_llm_persists_nothing(repository: InterviewRepository):
    session_id = await create_completed_interview(repository)
    bad_result = EvaluationResult.model_construct(
        technical_knowledge_score=99.0,
        reasoning_score=5.0,
        depth_score=5.0,
        communication_score=5.0,
        overall_score=5.0,
        strengths=[],
        weaknesses=[],
        evidence=[],
    )
    evaluation_service = make_evaluation_service(repository, FakeLLMProvider(structured_responses={"EvaluationResult": bad_result}))

    with pytest.raises(LLMInvalidResponseError):
        await evaluation_service.get_or_create_evaluation(session_id)

    assert repository.get_evaluation(session_id) is None


@pytest.mark.asyncio
async def test_evidence_referencing_an_unknown_question_id_still_succeeds(repository: InterviewRepository):
    session_id = await create_completed_interview(repository)
    result = default_evaluation_result(
        evidence=[EvidenceItem(question_id=str(uuid.uuid4()), claim="A claim.", evidence="Some evidence.")]
    )
    evaluation_service = make_evaluation_service(repository, FakeLLMProvider(structured_responses={"EvaluationResult": result}))

    evaluation = await evaluation_service.get_or_create_evaluation(session_id)

    assert len(evaluation.evidence) == 1
    assert "question_id" not in evaluation.evidence[0]


# ---------------------------------------------------------------------------
# Concurrency (Task 53) — the evaluation-generation lock
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_existing_evaluation_returns_without_acquiring_a_lock_or_generating(repository: InterviewRepository):
    session_id = await create_completed_interview(repository)
    fake_llm = FakeLLMProvider(structured_responses={"EvaluationResult": default_evaluation_result()})
    seeded = await make_evaluation_service(repository, fake_llm).get_or_create_evaluation(session_id)
    assert len(fake_llm.calls) == 1

    # A fresh service backed by Redis that raises on every operation: if
    # the already-persisted-evaluation fast path touched Redis at all
    # (acquiring the lock or otherwise), this would surface as
    # `RedisProtectionUnavailableError` instead of returning cleanly.
    service = make_evaluation_service(repository, fake_llm, FailingAsyncRedis())

    result = await service.get_or_create_evaluation(session_id)

    assert result.id == seeded.id
    assert len(fake_llm.calls) == 1  # no second LLM call either


@pytest.mark.asyncio
async def test_first_request_holds_the_evaluation_lock_while_generating(repository: InterviewRepository):
    session_id = await create_completed_interview(repository)
    blocking_llm = _BlockingLLMProvider(default_evaluation_result())
    redis_client = FakeAsyncRedis()
    service = make_evaluation_service(repository, blocking_llm, redis_client)

    task = asyncio.create_task(service.get_or_create_evaluation(session_id))
    await blocking_llm.started.wait()  # genuinely inside generate_structured now

    assert EvaluationRedisKeys.lock(session_id) in redis_client.store

    blocking_llm.release.set()
    await task


@pytest.mark.asyncio
async def test_genuinely_concurrent_request_does_not_independently_call_the_llm_while_locked(
    repository: InterviewRepository,
):
    """Genuine overlap, not a sequential stand-in: request A is proven to
    be inside the expensive LLM call (via `started`) before request B is
    even attempted, and B's outcome is asserted before A is allowed to
    finish (via `release`) — so B's busy error is provably concurrent
    with A's in-flight generation, not a result of A having already
    completed."""
    session_id = await create_completed_interview(repository)
    blocking_llm = _BlockingLLMProvider(default_evaluation_result())
    redis_client = FakeAsyncRedis()
    service = make_evaluation_service(repository, blocking_llm, redis_client)

    task_a = asyncio.create_task(service.get_or_create_evaluation(session_id))
    await blocking_llm.started.wait()  # A is now genuinely inside the LLM call

    with pytest.raises(EvaluationLockBusyError):
        await service.get_or_create_evaluation(session_id)  # request B

    assert blocking_llm.calls == 1  # B did not independently invoke the LLM

    blocking_llm.release.set()
    result_a = await task_a

    assert result_a.session_id == session_id
    assert blocking_llm.calls == 1


@pytest.mark.asyncio
async def test_n_concurrent_first_time_requests_result_in_exactly_one_llm_call(
    repository: InterviewRepository, db_session: Session
):
    async def get_or_create_with_retry(service: EvaluationService, session_id: uuid.UUID, max_attempts: int = 10):
        # Models a real caller: our lock is deliberately non-blocking (see
        # EvaluationLock/InterviewLock), so a caller that wants the
        # eventual result retries on a busy lock rather than waiting
        # inside the service. Bounded, not an infinite/long poll — and
        # `asyncio.sleep(0)` is a scheduling yield between attempts, not a
        # timing-based wait: the actual proof that only one LLM call
        # happens is the call-count assertion below, not this loop.
        for _ in range(max_attempts):
            try:
                return await service.get_or_create_evaluation(session_id)
            except EvaluationLockBusyError:
                await asyncio.sleep(0)
        raise AssertionError("evaluation still busy after max_attempts retries")

    session_id = await create_completed_interview(repository)
    fake_llm = FakeLLMProvider(structured_responses={"EvaluationResult": default_evaluation_result()})
    service = make_evaluation_service(repository, fake_llm)

    results = await asyncio.gather(
        *(get_or_create_with_retry(service, session_id) for _ in range(5))
    )

    assert len(fake_llm.calls) == 1  # the most important guarantee: exactly one LLM call
    assert len({evaluation.id for evaluation in results}) == 1  # every caller got the same evaluation

    rows = db_session.execute(select(Evaluation).where(Evaluation.session_id == session_id)).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_redis_unavailable_before_lock_prevents_the_llm_call(repository: InterviewRepository):
    session_id = await create_completed_interview(repository)
    fake_llm = FakeLLMProvider(structured_responses={"EvaluationResult": default_evaluation_result()})
    service = make_evaluation_service(repository, fake_llm, FailingAsyncRedis())

    with pytest.raises(RedisProtectionUnavailableError):
        await service.get_or_create_evaluation(session_id)

    assert len(fake_llm.calls) == 0  # fails closed before the expensive call
    assert repository.get_evaluation(session_id) is None


@pytest.mark.asyncio
async def test_lock_already_held_raises_busy_immediately_without_waiting(repository: InterviewRepository):
    session_id = await create_completed_interview(repository)
    redis_client = FakeAsyncRedis()
    other_holder = EvaluationLock(redis_client, session_id, _TEST_LOCK_TTL_SECONDS)
    assert await other_holder.acquire() is True  # simulates another request already holding it

    fake_llm = FakeLLMProvider(structured_responses={"EvaluationResult": default_evaluation_result()})
    service = make_evaluation_service(repository, fake_llm, redis_client)

    with pytest.raises(EvaluationLockBusyError):
        await service.get_or_create_evaluation(session_id)

    assert len(fake_llm.calls) == 0  # the busy path never reaches the LLM


@pytest.mark.asyncio
async def test_lock_is_released_after_successful_generation(repository: InterviewRepository):
    session_id = await create_completed_interview(repository)
    redis_client = FakeAsyncRedis()
    fake_llm = FakeLLMProvider(structured_responses={"EvaluationResult": default_evaluation_result()})
    service = make_evaluation_service(repository, fake_llm, redis_client)

    await service.get_or_create_evaluation(session_id)

    assert EvaluationRedisKeys.lock(session_id) not in redis_client.store


@pytest.mark.asyncio
async def test_lock_is_released_after_llm_failure(repository: InterviewRepository):
    session_id = await create_completed_interview(repository)
    redis_client = FakeAsyncRedis()
    service = make_evaluation_service(repository, FakeLLMProvider(error=LLMTimeoutError("simulated")), redis_client)

    with pytest.raises(LLMTimeoutError):
        await service.get_or_create_evaluation(session_id)

    assert EvaluationRedisKeys.lock(session_id) not in redis_client.store


@pytest.mark.asyncio
async def test_lock_is_released_after_validation_failure(repository: InterviewRepository):
    session_id = await create_completed_interview(repository)
    redis_client = FakeAsyncRedis()
    bad_result = EvaluationResult.model_construct(
        technical_knowledge_score=99.0,
        reasoning_score=5.0,
        depth_score=5.0,
        communication_score=5.0,
        overall_score=5.0,
        strengths=[],
        weaknesses=[],
        evidence=[],
    )
    service = make_evaluation_service(
        repository, FakeLLMProvider(structured_responses={"EvaluationResult": bad_result}), redis_client
    )

    with pytest.raises(LLMInvalidResponseError):
        await service.get_or_create_evaluation(session_id)

    assert EvaluationRedisKeys.lock(session_id) not in redis_client.store


@pytest.mark.asyncio
async def test_evaluation_persisted_between_first_check_and_lock_acquisition_is_returned_not_regenerated(
    repository: InterviewRepository, monkeypatch: pytest.MonkeyPatch
):
    """Proves the mandatory post-lock-acquisition DB re-check (ordering
    steps 3-5): simulates another request winning the race and persisting
    its own evaluation in the window between this request's first
    (unlocked) check and this request's own lock acquisition completing —
    a window that is otherwise hard to hit deterministically without
    patching `EvaluationLock.acquire` itself."""
    session_id = await create_completed_interview(repository)
    fake_llm = FakeLLMProvider(structured_responses={"EvaluationResult": default_evaluation_result()})
    redis_client = FakeAsyncRedis()
    service = make_evaluation_service(repository, fake_llm, redis_client)

    other_evaluation = Evaluation(
        session_id=session_id,
        technical_knowledge_score=1,
        reasoning_score=1,
        depth_score=1,
        communication_score=1,
        overall_score=1,
        strengths=[],
        weaknesses=[],
        evidence=[],
    )
    real_acquire = EvaluationLock.acquire

    async def acquire_after_seeding_a_competing_evaluation(self: EvaluationLock) -> bool:
        repository.create_evaluation(other_evaluation)
        repository.session.commit()
        return await real_acquire(self)

    monkeypatch.setattr(EvaluationLock, "acquire", acquire_after_seeding_a_competing_evaluation)

    result = await service.get_or_create_evaluation(session_id)

    assert result.id == other_evaluation.id
    assert len(fake_llm.calls) == 0  # never reached the LLM at all
