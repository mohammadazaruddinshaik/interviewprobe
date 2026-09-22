"""Task 22 — `ResultService`: result assembly, question/answer mapping,
topic ordering, evaluation integration (reusing EvaluationService's
idempotency), determinism, and no lifecycle mutation. Real SQLite-backed
`InterviewRepository` (same pattern as tests/test_evaluation_service.py),
`FakeLLMProvider` — no real Postgres/LLM.
"""

import uuid

import pytest
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy import create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.domain.enums import Difficulty, InterviewStatus, InterviewTopic, InterviewTopicStatus, QuestionType, Role
from app.evaluation.models import EvaluationResult
from app.evaluation.service import EvaluationService
from app.repositories.interview_repository import InterviewRepository
from app.services.interview_service import InterviewNotFoundError, InterviewService, InvalidInterviewStateError
from app.services.result_service import ResultService
from app.workflows.interview.graph import InterviewWorkflow
from app.workflows.interview.models import AnswerAnalysis, GeneratedQuestion, NextAction
from tests.fakes import FakeAsyncRedis, FakeLLMProvider

# Task 53: EvaluationService now requires a Redis client/lock TTL for its
# evaluation-generation lock. A fresh FakeAsyncRedis per service (never
# shared across sessions/tests) is enough here — none of these tests
# exercise lock contention itself (see tests/test_evaluation_service.py
# for that), only that ResultService's existing evaluation integration is
# unaffected by the new constructor shape.
_TEST_LOCK_TTL_SECONDS = 30


def make_evaluation_service(repository, llm_provider, redis_client=None):
    return EvaluationService(
        repository, llm_provider, redis_client or FakeAsyncRedis(), _TEST_LOCK_TTL_SECONDS
    )

# Same sqlite-compatibility strategy as tests/test_evaluation_service.py.


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


async def create_completed_interview(
    repository: InterviewRepository, question_limit: int = 3, topics: list[InterviewTopic] | None = None
) -> uuid.UUID:
    workflow = InterviewWorkflow(repository=repository, llm_provider=interview_fake_llm())
    interview_service = InterviewService(repository, workflow)
    session = interview_service.create_interview(
        role=Role.BACKEND_DEVELOPER, difficulty=Difficulty.MEDIUM, question_limit=question_limit,
        topics=topics or [InterviewTopic.DATABASES],
    )
    _, question = await interview_service.start_interview(session.id)
    for i in range(question_limit):
        _, next_question = await interview_service.submit_answer(session.id, question.id, f"answer {i}")
        if next_question is not None:
            question = next_question
    return session.id


def make_result_service(repository: InterviewRepository, llm_provider: FakeLLMProvider) -> ResultService:
    evaluation_service = make_evaluation_service(repository, llm_provider)
    return ResultService(repository, evaluation_service)


# ---------------------------------------------------------------------------
# State validation (reused from EvaluationService, never duplicated)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_created_interview_is_rejected(repository: InterviewRepository):
    workflow = InterviewWorkflow(repository=repository, llm_provider=FakeLLMProvider())
    interview_service = InterviewService(repository, workflow)
    session = interview_service.create_interview(
        role=Role.BACKEND_DEVELOPER, difficulty=Difficulty.MEDIUM, question_limit=3,
        topics=[InterviewTopic.DATABASES],
    )
    result_service = make_result_service(repository, FakeLLMProvider())

    with pytest.raises(InvalidInterviewStateError):
        await result_service.get_result(session.id)


@pytest.mark.asyncio
async def test_in_progress_interview_is_rejected(repository: InterviewRepository):
    workflow = InterviewWorkflow(repository=repository, llm_provider=interview_fake_llm())
    interview_service = InterviewService(repository, workflow)
    session = interview_service.create_interview(
        role=Role.BACKEND_DEVELOPER, difficulty=Difficulty.MEDIUM, question_limit=3,
        topics=[InterviewTopic.DATABASES],
    )
    await interview_service.start_interview(session.id)
    result_service = make_result_service(repository, FakeLLMProvider())

    with pytest.raises(InvalidInterviewStateError):
        await result_service.get_result(session.id)


