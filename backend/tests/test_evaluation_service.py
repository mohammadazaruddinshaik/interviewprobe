"""Task 21 — `EvaluationService`: state validation, idempotency,
concurrency-safe persistence, transaction boundaries, and LLM-failure
propagation. Real SQLite-backed `InterviewRepository` (same pattern as
tests/test_interview_service.py), `FakeLLMProvider` — no real Postgres/LLM.
"""

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
from app.llm.exceptions import (
    LLMConfigurationError,
    LLMInvalidResponseError,
    LLMProviderUnavailableError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from app.models.evaluation import Evaluation
from app.repositories.interview_repository import InterviewRepository
from app.services.interview_service import InterviewNotFoundError, InterviewService, InvalidInterviewStateError
from app.workflows.interview.graph import InterviewWorkflow
from app.workflows.interview.models import AnswerAnalysis, GeneratedQuestion, NextAction
from tests.fakes import FakeLLMProvider

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
    evaluation_service = EvaluationService(repository, FakeLLMProvider())

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
    evaluation_service = EvaluationService(repository, FakeLLMProvider())

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
    evaluation_service = EvaluationService(repository, FakeLLMProvider())

    with pytest.raises(InvalidInterviewStateError):
        await evaluation_service.get_or_create_evaluation(session.id)


@pytest.mark.asyncio
async def test_nonexistent_session_raises_not_found(repository: InterviewRepository):
    evaluation_service = EvaluationService(repository, FakeLLMProvider())

    with pytest.raises(InterviewNotFoundError):
        await evaluation_service.get_or_create_evaluation(uuid.uuid4())


@pytest.mark.asyncio
async def test_completed_interview_is_accepted_and_persists_all_four_scores(repository: InterviewRepository):
    session_id = await create_completed_interview(repository)
    evaluation_service = EvaluationService(repository, FakeLLMProvider(structured_responses={"EvaluationResult": default_evaluation_result()}))

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
    evaluation_service = EvaluationService(repository, FakeLLMProvider(structured_responses={"EvaluationResult": result}))

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
    evaluation_service = EvaluationService(repository, fake_llm)

    first = await evaluation_service.get_or_create_evaluation(session_id)
    assert len(fake_llm.calls) == 1

    second = await evaluation_service.get_or_create_evaluation(session_id)
    third = await evaluation_service.get_or_create_evaluation(session_id)

    assert second.id == first.id == third.id
    assert len(fake_llm.calls) == 1  # no additional LLM call


@pytest.mark.asyncio
async def test_at_most_one_evaluation_row_exists_per_session(repository: InterviewRepository, db_session: Session):
    session_id = await create_completed_interview(repository)
    evaluation_service = EvaluationService(
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
    evaluation_service = EvaluationService(
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
    evaluation_service = EvaluationService(
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
    evaluation_service = EvaluationService(repository, FakeLLMProvider(error=error))

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
    evaluation_service = EvaluationService(repository, FakeLLMProvider(structured_responses={"EvaluationResult": bad_result}))

    with pytest.raises(LLMInvalidResponseError):
        await evaluation_service.get_or_create_evaluation(session_id)

    assert repository.get_evaluation(session_id) is None


@pytest.mark.asyncio
async def test_evidence_referencing_an_unknown_question_id_still_succeeds(repository: InterviewRepository):
    session_id = await create_completed_interview(repository)
    result = default_evaluation_result(
        evidence=[EvidenceItem(question_id=str(uuid.uuid4()), claim="A claim.", evidence="Some evidence.")]
    )
    evaluation_service = EvaluationService(repository, FakeLLMProvider(structured_responses={"EvaluationResult": result}))

    evaluation = await evaluation_service.get_or_create_evaluation(session_id)

    assert len(evaluation.evidence) == 1
    assert "question_id" not in evaluation.evidence[0]
