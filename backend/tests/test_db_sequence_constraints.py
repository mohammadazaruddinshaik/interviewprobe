"""Task 52: DB-level uniqueness of (session_id, sequence_number).

Two layers, matching the project's existing conventions:

- SQLite-backed model tests (same fixture strategy as
  tests/test_interview_topics.py) exercise the SQLAlchemy-level behavior
  of the new `UniqueConstraint`s: rejection of duplicates, isolation
  across sessions, and that FK/cascade behavior around the affected
  tables is unaffected.
- Real-PostgreSQL tests (same skip-if-unreachable convention as
  tests/test_db.py) confirm the migration actually creates named unique
  constraints in PostgreSQL and that PostgreSQL itself — not just
  SQLite — rejects a duplicate insert. These run inside a transaction
  that is always rolled back, so no data is ever persisted against the
  configured database.
"""
import uuid

import pytest
from sqlalchemy import create_engine, delete, event, select, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.domain.enums import Difficulty, MessageRole, QuestionType, Role
from app.domain.enums import InterviewTopic as InterviewTopicEnum
from app.models.interview_message import InterviewMessage
from app.models.interview_question import InterviewQuestion
from app.models.interview_session import InterviewSession


@compiles(UUID, "sqlite")
def _compile_uuid_sqlite(element, compiler, **kw):
    return "CHAR(32)"


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(element, compiler, **kw):
    return "JSON"


# ---------------------------------------------------------------------------
# SQLite-backed model tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

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


def _make_session(db_session: Session, question_limit: int = 5) -> InterviewSession:
    session = InterviewSession(
        role=Role.AI_ENGINEER,
        difficulty=Difficulty.MEDIUM,
        question_limit=question_limit,
    )
    db_session.add(session)
    db_session.flush()
    return session


def _make_question(
    db_session: Session, session_id: uuid.UUID, sequence_number: int
) -> InterviewQuestion:
    question = InterviewQuestion(
        session_id=session_id,
        sequence_number=sequence_number,
        question_text="What is retrieval-augmented generation?",
        topic=InterviewTopicEnum.RAG,
        difficulty=Difficulty.MEDIUM,
        question_type=QuestionType.INITIAL,
    )
    db_session.add(question)
    db_session.flush()
    return question


def _make_message(
    db_session: Session, session_id: uuid.UUID, sequence_number: int
) -> InterviewMessage:
    message = InterviewMessage(
        session_id=session_id,
        role=MessageRole.INTERVIEWER,
        content="What is retrieval-augmented generation?",
        sequence_number=sequence_number,
    )
    db_session.add(message)
    db_session.flush()
    return message