@pytest.mark.asyncio
async def test_failed_interview_is_rejected(repository: InterviewRepository):
    workflow = InterviewWorkflow(repository=repository, llm_provider=interview_fake_llm())
    interview_service = InterviewService(repository, workflow)
    session = interview_service.create_interview(
        role=Role.BACKEND_DEVELOPER, difficulty=Difficulty.MEDIUM, question_limit=3,
        topics=[InterviewTopic.DATABASES],
    )
    interview_service.repository.update_session(session, status=InterviewStatus.FAILED)
    repository.session.commit()
    result_service = make_result_service(repository, FakeLLMProvider())

    with pytest.raises(InvalidInterviewStateError):
        await result_service.get_result(session.id)


@pytest.mark.asyncio
async def test_nonexistent_session_raises_not_found(repository: InterviewRepository):
    result_service = make_result_service(repository, FakeLLMProvider())

    with pytest.raises(InterviewNotFoundError):
        await result_service.get_result(uuid.uuid4())


# ---------------------------------------------------------------------------
# Result assembly
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_interview_metadata_is_correct(repository: InterviewRepository):
    session_id = await create_completed_interview(repository, question_limit=3)
    result_service = make_result_service(
        repository, FakeLLMProvider(structured_responses={"EvaluationResult": default_evaluation_result()})
    )

    result = await result_service.get_result(session_id)

    assert result.session.id == session_id
    assert result.session.role is Role.BACKEND_DEVELOPER
    assert result.session.difficulty is Difficulty.MEDIUM
    assert result.session.status is InterviewStatus.COMPLETED
    assert result.session.question_limit == 3
    assert result.session.started_at is not None
    assert result.session.completed_at is not None


@pytest.mark.asyncio
async def test_topics_are_returned_in_persisted_sequence_order(repository: InterviewRepository):
    session_id = await create_completed_interview(
        repository, question_limit=3, topics=[InterviewTopic.DATABASES, InterviewTopic.REST_APIS, InterviewTopic.CACHING]
    )
    result_service = make_result_service(
        repository, FakeLLMProvider(structured_responses={"EvaluationResult": default_evaluation_result()})
    )

    result = await result_service.get_result(session_id)

    assert [t.topic for t in result.topics] == [InterviewTopic.DATABASES, InterviewTopic.REST_APIS, InterviewTopic.CACHING]
    assert [t.sequence_number for t in result.topics] == [1, 2, 3]


@pytest.mark.asyncio
async def test_questions_are_returned_in_persisted_sequence_order(repository: InterviewRepository):
    session_id = await create_completed_interview(repository, question_limit=3)
    result_service = make_result_service(
        repository, FakeLLMProvider(structured_responses={"EvaluationResult": default_evaluation_result()})
    )

    result = await result_service.get_result(session_id)

    assert [qwa.question.sequence_number for qwa in result.questions] == [1, 2, 3]


@pytest.mark.asyncio
async def test_candidate_answers_map_to_the_correct_question_by_id(repository: InterviewRepository):
    session_id = await create_completed_interview(repository, question_limit=3)
    result_service = make_result_service(
        repository, FakeLLMProvider(structured_responses={"EvaluationResult": default_evaluation_result()})
    )

    result = await result_service.get_result(session_id)

    assert [qwa.candidate_answer for qwa in result.questions] == ["answer 0", "answer 1", "answer 2"]
    # Answer content is preserved verbatim — never rewritten/truncated.
    for qwa in result.questions:
        assert qwa.candidate_answer.startswith("answer ")


@pytest.mark.asyncio
async def test_question_never_answered_is_represented_as_none(repository: InterviewRepository):
    # /complete is called right after /start, before any answer.
    workflow = InterviewWorkflow(repository=repository, llm_provider=interview_fake_llm())
    interview_service = InterviewService(repository, workflow)
    session = interview_service.create_interview(
        role=Role.BACKEND_DEVELOPER, difficulty=Difficulty.MEDIUM, question_limit=3,
        topics=[InterviewTopic.DATABASES],
    )
    await interview_service.start_interview(session.id)
    interview_service.complete_interview(session.id)
    result_service = make_result_service(
        repository, FakeLLMProvider(structured_responses={"EvaluationResult": default_evaluation_result()})
    )

    result = await result_service.get_result(session.id)

    assert len(result.questions) == 1
    assert result.questions[0].candidate_answer is None


