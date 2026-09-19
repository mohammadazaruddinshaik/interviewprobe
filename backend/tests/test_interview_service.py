import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.domain.enums import (
    Difficulty,
    InterviewStatus,
    InterviewTopic,
    InterviewTopicStatus,
    MessageRole,
    QuestionType,
    Role,
)
from app.models.interview_message import InterviewMessage
from app.models.interview_question import InterviewQuestion
from app.models.interview_session import InterviewSession
from app.repositories.interview_repository import InterviewRepository
from app.services.interview_service import (
    InterviewNotFoundError,
    InterviewService,
    InvalidInterviewStateError,
    InvalidQuestionError,
    InvalidRoleTopicSelectionError,
)
from app.workflows.interview.graph import InterviewWorkflow
from app.workflows.interview.models import AnswerAnalysis, GeneratedQuestion, NextAction
from tests.fakes import FakeLLMProvider

# Same sqlite-compatibility strategy as tests/test_interview_repository.py
# (Task 7): teach only the sqlite dialect how to render the PostgreSQL-only
# UUID/JSONB types used by the production models, without touching the
# models themselves.


@compiles(UUID, "sqlite")
def _compile_uuid_sqlite(element, compiler, **kw):
    return "CHAR(32)"


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(element, compiler, **kw):
    return "JSON"


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    yield factory
    engine.dispose()


@pytest.fixture()
def db_session(session_factory) -> Session:
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def repository(db_session: Session) -> InterviewRepository:
    return InterviewRepository(db_session)


def default_fake_llm_provider() -> FakeLLMProvider:
    """Shared default for tests that only exercise lifecycle/state
    mechanics, not the adaptive decision itself: always proposes FOLLOW_UP
    on the current topic/difficulty. `InterviewService` never trusts
    `GeneratedQuestion.topic`/`.difficulty` for persistence — only
    `.question` — so this stays correct regardless of which session/topic
    a given test uses."""
    return FakeLLMProvider(
        structured_responses={
            "GeneratedQuestion": GeneratedQuestion(
                question="Can you go deeper on that?",
                topic=InterviewTopic.RAG,
                difficulty=Difficulty.MEDIUM,
                question_type=QuestionType.FOLLOW_UP,
            ),
            "AnswerAnalysis": AnswerAnalysis(
                understanding="BASIC",
                correctness=0.6,
                depth=0.5,
                concepts_demonstrated=[],
                concepts_missing=[],
                reasoning_quality="MODERATE",
                needs_follow_up=True,
            ),
            "NextAction": NextAction(
                action="FOLLOW_UP",
                topic=InterviewTopic.RAG,
                difficulty=Difficulty.MEDIUM,
                rationale="Probe the candidate's understanding further.",
            ),
        }
    )


@pytest.fixture()
def fake_llm() -> FakeLLMProvider:
    return default_fake_llm_provider()


@pytest.fixture()
def workflow(repository: InterviewRepository, fake_llm: FakeLLMProvider) -> InterviewWorkflow:
    return InterviewWorkflow(repository=repository, llm_provider=fake_llm)


@pytest.fixture()
def service(repository: InterviewRepository, workflow: InterviewWorkflow) -> InterviewService:
    return InterviewService(repository, workflow)


def create_session(service: InterviewService, question_limit: int = 3) -> InterviewSession:
    return service.create_interview(
        role=Role.AI_ENGINEER,
        difficulty=Difficulty.MEDIUM,
        question_limit=question_limit,
        topics=[InterviewTopic.RAG],
    )


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


def test_create_interview_sets_initial_state(service: InterviewService):
    session = create_session(service, question_limit=5)

    assert session.id is not None
    assert session.role is Role.AI_ENGINEER
    assert session.difficulty is Difficulty.MEDIUM
    assert session.question_limit == 5
    assert session.status is InterviewStatus.CREATED
    assert session.current_question_number == 0
    assert session.version == 1
    assert session.started_at is None
    assert session.completed_at is None


