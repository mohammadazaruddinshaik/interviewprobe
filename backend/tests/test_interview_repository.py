import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.domain.enums import Difficulty, InterviewStatus, InterviewTopic, MessageRole, QuestionType, Role
from app.models import Evaluation, InterviewMessage, InterviewQuestion, InterviewSession
from app.repositories.interview_repository import InterviewRepository

# The production models use PostgreSQL-specific types (dialects.postgresql
# UUID / JSONB) that the sqlite dialect cannot compile into DDL on its own.
# These hooks teach *only the sqlite dialect* how to render them as columns,
# so the real, unmodified production models can be exercised against an
# isolated in-memory SQLite database for repository-behavior tests. This
# does not touch the models or affect PostgreSQL compilation in any way:
# the Python-side value conversion (uuid.UUID <-> str, dict <-> JSON text)
# in both types is already dialect-agnostic; only DDL rendering needed help.


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


def make_session(**overrides) -> InterviewSession:
    defaults = dict(
        role=Role.AI_ENGINEER,
        difficulty=Difficulty.MEDIUM,
        status=InterviewStatus.CREATED,
        question_limit=5,
        current_question_number=0,
        version=1,
    )
    defaults.update(overrides)
    return InterviewSession(**defaults)


def make_question(session_id: uuid.UUID, **overrides) -> InterviewQuestion:
    defaults = dict(
        session_id=session_id,
        sequence_number=1,
        question_text="Explain RAG.",
        topic=InterviewTopic.RAG,
        difficulty=Difficulty.MEDIUM,
        question_type=QuestionType.INITIAL,
    )
    defaults.update(overrides)
    return InterviewQuestion(**defaults)


def make_message(session_id: uuid.UUID, **overrides) -> InterviewMessage:
    defaults = dict(
        session_id=session_id,
        role=MessageRole.INTERVIEWER,
        content="Hello, let's begin.",
        sequence_number=1,
    )
    defaults.update(overrides)
    return InterviewMessage(**defaults)


def make_evaluation(session_id: uuid.UUID, **overrides) -> Evaluation:
    defaults = dict(
        session_id=session_id,
        technical_knowledge_score="8.00",
        reasoning_score="7.50",
        depth_score="6.00",
        communication_score="9.00",
        overall_score="7.63",
        strengths=["clear communication"],
        weaknesses=["shallow on RAG"],
        evidence=[{"question_id": str(uuid.uuid4()), "note": "solid"}],
    )
    defaults.update(overrides)
    return Evaluation(**defaults)


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


def test_create_session_persists_and_assigns_id(repository: InterviewRepository):
    session = make_session()

    created = repository.create_session(session)

    assert created.id is not None


def test_get_session_returns_existing(repository: InterviewRepository):
    session = repository.create_session(make_session())

    fetched = repository.get_session(session.id)

    assert fetched is not None
    assert fetched.id == session.id
    assert fetched.role is Role.AI_ENGINEER


def test_get_session_returns_none_for_missing(repository: InterviewRepository):
    assert repository.get_session(uuid.uuid4()) is None


def test_update_session_mutates_fields(repository: InterviewRepository):
    session = repository.create_session(make_session())

    updated = repository.update_session(
        session,
        status=InterviewStatus.IN_PROGRESS,
        current_question_number=1,
    )

    assert updated.status is InterviewStatus.IN_PROGRESS
    assert updated.current_question_number == 1

    fetched = repository.get_session(session.id)
    assert fetched.status is InterviewStatus.IN_PROGRESS
    assert fetched.current_question_number == 1


# ---------------------------------------------------------------------------
# Questions
# ---------------------------------------------------------------------------


def test_create_question(repository: InterviewRepository):
    session = repository.create_session(make_session())

    question = repository.create_question(make_question(session.id))

    assert question.id is not None
    assert question.session_id == session.id


def test_get_question(repository: InterviewRepository):
    session = repository.create_session(make_session())
    created = repository.create_question(make_question(session.id))

    fetched = repository.get_question(created.id)

    assert fetched is not None
    assert fetched.id == created.id


def test_get_current_question_matches_session_current_number(repository: InterviewRepository):
    session = repository.create_session(make_session(current_question_number=2))
    repository.create_question(make_question(session.id, sequence_number=1))
    second = repository.create_question(make_question(session.id, sequence_number=2))
    repository.create_question(make_question(session.id, sequence_number=3))

    current = repository.get_current_question(session.id)

    assert current is not None
    assert current.id == second.id
    assert current.sequence_number == 2


def test_get_current_question_returns_none_when_no_match(repository: InterviewRepository):
    session = repository.create_session(make_session(current_question_number=5))
    repository.create_question(make_question(session.id, sequence_number=1))

    assert repository.get_current_question(session.id) is None


def test_get_questions_ordered_by_sequence(repository: InterviewRepository):
    session = repository.create_session(make_session())
    repository.create_question(make_question(session.id, sequence_number=3))
    repository.create_question(make_question(session.id, sequence_number=1))
    repository.create_question(make_question(session.id, sequence_number=2))

    questions = repository.get_questions(session.id)

    assert [q.sequence_number for q in questions] == [1, 2, 3]


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------


def test_create_message(repository: InterviewRepository):
    session = repository.create_session(make_session())

    message = repository.create_message(make_message(session.id))

    assert message.id is not None
    assert message.session_id == session.id


def test_get_messages_ordered_by_sequence(repository: InterviewRepository):
    session = repository.create_session(make_session())
    repository.create_message(make_message(session.id, sequence_number=2, role=MessageRole.CANDIDATE))
    repository.create_message(make_message(session.id, sequence_number=1, role=MessageRole.INTERVIEWER))
    repository.create_message(make_message(session.id, sequence_number=3, role=MessageRole.SYSTEM))

    messages = repository.get_messages(session.id)

    assert [m.sequence_number for m in messages] == [1, 2, 3]


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


def test_create_evaluation(repository: InterviewRepository):
    session = repository.create_session(make_session())

    evaluation = repository.create_evaluation(make_evaluation(session.id))

    assert evaluation.id is not None
    assert evaluation.session_id == session.id


def test_get_evaluation_returns_existing(repository: InterviewRepository):
    session = repository.create_session(make_session())
    created = repository.create_evaluation(make_evaluation(session.id))

    fetched = repository.get_evaluation(session.id)

    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.strengths == ["clear communication"]


def test_get_evaluation_returns_none_for_missing(repository: InterviewRepository):
    session = repository.create_session(make_session())

    assert repository.get_evaluation(session.id) is None


# ---------------------------------------------------------------------------
# Transaction behavior — repository must not commit internally
# ---------------------------------------------------------------------------


def test_repository_methods_do_not_commit(session_factory, db_session: Session):
    repository = InterviewRepository(db_session)
    session = repository.create_session(make_session())
    session_id = session.id

    # Only flush() has happened inside the repository — the transaction
    # should still be open on this Session.
    assert db_session.in_transaction() is True

    # Roll back without ever having committed. If the repository had
    # committed internally, this data would survive the rollback.
    db_session.rollback()

    verification_session = session_factory()
    try:
        assert InterviewRepository(verification_session).get_session(session_id) is None
    finally:
        verification_session.close()
