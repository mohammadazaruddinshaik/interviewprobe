"""TopicProgressionService is the durable-mutation-applying counterpart to
the LangGraph workflow's proposed TopicTransition — the workflow itself
never writes to PostgreSQL (see tests/test_workflow_graph.py and
tests/test_decision_validator.py for the graph/validator side, which stay
entirely repository-write-free). This file tests the service that actually
performs the transition, against a real SQLAlchemy-backed repository (same
sqlite-compatibility strategy as tests/test_interview_repository.py).
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.domain.enums import Difficulty, InterviewStatus, InterviewTopic, InterviewTopicStatus, Role
from app.models.interview_session import InterviewSession
from app.models.interview_topic import InterviewTopicEntry
from app.repositories.interview_repository import InterviewRepository
from app.services.topic_progression_service import TopicProgressionService
from app.workflows.interview.models import TopicTransition


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


@pytest.fixture()
def service(repository: InterviewRepository) -> TopicProgressionService:
    return TopicProgressionService(repository)


def create_session_with_topics(repository: InterviewRepository) -> InterviewSession:
    session = InterviewSession(
        role=Role.AI_ENGINEER,
        difficulty=Difficulty.MEDIUM,
        status=InterviewStatus.IN_PROGRESS,
        question_limit=5,
        current_question_number=1,
        version=1,
    )
    repository.create_session(session)
    repository.create_topics(
        [
            InterviewTopicEntry(session_id=session.id, topic=InterviewTopic.RAG, sequence_number=1),
            InterviewTopicEntry(session_id=session.id, topic=InterviewTopic.AI_AGENTS, sequence_number=2),
            InterviewTopicEntry(
                session_id=session.id, topic=InterviewTopic.LLM_EVALUATION, sequence_number=3
            ),
        ]
    )
    return session


def statuses_by_topic(repository: InterviewRepository, session_id) -> dict[InterviewTopic, InterviewTopicStatus]:
    return {t.topic: t.status for t in repository.get_topics(session_id)}


# ---------------------------------------------------------------------------
# initialize_topic_progression
# ---------------------------------------------------------------------------


def test_initialize_sets_first_topic_in_progress_and_rest_pending(
    service: TopicProgressionService, repository: InterviewRepository
):
    session = create_session_with_topics(repository)

    service.initialize_topic_progression(session.id)

    statuses = statuses_by_topic(repository, session.id)
    assert statuses[InterviewTopic.RAG] == InterviewTopicStatus.IN_PROGRESS
    assert statuses[InterviewTopic.AI_AGENTS] == InterviewTopicStatus.PENDING
    assert statuses[InterviewTopic.LLM_EVALUATION] == InterviewTopicStatus.PENDING


def test_initialize_is_a_committed_durable_change(
    service: TopicProgressionService, repository: InterviewRepository, db_session: Session
):
    session = create_session_with_topics(repository)

    service.initialize_topic_progression(session.id)
    db_session.expire_all()  # force a reload from the DB, not the identity map

    statuses = statuses_by_topic(repository, session.id)
    assert statuses[InterviewTopic.RAG] == InterviewTopicStatus.IN_PROGRESS


def test_apply_initial_progression_does_not_commit_on_its_own(
    service: TopicProgressionService, repository: InterviewRepository, db_session: Session
):
    # Task 17: `InterviewService.start_interview` calls this variant mid-
    # transaction and commits once itself — verify it really doesn't
    # commit by rolling back afterwards and confirming nothing persisted.
    session = create_session_with_topics(repository)
    db_session.commit()  # the session/topics themselves must survive the rollback below

    service.apply_initial_progression(session.id)
    db_session.rollback()

    statuses = statuses_by_topic(repository, session.id)
    assert statuses[InterviewTopic.RAG] == InterviewTopicStatus.PENDING


def test_initialize_with_no_topics_does_not_raise(
    service: TopicProgressionService, repository: InterviewRepository
):
    session = InterviewSession(
        role=Role.AI_ENGINEER,
        difficulty=Difficulty.MEDIUM,
        status=InterviewStatus.CREATED,
        question_limit=5,
        current_question_number=0,
        version=1,
    )
    repository.create_session(session)

    service.initialize_topic_progression(session.id)  # must not raise


# ---------------------------------------------------------------------------
# apply_transition
# ---------------------------------------------------------------------------


def test_apply_transition_completes_from_topic_and_starts_to_topic(
    service: TopicProgressionService, repository: InterviewRepository
):
    session = create_session_with_topics(repository)
    service.initialize_topic_progression(session.id)

    service.apply_transition(
        session.id, TopicTransition(from_topic=InterviewTopic.RAG, to_topic=InterviewTopic.AI_AGENTS)
    )

    statuses = statuses_by_topic(repository, session.id)
    assert statuses[InterviewTopic.RAG] == InterviewTopicStatus.COMPLETED
    assert statuses[InterviewTopic.AI_AGENTS] == InterviewTopicStatus.IN_PROGRESS
    assert statuses[InterviewTopic.LLM_EVALUATION] == InterviewTopicStatus.PENDING


def test_apply_transition_is_a_committed_durable_change(
    service: TopicProgressionService, repository: InterviewRepository, db_session: Session
):
    session = create_session_with_topics(repository)
    service.initialize_topic_progression(session.id)

    service.apply_transition(
        session.id, TopicTransition(from_topic=InterviewTopic.RAG, to_topic=InterviewTopic.AI_AGENTS)
    )
    db_session.expire_all()

    statuses = statuses_by_topic(repository, session.id)
    assert statuses[InterviewTopic.RAG] == InterviewTopicStatus.COMPLETED
    assert statuses[InterviewTopic.AI_AGENTS] == InterviewTopicStatus.IN_PROGRESS


def test_apply_transition_with_no_topics_is_a_clean_noop(
    service: TopicProgressionService, repository: InterviewRepository
):
    session = create_session_with_topics(repository)
    service.initialize_topic_progression(session.id)

    service.apply_transition(session.id, TopicTransition())  # FOLLOW_UP/CLARIFY/END case

    statuses = statuses_by_topic(repository, session.id)
    assert statuses[InterviewTopic.RAG] == InterviewTopicStatus.IN_PROGRESS  # unchanged