# ---------------------------------------------------------------------------
# Start
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_interview_transitions_state_and_creates_question(service: InterviewService):
    session = create_session(service)

    updated_session, question = await service.start_interview(session.id)

    assert updated_session.status is InterviewStatus.IN_PROGRESS
    assert updated_session.current_question_number == 1
    assert updated_session.version == 2
    assert updated_session.started_at is not None

    assert question.session_id == session.id
    assert question.sequence_number == 1
    assert question.question_type is QuestionType.INITIAL
    # Task 17: the first question's topic comes from the persisted
    # selection (`create_session`'s single topic, RAG), not a hardcoded
    # constant.
    assert question.topic is InterviewTopic.RAG
    assert question.difficulty is Difficulty.MEDIUM
    assert question.question_text


@pytest.mark.asyncio
async def test_start_interview_creates_interviewer_message(
    service: InterviewService, repository: InterviewRepository
):
    session = create_session(service)

    _, question = await service.start_interview(session.id)

    messages = repository.get_messages(session.id)
    assert len(messages) == 1
    assert messages[0].role.value == "INTERVIEWER"
    assert messages[0].question_id == question.id
    assert messages[0].sequence_number == 1
    assert messages[0].content == question.question_text


@pytest.mark.asyncio
async def test_start_interview_fails_if_already_started(service: InterviewService):
    session = create_session(service)
    await service.start_interview(session.id)

    with pytest.raises(InvalidInterviewStateError):
        await service.start_interview(session.id)


@pytest.mark.asyncio
async def test_start_interview_fails_for_nonexistent_session(service: InterviewService):
    with pytest.raises(InterviewNotFoundError):
        await service.start_interview(uuid.uuid4())


# ---------------------------------------------------------------------------
# Submit answer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_submit_answer_creates_candidate_message(
    service: InterviewService, repository: InterviewRepository
):
    session = create_session(service)
    _, question = await service.start_interview(session.id)

    await service.submit_answer(session.id, question.id, "My answer.")

    messages = repository.get_messages(session.id)
    candidate_messages = [m for m in messages if m.role.value == "CANDIDATE"]
    assert len(candidate_messages) == 1
    assert candidate_messages[0].content == "My answer."
    assert candidate_messages[0].question_id == question.id


@pytest.mark.asyncio
async def test_submit_answer_advances_current_question(service: InterviewService):
    session = create_session(service, question_limit=3)
    _, question = await service.start_interview(session.id)

    updated_session, _ = await service.submit_answer(session.id, question.id, "answer")

    assert updated_session.current_question_number == 2
    assert updated_session.version == 3


@pytest.mark.asyncio
async def test_submit_answer_creates_follow_up_question_when_limit_not_reached(service: InterviewService):
    session = create_session(service, question_limit=3)
    _, first_question = await service.start_interview(session.id)

    updated_session, next_question = await service.submit_answer(session.id, first_question.id, "answer")

    assert updated_session.status is InterviewStatus.IN_PROGRESS
    assert next_question is not None
    assert next_question.sequence_number == 2
    assert next_question.question_type is QuestionType.FOLLOW_UP
    assert next_question.topic == first_question.topic
    assert next_question.difficulty == first_question.difficulty


@pytest.mark.asyncio
async def test_submit_answer_reaches_question_limit_and_completes(
    service: InterviewService, repository: InterviewRepository
):
    session = create_session(service, question_limit=3)
    _, question = await service.start_interview(session.id)

    for _ in range(2):
        session_state, question = await service.submit_answer(session.id, question.id, "answer")
        assert session_state.status is InterviewStatus.IN_PROGRESS
        assert question is not None

    final_session, final_question = await service.submit_answer(session.id, question.id, "final answer")

    assert final_session.status is InterviewStatus.COMPLETED
    assert final_session.completed_at is not None
    assert final_question is None

    questions = repository.get_questions(session.id)
    assert len(questions) == 3


@pytest.mark.asyncio
async def test_submit_answer_fails_for_question_from_other_session(service: InterviewService):
    session_a = create_session(service)
    _, question_a = await service.start_interview(session_a.id)

    session_b = create_session(service)
    await service.start_interview(session_b.id)

    with pytest.raises(InvalidQuestionError):
        await service.submit_answer(session_b.id, question_a.id, "answer")