def test_duplicate_question_sequence_number_within_session_rejected(db_session: Session):
    session = _make_session(db_session)
    _make_question(db_session, session.id, sequence_number=1)

    duplicate = InterviewQuestion(
        session_id=session.id,
        sequence_number=1,
        question_text="A different question.",
        topic=InterviewTopicEnum.RAG,
        difficulty=Difficulty.MEDIUM,
        question_type=QuestionType.FOLLOW_UP,
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_duplicate_message_sequence_number_within_session_rejected(db_session: Session):
    session = _make_session(db_session)
    _make_message(db_session, session.id, sequence_number=1)

    duplicate = InterviewMessage(
        session_id=session.id,
        role=MessageRole.CANDIDATE,
        content="A different message.",
        sequence_number=1,
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_same_sequence_number_across_different_sessions_allowed(db_session: Session):
    session_a = _make_session(db_session)
    session_b = _make_session(db_session)

    question_a = _make_question(db_session, session_a.id, sequence_number=1)
    question_b = _make_question(db_session, session_b.id, sequence_number=1)

    assert question_a.id != question_b.id
    assert question_a.sequence_number == question_b.sequence_number == 1


def test_different_sequence_numbers_within_same_session_allowed(db_session: Session):
    session = _make_session(db_session)

    _make_question(db_session, session.id, sequence_number=1)
    _make_question(db_session, session.id, sequence_number=2)

    questions = (
        db_session.execute(select(InterviewQuestion).where(InterviewQuestion.session_id == session.id))
        .scalars()
        .all()
    )
    assert sorted(q.sequence_number for q in questions) == [1, 2]


def test_deleting_session_still_cascades_to_questions_and_messages(db_session: Session):
    session = _make_session(db_session)
    _make_question(db_session, session.id, sequence_number=1)
    _make_message(db_session, session.id, sequence_number=1)
    session_id = session.id
    db_session.commit()

    # A Core-level DELETE, not `db_session.delete(...)`, so the ORM never
    # touches the loaded question/message identity-map entries. That way
    # this test exercises the database's own ON DELETE CASCADE — the
    # thing Task 52 must leave intact — rather than the ORM's unrelated
    # (and, for these two relationships, non-cascading) default behavior
    # of nulling out a child's foreign key when its parent is deleted
    # while the child is loaded in the session.
    db_session.execute(delete(InterviewSession).where(InterviewSession.id == session_id))
    db_session.commit()

    remaining_questions = (
        db_session.execute(select(InterviewQuestion).where(InterviewQuestion.session_id == session_id))
        .scalars()
        .all()
    )
    remaining_messages = (
        db_session.execute(select(InterviewMessage).where(InterviewMessage.session_id == session_id))
        .scalars()
        .all()
    )
    assert remaining_questions == []
    assert remaining_messages == []


# ---------------------------------------------------------------------------
# Real PostgreSQL tests
#
# Each test opens its own connection/transaction and rolls back
# unconditionally in a `finally`, so nothing is ever committed against the
# configured database.
# ---------------------------------------------------------------------------


@pytest.fixture()
def pg_connection():
    from app.db.session import engine

    try:
        connection = engine.connect()
    except OperationalError as exc:
        pytest.skip(f"PostgreSQL is not reachable at the configured DATABASE_URL: {exc}")
        return
    trans = connection.begin()
    try:
        yield connection
    finally:
        if trans.is_active:
            trans.rollback()
        connection.close()


def test_postgres_has_named_unique_constraint_on_interview_questions(pg_connection):
    row = pg_connection.execute(
        text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conname = 'uq_interview_questions_session_id_sequence_number' "
            "AND conrelid = 'interview_questions'::regclass"
        )
    ).fetchone()
    assert row is not None, "uq_interview_questions_session_id_sequence_number is missing"
    assert row[0] == "UNIQUE (session_id, sequence_number)"


def test_postgres_has_named_unique_constraint_on_interview_messages(pg_connection):
    row = pg_connection.execute(
        text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conname = 'uq_interview_messages_session_id_sequence_number' "
            "AND conrelid = 'interview_messages'::regclass"
        )
    ).fetchone()
    assert row is not None, "uq_interview_messages_session_id_sequence_number is missing"
    assert row[0] == "UNIQUE (session_id, sequence_number)"


def test_postgres_rejects_duplicate_question_sequence_number(pg_connection):
    Session = sessionmaker(bind=pg_connection)
    session = Session()

    interview_session = InterviewSession(
        role=Role.AI_ENGINEER, difficulty=Difficulty.MEDIUM, question_limit=5
    )
    session.add(interview_session)
    session.flush()

    session.add(
        InterviewQuestion(
            session_id=interview_session.id,
            sequence_number=1,
            question_text="What is retrieval-augmented generation?",
            topic=InterviewTopicEnum.RAG,
            difficulty=Difficulty.MEDIUM,
            question_type=QuestionType.INITIAL,
        )
    )
    session.flush()

    session.add(
        InterviewQuestion(
            session_id=interview_session.id,
            sequence_number=1,
            question_text="A different question.",
            topic=InterviewTopicEnum.RAG,
            difficulty=Difficulty.MEDIUM,
            question_type=QuestionType.FOLLOW_UP,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()
    session.close()


def test_postgres_rejects_duplicate_message_sequence_number(pg_connection):
    Session = sessionmaker(bind=pg_connection)
    session = Session()

    interview_session = InterviewSession(
        role=Role.AI_ENGINEER, difficulty=Difficulty.MEDIUM, question_limit=5
    )
    session.add(interview_session)
    session.flush()

    session.add(
        InterviewMessage(
            session_id=interview_session.id,
            role=MessageRole.INTERVIEWER,
            content="What is retrieval-augmented generation?",
            sequence_number=1,
        )
    )
    session.flush()

    session.add(
        InterviewMessage(
            session_id=interview_session.id,
            role=MessageRole.CANDIDATE,
            content="A different message.",
            sequence_number=1,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()
    session.close()