@pytest.mark.asyncio
async def test_question_metadata_is_correct(repository: InterviewRepository):
    session_id = await create_completed_interview(repository, question_limit=3)
    result_service = make_result_service(
        repository, FakeLLMProvider(structured_responses={"EvaluationResult": default_evaluation_result()})
    )

    result = await result_service.get_result(session_id)

    first = result.questions[0].question
    assert first.topic is InterviewTopic.DATABASES
    assert first.difficulty is Difficulty.MEDIUM
    assert first.question_type is QuestionType.INITIAL
    assert first.question_text


# ---------------------------------------------------------------------------
# Evaluation integration — reused, not duplicated
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_result_for_completed_interview_without_evaluation_triggers_exactly_one_evaluation(
    repository: InterviewRepository,
):
    session_id = await create_completed_interview(repository)
    fake_llm = FakeLLMProvider(structured_responses={"EvaluationResult": default_evaluation_result()})
    result_service = make_result_service(repository, fake_llm)

    result = await result_service.get_result(session_id)

    assert len(fake_llm.calls) == 1
    assert result.evaluation is not None


@pytest.mark.asyncio
async def test_result_with_existing_evaluation_does_not_call_the_llm(repository: InterviewRepository):
    session_id = await create_completed_interview(repository)
    fake_llm = FakeLLMProvider(structured_responses={"EvaluationResult": default_evaluation_result()})
    evaluation_service = make_evaluation_service(repository, fake_llm)
    await evaluation_service.get_or_create_evaluation(session_id)  # pre-existing evaluation
    assert len(fake_llm.calls) == 1

    result_service = ResultService(repository, evaluation_service)
    result = await result_service.get_result(session_id)

    assert len(fake_llm.calls) == 1  # no additional call
    assert result.evaluation is not None


@pytest.mark.asyncio
async def test_repeated_result_requests_do_not_generate_another_evaluation(repository: InterviewRepository):
    session_id = await create_completed_interview(repository)
    fake_llm = FakeLLMProvider(structured_responses={"EvaluationResult": default_evaluation_result()})
    result_service = make_result_service(repository, fake_llm)

    await result_service.get_result(session_id)
    await result_service.get_result(session_id)
    await result_service.get_result(session_id)

    assert len(fake_llm.calls) == 1


# ---------------------------------------------------------------------------
# Determinism / no lifecycle mutation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_repeated_get_result_returns_equivalent_data(repository: InterviewRepository):
    session_id = await create_completed_interview(repository)
    result_service = make_result_service(
        repository, FakeLLMProvider(structured_responses={"EvaluationResult": default_evaluation_result()})
    )

    first = await result_service.get_result(session_id)
    second = await result_service.get_result(session_id)

    assert first.session.status == second.session.status
    assert [q.question.id for q in first.questions] == [q.question.id for q in second.questions]
    assert [q.candidate_answer for q in first.questions] == [q.candidate_answer for q in second.questions]
    assert first.evaluation.id == second.evaluation.id
    assert float(first.evaluation.overall_score) == float(second.evaluation.overall_score)


@pytest.mark.asyncio
async def test_get_result_does_not_mutate_session_or_topics(repository: InterviewRepository):
    session_id = await create_completed_interview(repository)
    session_before = repository.get_session(session_id)
    status_before, version_before = session_before.status, session_before.version
    topics_before = {t.topic: t.status for t in repository.get_topics(session_id)}
    result_service = make_result_service(
        repository, FakeLLMProvider(structured_responses={"EvaluationResult": default_evaluation_result()})
    )

    await result_service.get_result(session_id)

    session_after = repository.get_session(session_id)
    assert session_after.status == status_before
    assert session_after.version == version_before
    topics_after = {t.topic: t.status for t in repository.get_topics(session_id)}
    assert topics_after == topics_before


@pytest.mark.asyncio
async def test_get_result_does_not_create_additional_questions_or_messages(repository: InterviewRepository):
    session_id = await create_completed_interview(repository)
    questions_before = len(repository.get_questions(session_id))
    messages_before = len(repository.get_messages(session_id))
    result_service = make_result_service(
        repository, FakeLLMProvider(structured_responses={"EvaluationResult": default_evaluation_result()})
    )

    await result_service.get_result(session_id)
    await result_service.get_result(session_id)

    assert len(repository.get_questions(session_id)) == questions_before
    assert len(repository.get_messages(session_id)) == messages_before