@pytest.mark.asyncio
async def test_submit_answer_fails_for_stale_question(service: InterviewService):
    session = create_session(service, question_limit=3)
    _, first_question = await service.start_interview(session.id)
    await service.submit_answer(session.id, first_question.id, "answer")

    with pytest.raises(InvalidQuestionError):
        await service.submit_answer(session.id, first_question.id, "answer again")


@pytest.mark.asyncio
async def test_submit_answer_fails_when_interview_completed(service: InterviewService):
    session = create_session(service, question_limit=3)
    _, question = await service.start_interview(session.id)

    for _ in range(2):
        _, question = await service.submit_answer(session.id, question.id, "answer")

    final_session, _ = await service.submit_answer(session.id, question.id, "final answer")
    assert final_session.status is InterviewStatus.COMPLETED

    with pytest.raises(InvalidInterviewStateError):
        await service.submit_answer(session.id, question.id, "another answer")


@pytest.mark.asyncio
async def test_submit_answer_fails_for_nonexistent_session(service: InterviewService):
    with pytest.raises(InterviewNotFoundError):
        await service.submit_answer(uuid.uuid4(), uuid.uuid4(), "answer")


# ---------------------------------------------------------------------------
# Complete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_complete_interview_transitions_and_sets_completed_at(service: InterviewService):
    session = create_session(service)
    await service.start_interview(session.id)

    completed = service.complete_interview(session.id)

    assert completed.status is InterviewStatus.COMPLETED
    assert completed.completed_at is not None


@pytest.mark.asyncio
async def test_complete_interview_increments_version(service: InterviewService):
    session = create_session(service)
    started_session, _ = await service.start_interview(session.id)
    version_before = started_session.version

    completed = service.complete_interview(session.id)

    assert completed.version == version_before + 1


@pytest.mark.asyncio
async def test_complete_interview_fails_if_already_completed(service: InterviewService):
    session = create_session(service)
    await service.start_interview(session.id)
    service.complete_interview(session.id)

    with pytest.raises(InvalidInterviewStateError):
        service.complete_interview(session.id)


def test_complete_interview_fails_for_nonexistent_session(service: InterviewService):
    with pytest.raises(InterviewNotFoundError):
        service.complete_interview(uuid.uuid4())


def test_complete_interview_fails_for_session_never_started(service: InterviewService):
    session = create_session(service)

    with pytest.raises(InvalidInterviewStateError):
        service.complete_interview(session.id)


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------


def test_failed_create_interview_persists_nothing(
    service: InterviewService, repository: InterviewRepository, db_session: Session
):
    with patch.object(repository, "create_session", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError):
            service.create_interview(
                role=Role.AI_ENGINEER,
                difficulty=Difficulty.EASY,
                question_limit=3,
                topics=[InterviewTopic.RAG],
            )

    remaining = db_session.execute(select(InterviewSession)).scalars().all()
    assert remaining == []


@pytest.mark.asyncio
async def test_failed_submit_answer_rolls_back_partial_writes(
    service: InterviewService, repository: InterviewRepository, db_session: Session
):
    session = create_session(service, question_limit=3)
    _, question = await service.start_interview(session.id)

    messages_before = len(repository.get_messages(session.id))
    questions_before = len(repository.get_questions(session.id))
    current_question_number_before = session.current_question_number
    version_before = session.version

    with patch.object(repository, "create_question", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError):
            await service.submit_answer(session.id, question.id, "an answer")

    # The candidate message created before the injected failure must not
    # have survived the rollback either — the whole operation is atomic.
    assert len(repository.get_messages(session.id)) == messages_before
    assert len(repository.get_questions(session.id)) == questions_before

    db_session.refresh(session)
    assert session.current_question_number == current_question_number_before
    assert session.version == version_before


