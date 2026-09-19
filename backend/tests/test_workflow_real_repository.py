"""Confirms app.workflows.interview.nodes.load_interview_context genuinely
integrates with the real, SQLAlchemy-backed InterviewRepository — not just
the FakeInterviewRepository used elsewhere. Same sqlite-compatibility
strategy as tests/test_interview_repository.py (Task 7).
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.domain.enums import Difficulty, InterviewStatus, InterviewTopic, QuestionType, Role
from app.models.interview_question import InterviewQuestion
from app.models.interview_session import InterviewSession
from app.models.interview_topic import InterviewTopicEntry
from app.repositories.interview_repository import InterviewRepository
from app.workflows.interview.nodes import load_interview_context


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


def test_load_interview_context_against_real_repository(repository: InterviewRepository):
    session = InterviewSession(
        role=Role.AI_ENGINEER,
        difficulty=Difficulty.MEDIUM,
        status=InterviewStatus.IN_PROGRESS,
        question_limit=5,
        current_question_number=1,
        version=2,
    )
    repository.create_session(session)
    repository.create_topics(
        [
            InterviewTopicEntry(session_id=session.id, topic=InterviewTopic.RAG, sequence_number=1),
            InterviewTopicEntry(
                session_id=session.id, topic=InterviewTopic.AI_AGENTS, sequence_number=2
            ),
        ]
    )
    question = InterviewQuestion(
        session_id=session.id,
        sequence_number=1,
        question_text="Explain RAG.",
        topic=InterviewTopic.RAG,
        difficulty=Difficulty.MEDIUM,
        question_type=QuestionType.INITIAL,
    )
    repository.create_question(question)

    node = load_interview_context(repository)
    result = node({"session_id": session.id})

    assert result["role"] is Role.AI_ENGINEER
    assert result["difficulty"] is Difficulty.MEDIUM
    assert result["question_limit"] == 5
    assert result["current_topic"] is InterviewTopic.RAG
    assert result["current_question_id"] == question.id
    assert result["current_question"] == "Explain RAG."


def test_load_interview_context_falls_back_to_first_topic_against_real_repository(
    repository: InterviewRepository,
):
    session = InterviewSession(
        role=Role.AI_ENGINEER,
        difficulty=Difficulty.EASY,
        status=InterviewStatus.CREATED,
        question_limit=3,
        current_question_number=0,
        version=1,
    )
    repository.create_session(session)
    repository.create_topics(
        [InterviewTopicEntry(session_id=session.id, topic=InterviewTopic.LLM_EVALUATION, sequence_number=1)]
    )

    node = load_interview_context(repository)
    result = node({"session_id": session.id})

    assert result["current_topic"] is InterviewTopic.LLM_EVALUATION
    assert result["current_question_id"] is None
