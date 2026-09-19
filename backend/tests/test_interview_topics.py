import uuid

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.domain.enums import Difficulty, InterviewTopic, InterviewTopicStatus, Role
from app.models.interview_session import InterviewSession
from app.models.interview_topic import InterviewTopicEntry
from app.repositories.interview_repository import InterviewRepository
from app.services.interview_service import InterviewService
from app.workflows.interview.graph import InterviewWorkflow
from tests.fakes import FakeLLMProvider

# Same sqlite-compatibility strategy as tests/test_interview_repository.py,
# tests/test_interview_service.py and tests/test_interview_api.py (Tasks
# 7-9): teach only the sqlite dialect how to render the PostgreSQL-only
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

    # SQLite does not enforce foreign keys (including ON DELETE CASCADE)
    # unless explicitly told to per-connection. This is required for the
    # delete-cascade test below; it has no effect on the real PostgreSQL
    # target, which always enforces FKs.
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


@pytest.fixture()
def repository(db_session: Session) -> InterviewRepository:
    return InterviewRepository(db_session)


@pytest.fixture()
def service(repository: InterviewRepository) -> InterviewService:
    # None of these tests exercise `start_interview`/`submit_answer` (only
    # `create_interview`, which never touches the workflow), so an
    # unconfigured `FakeLLMProvider` is sufficient — it is never called.
    workflow = InterviewWorkflow(repository=repository, llm_provider=FakeLLMProvider())
    return InterviewService(repository, workflow)


REQUESTED_TOPICS = [InterviewTopic.RAG, InterviewTopic.AI_AGENTS, InterviewTopic.LLM_EVALUATION]


def create_session_with_topics(service: InterviewService, topics: list[InterviewTopic] = None) -> InterviewSession:
    return service.create_interview(
        role=Role.AI_ENGINEER,
        difficulty=Difficulty.MEDIUM,
        question_limit=5,
        topics=topics if topics is not None else REQUESTED_TOPICS,
    )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def test_create_interview_persists_one_row_per_topic(
    service: InterviewService, repository: InterviewRepository
):
    session = create_session_with_topics(service)

    topics = repository.get_topics(session.id)

    assert len(topics) == 3


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------


def test_topics_retain_exact_request_order(service: InterviewService, repository: InterviewRepository):
    session = create_session_with_topics(service)

    topics = repository.get_topics(session.id)

    assert [t.topic for t in topics] == REQUESTED_TOPICS
    assert [t.sequence_number for t in topics] == [1, 2, 3]


# ---------------------------------------------------------------------------
# Initial status
# ---------------------------------------------------------------------------


def test_new_topics_start_pending(service: InterviewService, repository: InterviewRepository):
    session = create_session_with_topics(service)

    topics = repository.get_topics(session.id)

    assert all(t.status is InterviewTopicStatus.PENDING for t in topics)


# ---------------------------------------------------------------------------
# Uniqueness
# ---------------------------------------------------------------------------


def test_duplicate_topic_within_session_violates_unique_constraint(
    service: InterviewService, repository: InterviewRepository, db_session: Session
):
    session = create_session_with_topics(service, topics=[InterviewTopic.RAG])

    duplicate = InterviewTopicEntry(
        session_id=session.id,
        topic=InterviewTopic.RAG,
        sequence_number=2,
        status=InterviewTopicStatus.PENDING,
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_duplicate_sequence_number_within_session_violates_unique_constraint(
    service: InterviewService, repository: InterviewRepository, db_session: Session
):
    session = create_session_with_topics(service, topics=[InterviewTopic.RAG])

    duplicate_sequence = InterviewTopicEntry(
        session_id=session.id,
        topic=InterviewTopic.AI_AGENTS,
        sequence_number=1,
        status=InterviewTopicStatus.PENDING,
    )
    db_session.add(duplicate_sequence)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


# ---------------------------------------------------------------------------
# Session isolation
# ---------------------------------------------------------------------------


def test_topics_are_isolated_per_session(service: InterviewService, repository: InterviewRepository):
    session_a = create_session_with_topics(service, topics=[InterviewTopic.RAG])
    session_b = create_session_with_topics(service, topics=[InterviewTopic.AI_AGENTS])

    topics_a = repository.get_topics(session_a.id)
    topics_b = repository.get_topics(session_b.id)

    assert [t.topic for t in topics_a] == [InterviewTopic.RAG]
    assert [t.topic for t in topics_b] == [InterviewTopic.AI_AGENTS]


# ---------------------------------------------------------------------------
# Delete cascade
# ---------------------------------------------------------------------------


def test_deleting_session_cascades_to_topics(
    service: InterviewService, repository: InterviewRepository, db_session: Session
):
    session = create_session_with_topics(service)
    session_id = session.id
    assert len(repository.get_topics(session_id)) == 3

    db_session.delete(session)
    db_session.commit()

    remaining = db_session.execute(
        select(InterviewTopicEntry).where(InterviewTopicEntry.session_id == session_id)
    ).scalars().all()
    assert remaining == []


# ---------------------------------------------------------------------------
# Repository methods used directly
# ---------------------------------------------------------------------------


def test_get_topic_returns_single_row(service: InterviewService, repository: InterviewRepository):
    session = create_session_with_topics(service)
    created = repository.get_topics(session.id)[0]

    fetched = repository.get_topic(created.id)

    assert fetched is not None
    assert fetched.id == created.id


def test_get_topic_returns_none_for_missing(repository: InterviewRepository):
    assert repository.get_topic(uuid.uuid4()) is None


def test_get_current_topic_returns_none_when_none_in_progress(
    service: InterviewService, repository: InterviewRepository
):
    session = create_session_with_topics(service)

    assert repository.get_current_topic(session.id) is None


def test_update_topic_status_persists_change(service: InterviewService, repository: InterviewRepository):
    session = create_session_with_topics(service)
    topic = repository.get_topics(session.id)[0]

    repository.update_topic_status(topic, InterviewTopicStatus.IN_PROGRESS)

    assert repository.get_current_topic(session.id).id == topic.id