# ---------------------------------------------------------------------------
# Task 17: role/topic validation at creation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "role,topics",
    [
        (Role.AI_ENGINEER, [InterviewTopic.RAG, InterviewTopic.AI_AGENTS]),
        (Role.FRONTEND_DEVELOPER, [InterviewTopic.JAVASCRIPT, InterviewTopic.REACT]),
        (Role.BACKEND_DEVELOPER, [InterviewTopic.REST_APIS, InterviewTopic.DATABASES]),
        (Role.JAVA_DEVELOPER, [InterviewTopic.CORE_JAVA, InterviewTopic.COLLECTIONS]),
    ],
)
def test_create_interview_accepts_topics_valid_for_the_role(
    service: InterviewService, role: Role, topics: list[InterviewTopic]
):
    session = service.create_interview(
        role=role, difficulty=Difficulty.MEDIUM, question_limit=3, topics=topics
    )

    assert session.role is role


@pytest.mark.parametrize(
    "role,topics",
    [
        (Role.BACKEND_DEVELOPER, [InterviewTopic.REACT]),
        (Role.FRONTEND_DEVELOPER, [InterviewTopic.DATABASES]),
        (Role.JAVA_DEVELOPER, [InterviewTopic.RAG]),
    ],
)
def test_create_interview_rejects_topics_invalid_for_the_role(
    service: InterviewService, role: Role, topics: list[InterviewTopic]
):
    with pytest.raises(InvalidRoleTopicSelectionError):
        service.create_interview(
            role=role, difficulty=Difficulty.MEDIUM, question_limit=3, topics=topics
        )


def test_create_interview_with_invalid_role_topic_persists_no_session(
    service: InterviewService, db_session: Session
):
    with pytest.raises(InvalidRoleTopicSelectionError):
        service.create_interview(
            role=Role.BACKEND_DEVELOPER,
            difficulty=Difficulty.MEDIUM,
            question_limit=3,
            topics=[InterviewTopic.REACT],
        )

    remaining = db_session.execute(select(InterviewSession)).scalars().all()
    assert remaining == []


# ---------------------------------------------------------------------------
# Task 17: topic order and starting from the first selected topic
# ---------------------------------------------------------------------------


def test_create_interview_persists_topics_in_requested_order_not_alphabetical(
    service: InterviewService, repository: InterviewRepository
):
    session = service.create_interview(
        role=Role.BACKEND_DEVELOPER,
        difficulty=Difficulty.MEDIUM,
        question_limit=3,
        topics=[InterviewTopic.DATABASES, InterviewTopic.REST_APIS, InterviewTopic.CACHING],
    )

    persisted = repository.get_topics(session.id)
    assert [t.topic for t in persisted] == [
        InterviewTopic.DATABASES,
        InterviewTopic.REST_APIS,
        InterviewTopic.CACHING,
    ]
    assert [t.sequence_number for t in persisted] == [1, 2, 3]


@pytest.mark.asyncio
async def test_start_interview_uses_first_persisted_topic_not_a_hardcoded_constant(
    service: InterviewService, repository: InterviewRepository
):
    session = service.create_interview(
        role=Role.FRONTEND_DEVELOPER,
        difficulty=Difficulty.MEDIUM,
        question_limit=3,
        topics=[InterviewTopic.REACT, InterviewTopic.JAVASCRIPT, InterviewTopic.CSS],
    )

    _, question = await service.start_interview(session.id)

    assert question.topic is InterviewTopic.REACT


@pytest.mark.asyncio
async def test_start_interview_marks_only_first_topic_in_progress(
    service: InterviewService, repository: InterviewRepository
):
    session = service.create_interview(
        role=Role.JAVA_DEVELOPER,
        difficulty=Difficulty.MEDIUM,
        question_limit=3,
        topics=[InterviewTopic.COLLECTIONS, InterviewTopic.CONCURRENCY, InterviewTopic.JVM],
    )

    topics_before = repository.get_topics(session.id)
    assert all(t.status == InterviewTopicStatus.PENDING for t in topics_before)

    await service.start_interview(session.id)

    topics_after = {t.topic: t.status for t in repository.get_topics(session.id)}
    assert topics_after[InterviewTopic.COLLECTIONS] == InterviewTopicStatus.IN_PROGRESS
    assert topics_after[InterviewTopic.CONCURRENCY] == InterviewTopicStatus.PENDING
    assert topics_after[InterviewTopic.JVM] == InterviewTopicStatus.PENDING


