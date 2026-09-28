"""DB-level tests for the `interview_resumes` table/model: the unique
session relationship, cascade delete, and default status — the same
concern class as tests/test_interview_topics.py, for the new resume model.
"""

import uuid

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.domain.enums import Difficulty, InterviewTopic, ResumeExtractionStatus, Role
from app.models.interview_resume import InterviewResume
from app.models.interview_session import InterviewSession
from app.repositories.interview_repository import InterviewRepository
from app.services.interview_service import InterviewService
from app.workflows.interview.graph import InterviewWorkflow
from tests.fakes import FakeLLMProvider

# Same sqlite-compatibility strategy as tests/test_interview_topics.py.


@compiles(UUID, "sqlite")
def _compile_uuid_sqlite(element, compiler, **kw):
    return "CHAR(32)"


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(element, compiler, **kw):
    return "JSON"


@pytest.fixture()
def session_factory():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

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
    workflow = InterviewWorkflow(repository=repository, llm_provider=FakeLLMProvider())
    return InterviewService(repository, workflow)


def create_session(service: InterviewService) -> InterviewSession:
    return service.create_interview(
        role=Role.AI_ENGINEER,
        difficulty=Difficulty.MEDIUM,
        question_limit=5,
        topics=[InterviewTopic.RAG],
    )


def test_create_and_get_resume(service: InterviewService, repository: InterviewRepository):
    session = create_session(service)
    resume = InterviewResume(
        session_id=session.id,
        original_filename="resume.pdf",
        content_type="application/pdf",
        file_size=1234,
    )

    repository.create_resume(resume)
    repository.session.commit()

    fetched = repository.get_resume(session.id)
    assert fetched is not None
    assert fetched.original_filename == "resume.pdf"
    assert fetched.extraction_status == ResumeExtractionStatus.UPLOADED


def test_get_resume_returns_none_when_absent(repository: InterviewRepository):
    assert repository.get_resume(uuid.uuid4()) is None


def test_only_one_resume_per_session_is_allowed(
    service: InterviewService, repository: InterviewRepository, db_session: Session
):
    session = create_session(service)
    repository.create_resume(
        InterviewResume(
            session_id=session.id, original_filename="a.pdf", content_type="application/pdf", file_size=1
        )
    )
    db_session.commit()

    second = InterviewResume(
        session_id=session.id, original_filename="b.pdf", content_type="application/pdf", file_size=1
    )
    db_session.add(second)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_deleting_session_cascades_to_resume(
    service: InterviewService, repository: InterviewRepository, db_session: Session
):
    session = create_session(service)
    repository.create_resume(
        InterviewResume(
            session_id=session.id, original_filename="a.pdf", content_type="application/pdf", file_size=1
        )
    )
    db_session.commit()
    session_id = session.id

    db_session.delete(session)
    db_session.commit()

    remaining = db_session.execute(
        select(InterviewResume).where(InterviewResume.session_id == session_id)
    ).scalars().all()
    assert remaining == []


def test_update_resume_persists_changes(service: InterviewService, repository: InterviewRepository):
    session = create_session(service)
    resume = repository.create_resume(
        InterviewResume(
            session_id=session.id, original_filename="a.pdf", content_type="application/pdf", file_size=1
        )
    )
    repository.session.commit()

    repository.update_resume(
        resume,
        extraction_status=ResumeExtractionStatus.READY,
        structured_profile={"candidate": {"name": "Jane"}},
    )
    repository.session.commit()

    fetched = repository.get_resume(session.id)
    assert fetched.extraction_status == ResumeExtractionStatus.READY
    assert fetched.structured_profile == {"candidate": {"name": "Jane"}}


def test_delete_resume_removes_the_row(
    service: InterviewService, repository: InterviewRepository, db_session: Session
):
    session = create_session(service)
    resume = repository.create_resume(
        InterviewResume(
            session_id=session.id, original_filename="a.pdf", content_type="application/pdf", file_size=1
        )
    )
    db_session.commit()

    repository.delete_resume(resume)
    db_session.commit()

    assert repository.get_resume(session.id) is None
