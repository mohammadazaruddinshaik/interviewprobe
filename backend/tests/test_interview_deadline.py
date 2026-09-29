"""Task 10 — Backend 45-minute enforcement + graceful closing.

Tests that the backend is the authoritative source of truth for the
maximum interview duration.  The candidate's answer is NEVER lost —
even when the deadline has already passed, the answer is persisted
and the session transitions to COMPLETED through the existing lifecycle.

Service-level tests mock ``is_interview_expired`` at the module level
rather than backdating ``started_at`` through SQLite, because SQLite
strips timezone info and the production helpers compare timezone-aware
datetimes.  The pure helper tests (sections A) use explicit
timezone-aware values and do not touch the database.
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.domain.enums import (
    Difficulty,
    InterviewStatus,
    InterviewTopic,
    MessageRole,
    QuestionType,
    Role,
)
from app.models.interview_session import InterviewSession
from app.repositories.interview_repository import InterviewRepository
from app.services.interview_service import (
    DEFAULT_MAX_DURATION_MINUTES,
    InterviewExpiredError,
    InterviewService,
    InvalidInterviewStateError,
    get_interview_deadline,
    is_interview_expired,
)
from app.workflows.interview.graph import InterviewWorkflow
from app.workflows.interview.models import AnswerAnalysis, GeneratedQuestion, NextAction
from tests.fakes import FakeLLMProvider

_EXPIRED = "app.services.interview_service.is_interview_expired"


# ---------------------------------------------------------------------------
# SQLite compatibility — same strategy as test_interview_service.py
# ---------------------------------------------------------------------------


@compiles(UUID, "sqlite")
def _compile_uuid_sqlite(element, compiler, **kw):
    return "CHAR(32)"


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(element, compiler, **kw):
    return "JSON"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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


def _default_fake_llm() -> FakeLLMProvider:
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


def _end_action_fake_llm() -> FakeLLMProvider:
    return FakeLLMProvider(
        structured_responses={
            "GeneratedQuestion": GeneratedQuestion(
                question="unused",
                topic=InterviewTopic.RAG,
                difficulty=Difficulty.MEDIUM,
                question_type=QuestionType.FOLLOW_UP,
            ),
            "AnswerAnalysis": AnswerAnalysis(
                understanding="GOOD",
                correctness=0.9,
                depth=0.8,
                concepts_demonstrated=["caching"],
                concepts_missing=[],
                reasoning_quality="STRONG",
                needs_follow_up=False,
            ),
            "NextAction": NextAction(
                action="END",
                topic=InterviewTopic.RAG,
                difficulty=Difficulty.MEDIUM,
                rationale="Sufficient evidence gathered.",
            ),
        }
    )


@pytest.fixture()
def fake_llm() -> FakeLLMProvider:
    return _default_fake_llm()


@pytest.fixture()
def workflow(repository: InterviewRepository, fake_llm: FakeLLMProvider) -> InterviewWorkflow:
    return InterviewWorkflow(repository=repository, llm_provider=fake_llm)


@pytest.fixture()
def service(repository: InterviewRepository, workflow: InterviewWorkflow) -> InterviewService:
    return InterviewService(repository, workflow)


def _create_session(service: InterviewService, question_limit: int = 5) -> InterviewSession:
    return service.create_interview(
        role=Role.AI_ENGINEER,
        difficulty=Difficulty.MEDIUM,
        question_limit=question_limit,
        topics=[InterviewTopic.RAG],
    )


# ===========================================================================
# A. Pure helper functions — no DB, no service
# ===========================================================================


class _StubSession:
    """Minimal stand-in: helpers only access ``started_at``."""

    def __init__(self, started_at=None):
        self.started_at = started_at


class TestGetInterviewDeadline:
    def test_returns_none_when_not_started(self):
        assert get_interview_deadline(_StubSession()) is None

    def test_returns_started_at_plus_default_duration(self):
        t = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        deadline = get_interview_deadline(_StubSession(started_at=t))
        assert deadline == t + timedelta(minutes=DEFAULT_MAX_DURATION_MINUTES)

    def test_respects_custom_duration(self):
        t = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        deadline = get_interview_deadline(_StubSession(started_at=t), max_duration_minutes=30)
        assert deadline == t + timedelta(minutes=30)


class TestIsInterviewExpired:
    def test_not_started_is_never_expired(self):
        assert is_interview_expired(_StubSession()) is False

    def test_before_deadline_is_not_expired(self):
        t = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        now = t + timedelta(minutes=44)
        assert is_interview_expired(_StubSession(started_at=t), now=now) is False

    def test_exactly_at_deadline_is_expired(self):
        t = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        now = t + timedelta(minutes=DEFAULT_MAX_DURATION_MINUTES)
        assert is_interview_expired(_StubSession(started_at=t), now=now) is True

    def test_after_deadline_is_expired(self):
        t = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        now = t + timedelta(minutes=46)
        assert is_interview_expired(_StubSession(started_at=t), now=now) is True

    def test_one_second_before_deadline_is_not_expired(self):
        t = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        now = t + timedelta(minutes=DEFAULT_MAX_DURATION_MINUTES) - timedelta(seconds=1)
        assert is_interview_expired(_StubSession(started_at=t), now=now) is False

    def test_respects_custom_duration(self):
        t = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        now = t + timedelta(minutes=31)
        assert is_interview_expired(
            _StubSession(started_at=t), now=now, max_duration_minutes=30
        ) is True

    def test_uses_current_time_when_now_omitted(self):
        far_past = datetime(2020, 1, 1, tzinfo=UTC)
        assert is_interview_expired(_StubSession(started_at=far_past)) is True


# ===========================================================================
# B. Pre-LLM deadline check — answer arrives after deadline already passed
# ===========================================================================


@pytest.mark.asyncio
async def test_expired_session_persists_candidate_answer(
    service: InterviewService, repository: InterviewRepository, db_session: Session
):
    session = _create_session(service)
    _, question, _ = await service.start_interview(session.id)

    with patch(_EXPIRED, return_value=True):
        await service.submit_answer(session.id, question.id, "My late answer")

    messages = repository.get_messages(session.id)
    candidate_msgs = [m for m in messages if m.role == MessageRole.CANDIDATE]
    assert len(candidate_msgs) == 1
    assert candidate_msgs[0].content == "My late answer"


@pytest.mark.asyncio
async def test_expired_session_transitions_to_completed(
    service: InterviewService, db_session: Session
):
    session = _create_session(service)
    _, question, _ = await service.start_interview(session.id)

    with patch(_EXPIRED, return_value=True):
        result_session, _, _ = await service.submit_answer(session.id, question.id, "answer")

    assert result_session.status is InterviewStatus.COMPLETED


@pytest.mark.asyncio
async def test_expired_session_sets_completed_at(
    service: InterviewService, db_session: Session
):
    session = _create_session(service)
    _, question, _ = await service.start_interview(session.id)

    with patch(_EXPIRED, return_value=True):
        result_session, _, _ = await service.submit_answer(session.id, question.id, "answer")

    assert result_session.completed_at is not None


@pytest.mark.asyncio
async def test_expired_session_returns_no_next_question(
    service: InterviewService, db_session: Session
):
    session = _create_session(service)
    _, question, _ = await service.start_interview(session.id)

    with patch(_EXPIRED, return_value=True):
        _, next_question, lead_in = await service.submit_answer(session.id, question.id, "answer")

    assert next_question is None
    assert lead_in is None


@pytest.mark.asyncio
async def test_expired_session_skips_llm_workflow(
    repository: InterviewRepository, db_session: Session
):
    fake_llm = _default_fake_llm()
    workflow = InterviewWorkflow(repository=repository, llm_provider=fake_llm)
    service = InterviewService(repository, workflow)

    session = _create_session(service)
    _, question, _ = await service.start_interview(session.id)
    calls_before = len(fake_llm.calls)

    with patch(_EXPIRED, return_value=True):
        await service.submit_answer(session.id, question.id, "answer")

    assert len(fake_llm.calls) == calls_before


@pytest.mark.asyncio
async def test_expired_session_increments_version(
    service: InterviewService, db_session: Session
):
    session = _create_session(service)
    started, question, _ = await service.start_interview(session.id)
    version_before = started.version

    with patch(_EXPIRED, return_value=True):
        result_session, _, _ = await service.submit_answer(session.id, question.id, "answer")

    assert result_session.version == version_before + 1


@pytest.mark.asyncio
async def test_expired_session_no_new_questions_created(
    service: InterviewService, repository: InterviewRepository, db_session: Session
):
    session = _create_session(service)
    _, question, _ = await service.start_interview(session.id)
    questions_before = len(repository.get_questions(session.id))

    with patch(_EXPIRED, return_value=True):
        await service.submit_answer(session.id, question.id, "answer")

    assert len(repository.get_questions(session.id)) == questions_before


@pytest.mark.asyncio
async def test_already_completed_by_expiry_rejects_further_answers(
    service: InterviewService, db_session: Session
):
    session = _create_session(service)
    _, question, _ = await service.start_interview(session.id)

    with patch(_EXPIRED, return_value=True):
        await service.submit_answer(session.id, question.id, "first late answer")

    with pytest.raises(InvalidInterviewStateError):
        await service.submit_answer(session.id, question.id, "second late answer")


# ===========================================================================
# C. Post-LLM deadline check — deadline passes during LLM processing
# ===========================================================================


@pytest.mark.asyncio
async def test_post_llm_expiry_persists_candidate_message(
    service: InterviewService, repository: InterviewRepository, db_session: Session
):
    session = _create_session(service)
    _, question, _ = await service.start_interview(session.id)

    with patch(_EXPIRED, side_effect=[False, True]):
        await service.submit_answer(session.id, question.id, "My answer")

    candidate_msgs = [
        m for m in repository.get_messages(session.id) if m.role == MessageRole.CANDIDATE
    ]
    assert len(candidate_msgs) == 1
    assert candidate_msgs[0].content == "My answer"


@pytest.mark.asyncio
async def test_post_llm_expiry_completes_session(
    service: InterviewService, db_session: Session
):
    session = _create_session(service)
    _, question, _ = await service.start_interview(session.id)

    with patch(_EXPIRED, side_effect=[False, True]):
        result_session, next_q, lead_in = await service.submit_answer(
            session.id, question.id, "answer"
        )

    assert result_session.status is InterviewStatus.COMPLETED
    assert result_session.completed_at is not None
    assert next_q is None
    assert lead_in is None


@pytest.mark.asyncio
async def test_post_llm_expiry_no_new_question_created(
    service: InterviewService, repository: InterviewRepository, db_session: Session
):
    session = _create_session(service)
    _, question, _ = await service.start_interview(session.id)
    questions_before = len(repository.get_questions(session.id))

    with patch(_EXPIRED, side_effect=[False, True]):
        await service.submit_answer(session.id, question.id, "answer")

    assert len(repository.get_questions(session.id)) == questions_before


@pytest.mark.asyncio
async def test_post_llm_expiry_increments_version(
    service: InterviewService, db_session: Session
):
    session = _create_session(service)
    started, question, _ = await service.start_interview(session.id)
    version_before = started.version

    with patch(_EXPIRED, side_effect=[False, True]):
        result_session, _, _ = await service.submit_answer(session.id, question.id, "answer")

    assert result_session.version == version_before + 1


@pytest.mark.asyncio
async def test_post_llm_expiry_llm_was_called(
    repository: InterviewRepository, db_session: Session
):
    """Unlike pre-LLM expiry, the workflow DOES run before the post-LLM
    check catches the deadline crossing."""
    fake_llm = _default_fake_llm()
    workflow = InterviewWorkflow(repository=repository, llm_provider=fake_llm)
    service = InterviewService(repository, workflow)

    session = _create_session(service)
    _, question, _ = await service.start_interview(session.id)
    calls_before = len(fake_llm.calls)

    with patch(_EXPIRED, side_effect=[False, True]):
        await service.submit_answer(session.id, question.id, "answer")

    assert len(fake_llm.calls) > calls_before


# ===========================================================================
# D. Within-deadline normal operation — no expiry interference
# ===========================================================================


@pytest.mark.asyncio
async def test_non_expired_session_continues_normally(
    service: InterviewService, db_session: Session
):
    session = _create_session(service)
    _, question, _ = await service.start_interview(session.id)

    with patch(_EXPIRED, return_value=False):
        result_session, next_q, _ = await service.submit_answer(session.id, question.id, "answer")

    assert result_session.status is InterviewStatus.IN_PROGRESS
    assert next_q is not None


@pytest.mark.asyncio
async def test_non_expired_session_generates_follow_up(
    service: InterviewService, db_session: Session
):
    session = _create_session(service)
    _, question, _ = await service.start_interview(session.id)

    with patch(_EXPIRED, return_value=False):
        _, next_q, _ = await service.submit_answer(session.id, question.id, "answer")

    assert next_q is not None
    assert next_q.question_type is QuestionType.FOLLOW_UP
    assert next_q.sequence_number == 2


@pytest.mark.asyncio
async def test_fresh_session_started_at_is_set(
    service: InterviewService, db_session: Session
):
    session = _create_session(service)
    started, _, _ = await service.start_interview(session.id)

    assert started.started_at is not None


@pytest.mark.asyncio
async def test_created_session_has_no_started_at(service: InterviewService):
    session = _create_session(service)
    assert session.started_at is None


# ===========================================================================
# E. Question limit + time limit interaction
# ===========================================================================


@pytest.mark.asyncio
async def test_question_limit_and_expiry_both_trigger_completion(
    repository: InterviewRepository, db_session: Session
):
    """When the last allowed answer is submitted AND the deadline has also
    passed, the session still completes exactly once (no double-commit)."""
    fake_llm = _default_fake_llm()
    workflow = InterviewWorkflow(repository=repository, llm_provider=fake_llm)
    service = InterviewService(repository, workflow)

    session = _create_session(service, question_limit=3)
    _, question, _ = await service.start_interview(session.id)

    with patch(_EXPIRED, return_value=False):
        _, question, _ = await service.submit_answer(session.id, question.id, "answer 1")
        _, question, _ = await service.submit_answer(session.id, question.id, "answer 2")

    with patch(_EXPIRED, side_effect=[False, True]):
        result_session, next_q, _ = await service.submit_answer(session.id, question.id, "answer 3")

    assert result_session.status is InterviewStatus.COMPLETED
    assert next_q is None


@pytest.mark.asyncio
async def test_question_limit_reached_but_not_expired_still_completes(
    service: InterviewService, db_session: Session
):
    session = _create_session(service, question_limit=3)
    _, question, _ = await service.start_interview(session.id)

    with patch(_EXPIRED, return_value=False):
        _, question, _ = await service.submit_answer(session.id, question.id, "answer 1")
        _, question, _ = await service.submit_answer(session.id, question.id, "answer 2")
        result_session, next_q, _ = await service.submit_answer(session.id, question.id, "answer 3")

    assert result_session.status is InterviewStatus.COMPLETED
    assert next_q is None


@pytest.mark.asyncio
async def test_not_at_limit_but_expired_completes_via_time(
    service: InterviewService, db_session: Session
):
    session = _create_session(service, question_limit=5)
    _, question, _ = await service.start_interview(session.id)

    with patch(_EXPIRED, return_value=True):
        result_session, next_q, _ = await service.submit_answer(session.id, question.id, "answer")

    assert result_session.status is InterviewStatus.COMPLETED
    assert next_q is None


# ===========================================================================
# F. END action + time limit simultaneously
# ===========================================================================


@pytest.mark.asyncio
async def test_end_action_and_expiry_both_present(
    repository: InterviewRepository, db_session: Session
):
    fake_llm = _end_action_fake_llm()
    workflow = InterviewWorkflow(repository=repository, llm_provider=fake_llm)
    service = InterviewService(repository, workflow)

    session = _create_session(service, question_limit=5)
    _, question, _ = await service.start_interview(session.id)

    with patch(_EXPIRED, side_effect=[False, True]):
        result_session, next_q, _ = await service.submit_answer(
            session.id, question.id, "answer"
        )

    assert result_session.status is InterviewStatus.COMPLETED
    assert next_q is None


@pytest.mark.asyncio
async def test_end_action_without_expiry_still_completes(
    repository: InterviewRepository, db_session: Session
):
    fake_llm = _end_action_fake_llm()
    workflow = InterviewWorkflow(repository=repository, llm_provider=fake_llm)
    service = InterviewService(repository, workflow)

    session = _create_session(service, question_limit=5)
    _, question, _ = await service.start_interview(session.id)

    with patch(_EXPIRED, return_value=False):
        result_session, next_q, _ = await service.submit_answer(
            session.id, question.id, "answer"
        )

    assert result_session.status is InterviewStatus.COMPLETED
    assert next_q is None


# ===========================================================================
# G. complete_interview endpoint with expired-but-IN_PROGRESS session
# ===========================================================================


@pytest.mark.asyncio
async def test_complete_interview_works_on_expired_but_in_progress(
    service: InterviewService, db_session: Session
):
    """complete_interview does not check expiry — it only checks status.
    An expired-but-IN_PROGRESS session completes normally."""
    session = _create_session(service)
    await service.start_interview(session.id)

    completed = service.complete_interview(session.id)

    assert completed.status is InterviewStatus.COMPLETED
    assert completed.completed_at is not None


@pytest.mark.asyncio
async def test_complete_interview_rejects_already_completed_expired_session(
    service: InterviewService, db_session: Session
):
    session = _create_session(service)
    _, question, _ = await service.start_interview(session.id)

    with patch(_EXPIRED, return_value=True):
        await service.submit_answer(session.id, question.id, "late answer")

    with pytest.raises(InvalidInterviewStateError):
        service.complete_interview(session.id)


# ===========================================================================
# H. Backward compatibility — sessions without started_at
# ===========================================================================


def test_created_session_is_never_expired(service: InterviewService):
    session = _create_session(service)
    assert is_interview_expired(session) is False


def test_created_session_has_no_deadline(service: InterviewService):
    session = _create_session(service)
    assert get_interview_deadline(session) is None


@pytest.mark.asyncio
async def test_submit_answer_on_created_session_raises_state_error(
    service: InterviewService,
):
    """A CREATED session must be started first — expiry logic does not
    interfere with the existing state guard."""
    session = _create_session(service)

    with pytest.raises(InvalidInterviewStateError):
        await service.submit_answer(session.id, uuid.uuid4(), "answer")


# ===========================================================================
# I. Transaction safety
# ===========================================================================


@pytest.mark.asyncio
async def test_pre_llm_expiry_path_commits_cleanly(
    service: InterviewService, repository: InterviewRepository, db_session: Session
):
    session = _create_session(service)
    _, question, _ = await service.start_interview(session.id)

    with patch(_EXPIRED, return_value=True):
        await service.submit_answer(session.id, question.id, "committed answer")

    db_session.expire_all()
    reloaded = repository.get_session(session.id)
    assert reloaded.status is InterviewStatus.COMPLETED
    messages = repository.get_messages(session.id)
    candidate_msgs = [m for m in messages if m.role == MessageRole.CANDIDATE]
    assert len(candidate_msgs) == 1


@pytest.mark.asyncio
async def test_post_llm_expiry_path_commits_cleanly(
    service: InterviewService, repository: InterviewRepository, db_session: Session
):
    session = _create_session(service)
    _, question, _ = await service.start_interview(session.id)

    with patch(_EXPIRED, side_effect=[False, True]):
        await service.submit_answer(session.id, question.id, "committed answer")

    db_session.expire_all()
    reloaded = repository.get_session(session.id)
    assert reloaded.status is InterviewStatus.COMPLETED


@pytest.mark.asyncio
async def test_failure_during_expiry_finalization_rolls_back(
    service: InterviewService, repository: InterviewRepository, db_session: Session
):
    session = _create_session(service)
    _, question, _ = await service.start_interview(session.id)
    version_before = session.version

    with patch(_EXPIRED, return_value=True):
        with patch.object(repository, "update_session", side_effect=RuntimeError("boom")):
            with pytest.raises(RuntimeError):
                await service.submit_answer(session.id, question.id, "answer")

    db_session.expire_all()
    reloaded = repository.get_session(session.id)
    assert reloaded.status is InterviewStatus.IN_PROGRESS
    assert reloaded.version == version_before


# ===========================================================================
# J. InterviewExpiredError registration + DEFAULT_MAX_DURATION_MINUTES
# ===========================================================================


def test_interview_expired_error_is_registered_in_main():
    from app.main import _SERVICE_ERROR_STATUS_CODES

    assert InterviewExpiredError in _SERVICE_ERROR_STATUS_CODES
    status_code, code = _SERVICE_ERROR_STATUS_CODES[InterviewExpiredError]
    assert status_code == 409
    assert code == "INTERVIEW_EXPIRED"


def test_default_max_duration_is_45():
    assert DEFAULT_MAX_DURATION_MINUTES == 45


def test_interview_expired_error_is_subclass_of_service_error():
    from app.services.interview_service import InterviewServiceError

    assert issubclass(InterviewExpiredError, InterviewServiceError)


# ===========================================================================
# K. Edge cases
# ===========================================================================


@pytest.mark.asyncio
async def test_multiple_answers_before_expiry_then_expiry_on_last(
    service: InterviewService, db_session: Session
):
    session = _create_session(service, question_limit=5)
    _, question, _ = await service.start_interview(session.id)

    with patch(_EXPIRED, return_value=False):
        _, question, _ = await service.submit_answer(session.id, question.id, "answer 1")
        _, question, _ = await service.submit_answer(session.id, question.id, "answer 2")

    with patch(_EXPIRED, return_value=True):
        result_session, next_q, _ = await service.submit_answer(session.id, question.id, "answer 3")

    assert result_session.status is InterviewStatus.COMPLETED
    assert next_q is None


@pytest.mark.asyncio
async def test_expiry_preserves_started_at_value(
    service: InterviewService, db_session: Session
):
    """Completing via expiry must not overwrite the original started_at."""
    session = _create_session(service)
    started, question, _ = await service.start_interview(session.id)
    original_started_at = started.started_at

    with patch(_EXPIRED, return_value=True):
        result_session, _, _ = await service.submit_answer(session.id, question.id, "answer")

    assert result_session.started_at == original_started_at


@pytest.mark.asyncio
async def test_expired_session_completed_at_is_set_to_recent_time(
    service: InterviewService, db_session: Session
):
    session = _create_session(service)
    _, question, _ = await service.start_interview(session.id)

    with patch(_EXPIRED, return_value=True):
        result_session, _, _ = await service.submit_answer(session.id, question.id, "answer")

    assert result_session.completed_at is not None


@pytest.mark.asyncio
async def test_complete_interview_on_non_expired_in_progress_still_works(
    service: InterviewService, db_session: Session
):
    """Voluntary early completion (before deadline) must still work."""
    session = _create_session(service)
    await service.start_interview(session.id)

    completed = service.complete_interview(session.id)

    assert completed.status is InterviewStatus.COMPLETED
    assert completed.completed_at is not None


@pytest.mark.asyncio
async def test_pre_expiry_answer_creates_interviewer_message_for_next_question(
    service: InterviewService, repository: InterviewRepository, db_session: Session
):
    """Within deadline, a follow-up question also gets an interviewer message."""
    session = _create_session(service)
    _, question, _ = await service.start_interview(session.id)

    with patch(_EXPIRED, return_value=False):
        _, next_q, _ = await service.submit_answer(session.id, question.id, "answer")

    messages = repository.get_messages(session.id)
    interviewer_msgs = [m for m in messages if m.role == MessageRole.INTERVIEWER]
    assert len(interviewer_msgs) == 2
    assert interviewer_msgs[-1].question_id == next_q.id


@pytest.mark.asyncio
async def test_expired_answer_does_not_create_interviewer_message_for_next(
    service: InterviewService, repository: InterviewRepository, db_session: Session
):
    """Pre-LLM expiry only persists the candidate message, no interviewer
    message for a question that doesn't exist."""
    session = _create_session(service)
    _, question, _ = await service.start_interview(session.id)

    with patch(_EXPIRED, return_value=True):
        await service.submit_answer(session.id, question.id, "answer")

    messages = repository.get_messages(session.id)
    interviewer_msgs = [m for m in messages if m.role == MessageRole.INTERVIEWER]
    assert len(interviewer_msgs) == 1