@pytest.mark.asyncio
async def test_start_interview_derives_topic_from_persisted_selection_not_role_catalog_order(
    service: InterviewService,
):
    # AI Engineer's role catalog lists LLM_FUNDAMENTALS first, but this
    # candidate selected AI_AGENTS first — the persisted selection order
    # must win, never the catalog's order.
    session = service.create_interview(
        role=Role.AI_ENGINEER,
        difficulty=Difficulty.MEDIUM,
        question_limit=3,
        topics=[InterviewTopic.AI_AGENTS, InterviewTopic.LLM_FUNDAMENTALS],
    )

    _, question = await service.start_interview(session.id)

    assert question.topic is InterviewTopic.AI_AGENTS


# ---------------------------------------------------------------------------
# Current question restoration on GET (Task 27)
# ---------------------------------------------------------------------------


def test_get_interview_state_returns_unanswered_question_even_if_pointer_is_stale(
    service: InterviewService, repository: InterviewRepository, db_session: Session
):
    """Defensive: `current_question` must be derived from the persisted
    questions/messages history itself, not blindly trusted from the
    session's `current_question_number` bookkeeping pointer. This
    constructs a session where that pointer is deliberately wrong —
    pointing at a question that has already been answered, while a later
    question is the genuinely unanswered one — and confirms the correct
    question is still returned."""
    session = service.create_interview(
        role=Role.AI_ENGINEER,
        difficulty=Difficulty.MEDIUM,
        question_limit=5,
        topics=[InterviewTopic.RAG],
    )

    first_question = repository.create_question(
        InterviewQuestion(
            session_id=session.id,
            sequence_number=1,
            question_text="First question?",
            topic=InterviewTopic.RAG,
            difficulty=Difficulty.MEDIUM,
            question_type=QuestionType.INITIAL,
        )
    )
    second_question = repository.create_question(
        InterviewQuestion(
            session_id=session.id,
            sequence_number=2,
            question_text="Second question?",
            topic=InterviewTopic.RAG,
            difficulty=Difficulty.MEDIUM,
            question_type=QuestionType.FOLLOW_UP,
        )
    )
    repository.create_message(
        InterviewMessage(
            session_id=session.id,
            question_id=first_question.id,
            role=MessageRole.CANDIDATE,
            content="An answer to the first question.",
            sequence_number=1,
        )
    )
    # Deliberately stale: points at the already-answered first question,
    # not the genuinely unanswered second one.
    repository.update_session(session, status=InterviewStatus.IN_PROGRESS, current_question_number=1)
    db_session.commit()

    _, _, _, _, current_question = service.get_interview_state(session.id)

    assert current_question is not None
    assert current_question.id == second_question.id


def test_get_interview_state_current_question_is_none_when_created(service: InterviewService):
    session = service.create_interview(
        role=Role.AI_ENGINEER,
        difficulty=Difficulty.MEDIUM,
        question_limit=3,
        topics=[InterviewTopic.RAG],
    )

    _, _, _, _, current_question = service.get_interview_state(session.id)

    assert current_question is None


@pytest.mark.asyncio
async def test_get_interview_state_current_question_is_none_once_completed(
    service: InterviewService,
):
    session = service.create_interview(
        role=Role.AI_ENGINEER,
        difficulty=Difficulty.MEDIUM,
        question_limit=3,
        topics=[InterviewTopic.RAG],
    )
    _, question = await service.start_interview(session.id)

    for i in range(3):
        _, next_question = await service.submit_answer(
            session.id, question.id, f"Answer {i + 1}.", idempotency_key=f"svc-complete-{i}"
        )
        if next_question is not None:
            question = next_question

    _, _, _, _, current_question = service.get_interview_state(session.id)

    assert current_question is None
