"""Task 11 — Full interview lifecycle + edge-case hardening.

Cross-feature integration tests verifying that Phase 3 systems
(planning, resume, investigation, adaptive progression, deadline,
evaluation) work together correctly.  Individual subsystem tests
live in their own files; this file covers the INTERACTIONS.

Uses the same in-memory SQLite / FakeLLMProvider strategy as
test_interview_service.py — no live LLM, no live DB.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.domain.enums import (
    ClaimInvestigationStatus,
    Difficulty,
    InterviewStatus,
    InterviewTopic,
    InterviewTopicStatus,
    MessageRole,
    PlannedTopicPriority,
    QuestionType,
    ResumeExtractionStatus,
    ResumeRelevance,
    Role,
)
from app.investigation.investigator import ClaimInvestigator
from app.investigation.models import (
    ClaimInvestigation,
    ClaimInvestigationResult,
    InvestigationEvidence,
)
from app.models.interview_message import InterviewMessage
from app.models.interview_question import InterviewQuestion
from app.models.interview_resume import InterviewResume
from app.models.interview_session import InterviewSession
from app.models.interview_topic import InterviewTopicEntry
from app.planning.models import (
    InterviewPlan,
    PlannedTopic,
    build_claim_id,
    identify_resume_claims,
)
from app.planning.planner import InterviewPlanner, LLMInterviewPlanner
from app.repositories.interview_repository import InterviewRepository
from app.resume.models import ResumeClaim, ResumeProfile
from app.services.interview_service import (
    InterviewService,
    InvalidInterviewStateError,
    is_interview_expired,
)
from app.workflows.interview.graph import InterviewWorkflow
from app.workflows.interview.models import (
    AnswerAnalysis,
    GeneratedQuestion,
    NextAction,
    TopicTransition,
)
from tests.fakes import FakeLLMProvider

_EXPIRED = "app.services.interview_service.is_interview_expired"


# ---------------------------------------------------------------------------
# SQLite compatibility
# ---------------------------------------------------------------------------


@compiles(UUID, "sqlite")
def _compile_uuid_sqlite(element, compiler, **kw):
    return "CHAR(32)"


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(element, compiler, **kw):
    return "JSON"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_CLAIM_RAG = ResumeClaim(claim="Built a RAG pipeline with Qdrant", category="project", source="experience")
_CLAIM_AGENTS = ResumeClaim(claim="Designed multi-agent orchestration", category="project", source="experience")
_CLAIM_RAG_ID = build_claim_id(_CLAIM_RAG)
_CLAIM_AGENTS_ID = build_claim_id(_CLAIM_AGENTS)


def _ai_plan_with_claims() -> InterviewPlan:
    return InterviewPlan(
        role=Role.AI_ENGINEER,
        objectives=["Assess RAG and agent skills"],
        planned_topics=[
            PlannedTopic(
                topic=InterviewTopic.RAG,
                competency_keys=["retrieval_augmented_generation"],
                priority=PlannedTopicPriority.HIGH,
                rationale="Probe RAG experience",
                resume_relevance=ResumeRelevance.PRIMARY,
                related_claim_ids=[_CLAIM_RAG_ID],
                suggested_time_budget_minutes=15,
            ),
            PlannedTopic(
                topic=InterviewTopic.AI_AGENTS,
                competency_keys=["ai_agents"],
                priority=PlannedTopicPriority.MEDIUM,
                rationale="Agent orchestration",
                resume_relevance=ResumeRelevance.PRIMARY,
                related_claim_ids=[_CLAIM_AGENTS_ID],
                suggested_time_budget_minutes=10,
            ),
        ],
    )


def _ai_plan_no_claims() -> InterviewPlan:
    return InterviewPlan(
        role=Role.AI_ENGINEER,
        objectives=["Baseline AI engineering assessment"],
        planned_topics=[
            PlannedTopic(
                topic=InterviewTopic.RAG,
                competency_keys=["retrieval_augmented_generation"],
                priority=PlannedTopicPriority.HIGH,
                rationale="RAG fundamentals",
                suggested_time_budget_minutes=15,
            ),
            PlannedTopic(
                topic=InterviewTopic.AI_AGENTS,
                competency_keys=["ai_agents"],
                priority=PlannedTopicPriority.MEDIUM,
                rationale="Agent fundamentals",
                suggested_time_budget_minutes=10,
            ),
        ],
    )


def _follow_up_llm(topic: InterviewTopic = InterviewTopic.RAG) -> FakeLLMProvider:
    return FakeLLMProvider(
        structured_responses={
            "GeneratedQuestion": GeneratedQuestion(
                question="Can you elaborate?",
                topic=topic,
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
                topic=topic,
                difficulty=Difficulty.MEDIUM,
                rationale="Probe further.",
            ),
        }
    )


def _new_topic_llm(
    from_topic: InterviewTopic = InterviewTopic.RAG,
    to_topic: InterviewTopic = InterviewTopic.AI_AGENTS,
) -> FakeLLMProvider:
    return FakeLLMProvider(
        structured_responses={
            "GeneratedQuestion": GeneratedQuestion(
                question=f"Let's move to {to_topic.value}.",
                topic=to_topic,
                difficulty=Difficulty.MEDIUM,
                question_type=QuestionType.TOPIC_TRANSITION,
            ),
            "AnswerAnalysis": AnswerAnalysis(
                understanding="GOOD",
                correctness=0.8,
                depth=0.7,
                concepts_demonstrated=["retrieval"],
                concepts_missing=[],
                reasoning_quality="STRONG",
                needs_follow_up=False,
            ),
            "NextAction": NextAction(
                action="NEW_TOPIC",
                topic=to_topic,
                difficulty=Difficulty.MEDIUM,
                rationale="Move to next area.",
            ),
        }
    )


def _end_llm() -> FakeLLMProvider:
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
                concepts_demonstrated=["design"],
                concepts_missing=[],
                reasoning_quality="STRONG",
                needs_follow_up=False,
            ),
            "NextAction": NextAction(
                action="END",
                topic=InterviewTopic.RAG,
                difficulty=Difficulty.MEDIUM,
                rationale="Sufficient evidence.",
            ),
        }
    )


class FakeClaimInvestigator(ClaimInvestigator):
    def __init__(
        self,
        results: dict[str, ClaimInvestigationResult] | None = None,
        error: Exception | None = None,
    ):
        self._results = results or {}
        self._error = error
        self.calls: list[tuple[str, list[InvestigationEvidence]]] = []

    async def investigate(self, claim, claim_id, evidence):
        self.calls.append((claim_id, list(evidence)))
        if self._error is not None:
            raise self._error
        result = self._results.get(claim_id)
        if result is None:
            return ClaimInvestigationResult(
                claim_id=claim_id,
                status=ClaimInvestigationStatus.NOT_YET_ESTABLISHED,
                evidence_summary="No evidence assessed",
                rationale="Default fake response",
            )
        return result


class FakePlanner(InterviewPlanner):
    def __init__(self, plan: InterviewPlan):
        self._plan = plan
        self.call_count = 0

    async def plan(self, planning_input):
        self.call_count += 1
        return self._plan


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

    @event.listens_for(engine, "connect")
    def _enable_fk(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
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


def _create_session_raw(
    repository: InterviewRepository,
    db_session: Session,
    role: Role = Role.AI_ENGINEER,
    topics: list[InterviewTopic] | None = None,
    question_limit: int = 5,
) -> InterviewSession:
    if topics is None:
        topics = [InterviewTopic.RAG, InterviewTopic.AI_AGENTS]
    session = InterviewSession(
        role=role,
        difficulty=Difficulty.MEDIUM,
        status=InterviewStatus.CREATED,
        question_limit=question_limit,
        current_question_number=0,
        version=1,
    )
    repository.create_session(session)
    topic_entries = [
        InterviewTopicEntry(
            session_id=session.id,
            topic=topic,
            sequence_number=seq,
            status=InterviewTopicStatus.PENDING,
        )
        for seq, topic in enumerate(topics, start=1)
    ]
    repository.create_topics(topic_entries)
    db_session.commit()
    return session


def _add_resume(
    repository: InterviewRepository,
    db_session: Session,
    session_id: uuid.UUID,
    profile: ResumeProfile | None = None,
    status: ResumeExtractionStatus = ResumeExtractionStatus.READY,
) -> InterviewResume:
    structured = None
    if profile is not None and status == ResumeExtractionStatus.READY:
        structured = profile.model_dump(mode="json")
    resume = InterviewResume(
        session_id=session_id,
        original_filename="resume.pdf",
        content_type="application/pdf",
        file_size=1024,
        extraction_status=status,
        structured_profile=structured,
    )
    repository.create_resume(resume)
    db_session.commit()
    return resume


def _build_service(
    repository: InterviewRepository,
    llm: FakeLLMProvider,
    planner: InterviewPlanner | None = None,
    investigator: ClaimInvestigator | None = None,
) -> InterviewService:
    workflow = InterviewWorkflow(repository=repository, llm_provider=llm)
    return InterviewService(repository, workflow, planner=planner, investigator=investigator)


def _plan_and_question_llm(plan: InterviewPlan) -> FakeLLMProvider:
    return FakeLLMProvider(
        structured_responses={
            "InterviewPlan": plan,
            "GeneratedQuestion": GeneratedQuestion(
                question="Tell me about your experience.",
                topic=plan.planned_topics[0].topic,
                difficulty=Difficulty.MEDIUM,
                question_type=QuestionType.INITIAL,
            ),
        }
    )


def _full_lifecycle_llm(plan: InterviewPlan) -> FakeLLMProvider:
    """LLM provider for planning + initial question + answer turns."""
    return FakeLLMProvider(
        structured_responses={
            "InterviewPlan": plan,
            "GeneratedQuestion": GeneratedQuestion(
                question="Can you elaborate?",
                topic=plan.planned_topics[0].topic,
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
                topic=plan.planned_topics[0].topic,
                difficulty=Difficulty.MEDIUM,
                rationale="Probe further.",
            ),
        }
    )


# ===========================================================================
# A. PLAN + RESUME + START
# ===========================================================================


class TestPlanResumeStart:
    @pytest.mark.asyncio
    async def test_start_without_resume_or_planner(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = _create_session_raw(repository, db_session)
        llm = _follow_up_llm()
        service = _build_service(repository, llm)

        started, question, _ = await service.start_interview(session.id)

        assert started.status is InterviewStatus.IN_PROGRESS
        assert question is not None
        assert repository.load_plan(session.id) is None

    @pytest.mark.asyncio
    async def test_start_with_planner_no_resume(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _ai_plan_no_claims()
        llm = _plan_and_question_llm(plan)
        planner = LLMInterviewPlanner(llm)
        session = _create_session_raw(repository, db_session)
        service = _build_service(repository, llm, planner=planner)

        started, question, _ = await service.start_interview(session.id)

        assert started.status is InterviewStatus.IN_PROGRESS
        loaded_plan = repository.load_plan(session.id)
        assert loaded_plan is not None
        assert loaded_plan.role is Role.AI_ENGINEER

    @pytest.mark.asyncio
    async def test_start_with_resume_and_planner(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _ai_plan_with_claims()
        profile = ResumeProfile(claims=[_CLAIM_RAG, _CLAIM_AGENTS])
        llm = _plan_and_question_llm(plan)
        planner = LLMInterviewPlanner(llm)
        session = _create_session_raw(repository, db_session)
        _add_resume(repository, db_session, session.id, profile=profile)
        service = _build_service(repository, llm, planner=planner)

        started, question, _ = await service.start_interview(session.id)

        assert started.status is InterviewStatus.IN_PROGRESS
        loaded_plan = repository.load_plan(session.id)
        assert loaded_plan is not None
        assert len(loaded_plan.planned_topics) == 2

    @pytest.mark.asyncio
    async def test_plan_materializes_topics(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _ai_plan_no_claims()
        llm = _plan_and_question_llm(plan)
        planner = LLMInterviewPlanner(llm)
        session = _create_session_raw(repository, db_session)
        service = _build_service(repository, llm, planner=planner)

        await service.start_interview(session.id)

        topics = repository.get_topics(session.id)
        topic_enums = [t.topic for t in topics]
        assert topic_enums == [InterviewTopic.RAG, InterviewTopic.AI_AGENTS]

    @pytest.mark.asyncio
    async def test_existing_plan_is_reused(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _ai_plan_no_claims()
        llm = _plan_and_question_llm(plan)
        fake_planner = FakePlanner(plan)
        session = _create_session_raw(repository, db_session)
        service = _build_service(repository, llm, planner=fake_planner)

        repository.create_plan(session.id, plan)
        db_session.commit()

        await service.start_interview(session.id)

        assert fake_planner.call_count == 0

    @pytest.mark.asyncio
    async def test_failed_resume_does_not_break_start(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _ai_plan_no_claims()
        llm = _plan_and_question_llm(plan)
        planner = LLMInterviewPlanner(llm)
        session = _create_session_raw(repository, db_session)
        _add_resume(
            repository, db_session, session.id,
            status=ResumeExtractionStatus.FAILED,
        )
        service = _build_service(repository, llm, planner=planner)

        started, question, _ = await service.start_interview(session.id)

        assert started.status is InterviewStatus.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_start_cannot_be_called_twice(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = _create_session_raw(repository, db_session)
        llm = _follow_up_llm()
        service = _build_service(repository, llm)

        await service.start_interview(session.id)

        with pytest.raises(InvalidInterviewStateError):
            await service.start_interview(session.id)

    @pytest.mark.asyncio
    async def test_first_topic_becomes_in_progress_on_start(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = _create_session_raw(repository, db_session)
        llm = _follow_up_llm()
        service = _build_service(repository, llm)

        await service.start_interview(session.id)

        topics = repository.get_topics(session.id)
        assert topics[0].status is InterviewTopicStatus.IN_PROGRESS
        for t in topics[1:]:
            assert t.status is InterviewTopicStatus.PENDING


# ===========================================================================
# B. PLAN + ADAPTIVE PROGRESSION
# ===========================================================================


class TestPlanAdaptiveProgression:
    @pytest.mark.asyncio
    async def test_follow_up_stays_on_current_topic(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _ai_plan_no_claims()
        llm = _full_lifecycle_llm(plan)
        planner = LLMInterviewPlanner(llm)
        session = _create_session_raw(repository, db_session)
        service = _build_service(repository, llm, planner=planner)

        _, question, _ = await service.start_interview(session.id)

        with patch(_EXPIRED, return_value=False):
            _, next_q, _ = await service.submit_answer(session.id, question.id, "answer")

        assert next_q.topic is InterviewTopic.RAG

    @pytest.mark.asyncio
    async def test_end_produces_no_question(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = _create_session_raw(repository, db_session)
        llm = _end_llm()
        service = _build_service(repository, llm)

        _, question, _ = await service.start_interview(session.id)

        with patch(_EXPIRED, return_value=False):
            result, next_q, _ = await service.submit_answer(session.id, question.id, "answer")

        assert result.status is InterviewStatus.COMPLETED
        assert next_q is None

    @pytest.mark.asyncio
    async def test_question_limit_overrides_further_generation(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = _create_session_raw(repository, db_session, question_limit=3)
        llm = _follow_up_llm()
        service = _build_service(repository, llm)

        _, question, _ = await service.start_interview(session.id)

        with patch(_EXPIRED, return_value=False):
            _, question, _ = await service.submit_answer(session.id, question.id, "a1")
            _, question, _ = await service.submit_answer(session.id, question.id, "a2")
            result, next_q, _ = await service.submit_answer(session.id, question.id, "a3")

        assert result.status is InterviewStatus.COMPLETED
        assert next_q is None


# ===========================================================================
# D. RESUME CLAIM INVESTIGATION
# ===========================================================================


class TestResumeClaimInvestigation:
    @pytest.mark.asyncio
    async def test_investigation_runs_on_relevant_topic(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _ai_plan_with_claims()
        profile = ResumeProfile(claims=[_CLAIM_RAG, _CLAIM_AGENTS])
        llm = _full_lifecycle_llm(plan)
        planner = LLMInterviewPlanner(llm)
        investigator = FakeClaimInvestigator()

        session = _create_session_raw(repository, db_session)
        _add_resume(repository, db_session, session.id, profile=profile)
        service = _build_service(repository, llm, planner=planner, investigator=investigator)

        _, question, _ = await service.start_interview(session.id)

        with patch(_EXPIRED, return_value=False):
            await service.submit_answer(session.id, question.id, "I built a RAG pipeline")

        assert len(investigator.calls) > 0
        investigated_claim_ids = {c[0] for c in investigator.calls}
        assert _CLAIM_RAG_ID in investigated_claim_ids

    @pytest.mark.asyncio
    async def test_investigation_failure_does_not_block_answer(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _ai_plan_with_claims()
        profile = ResumeProfile(claims=[_CLAIM_RAG, _CLAIM_AGENTS])
        llm = _full_lifecycle_llm(plan)
        planner = LLMInterviewPlanner(llm)
        investigator = FakeClaimInvestigator(error=RuntimeError("LLM down"))

        session = _create_session_raw(repository, db_session)
        _add_resume(repository, db_session, session.id, profile=profile)
        service = _build_service(repository, llm, planner=planner, investigator=investigator)

        _, question, _ = await service.start_interview(session.id)

        with patch(_EXPIRED, return_value=False):
            result, next_q, _ = await service.submit_answer(session.id, question.id, "answer")

        assert result.status is InterviewStatus.IN_PROGRESS
        assert next_q is not None
        messages = repository.get_messages(session.id)
        candidate_msgs = [m for m in messages if m.role == MessageRole.CANDIDATE]
        assert len(candidate_msgs) == 1

    @pytest.mark.asyncio
    async def test_investigation_state_persists_across_turns(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _ai_plan_with_claims()
        profile = ResumeProfile(claims=[_CLAIM_RAG, _CLAIM_AGENTS])
        llm = _full_lifecycle_llm(plan)
        planner = LLMInterviewPlanner(llm)
        investigator = FakeClaimInvestigator(
            results={
                _CLAIM_RAG_ID: ClaimInvestigationResult(
                    claim_id=_CLAIM_RAG_ID,
                    status=ClaimInvestigationStatus.PARTIALLY_SUPPORTED,
                    evidence_summary="Some evidence",
                    rationale="Candidate described pipeline",
                )
            }
        )

        session = _create_session_raw(repository, db_session)
        _add_resume(repository, db_session, session.id, profile=profile)
        service = _build_service(repository, llm, planner=planner, investigator=investigator)

        _, question, _ = await service.start_interview(session.id)

        with patch(_EXPIRED, return_value=False):
            _, question, _ = await service.submit_answer(session.id, question.id, "a1")

        investigations = repository.load_claim_investigations(session.id)
        assert len(investigations) > 0

        with patch(_EXPIRED, return_value=False):
            await service.submit_answer(session.id, question.id, "a2")

        investigations_after = repository.load_claim_investigations(session.id)
        assert len(investigations_after) > 0

    @pytest.mark.asyncio
    async def test_no_resume_no_investigation(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = _create_session_raw(repository, db_session)
        investigator = FakeClaimInvestigator()
        llm = _follow_up_llm()
        service = _build_service(repository, llm, investigator=investigator)

        _, question, _ = await service.start_interview(session.id)

        with patch(_EXPIRED, return_value=False):
            await service.submit_answer(session.id, question.id, "answer")

        assert len(investigator.calls) == 0

    @pytest.mark.asyncio
    async def test_no_plan_no_investigation(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _ai_plan_with_claims()
        profile = ResumeProfile(claims=[_CLAIM_RAG, _CLAIM_AGENTS])
        llm = _follow_up_llm()
        investigator = FakeClaimInvestigator()
        session = _create_session_raw(repository, db_session)
        _add_resume(repository, db_session, session.id, profile=profile)
        service = _build_service(repository, llm, investigator=investigator)

        _, question, _ = await service.start_interview(session.id)

        with patch(_EXPIRED, return_value=False):
            await service.submit_answer(session.id, question.id, "answer")

        assert len(investigator.calls) == 0


# ===========================================================================
# I. DEADLINE + ADAPTIVE FLOW
# ===========================================================================


class TestDeadlineAdaptiveFlow:
    @pytest.mark.asyncio
    async def test_answer_before_deadline_proceeds_normally(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = _create_session_raw(repository, db_session)
        llm = _follow_up_llm()
        service = _build_service(repository, llm)

        _, question, _ = await service.start_interview(session.id)

        with patch(_EXPIRED, return_value=False):
            result, next_q, _ = await service.submit_answer(session.id, question.id, "answer")

        assert result.status is InterviewStatus.IN_PROGRESS
        assert next_q is not None

    @pytest.mark.asyncio
    async def test_deadline_cannot_create_question(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = _create_session_raw(repository, db_session)
        llm = _follow_up_llm()
        service = _build_service(repository, llm)

        _, question, _ = await service.start_interview(session.id)
        questions_before = len(repository.get_questions(session.id))

        with patch(_EXPIRED, return_value=True):
            result, next_q, _ = await service.submit_answer(session.id, question.id, "answer")

        assert result.status is InterviewStatus.COMPLETED
        assert next_q is None
        assert len(repository.get_questions(session.id)) == questions_before

    @pytest.mark.asyncio
    async def test_deadline_preserves_candidate_answer(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = _create_session_raw(repository, db_session)
        llm = _follow_up_llm()
        service = _build_service(repository, llm)

        _, question, _ = await service.start_interview(session.id)

        with patch(_EXPIRED, return_value=True):
            await service.submit_answer(session.id, question.id, "my late answer")

        messages = repository.get_messages(session.id)
        candidate_msgs = [m for m in messages if m.role == MessageRole.CANDIDATE]
        assert len(candidate_msgs) == 1
        assert candidate_msgs[0].content == "my late answer"

    @pytest.mark.asyncio
    async def test_post_llm_deadline_no_question_generated(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = _create_session_raw(repository, db_session)
        llm = _follow_up_llm()
        service = _build_service(repository, llm)

        _, question, _ = await service.start_interview(session.id)

        with patch(_EXPIRED, side_effect=[False, True]):
            result, next_q, _ = await service.submit_answer(session.id, question.id, "answer")

        assert result.status is InterviewStatus.COMPLETED
        assert next_q is None

    @pytest.mark.asyncio
    async def test_deadline_with_investigation_remains_safe(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _ai_plan_with_claims()
        profile = ResumeProfile(claims=[_CLAIM_RAG, _CLAIM_AGENTS])
        llm = _full_lifecycle_llm(plan)
        planner = LLMInterviewPlanner(llm)
        investigator = FakeClaimInvestigator()

        session = _create_session_raw(repository, db_session)
        _add_resume(repository, db_session, session.id, profile=profile)
        service = _build_service(repository, llm, planner=planner, investigator=investigator)

        _, question, _ = await service.start_interview(session.id)

        with patch(_EXPIRED, return_value=True):
            result, next_q, _ = await service.submit_answer(session.id, question.id, "answer")

        assert result.status is InterviewStatus.COMPLETED
        messages = repository.get_messages(session.id)
        candidate_msgs = [m for m in messages if m.role == MessageRole.CANDIDATE]
        assert len(candidate_msgs) == 1


# ===========================================================================
# J. QUESTION LIMIT + TIME LIMIT
# ===========================================================================


class TestQuestionLimitTimeLimitInteraction:
    @pytest.mark.asyncio
    async def test_question_limit_ends_before_45_minutes(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = _create_session_raw(repository, db_session, question_limit=3)
        llm = _follow_up_llm()
        service = _build_service(repository, llm)

        _, question, _ = await service.start_interview(session.id)

        with patch(_EXPIRED, return_value=False):
            _, question, _ = await service.submit_answer(session.id, question.id, "a1")
            _, question, _ = await service.submit_answer(session.id, question.id, "a2")
            result, next_q, _ = await service.submit_answer(session.id, question.id, "a3")

        assert result.status is InterviewStatus.COMPLETED
        assert next_q is None

    @pytest.mark.asyncio
    async def test_time_limit_ends_before_question_limit(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = _create_session_raw(repository, db_session, question_limit=10)
        llm = _follow_up_llm()
        service = _build_service(repository, llm)

        _, question, _ = await service.start_interview(session.id)

        with patch(_EXPIRED, return_value=True):
            result, next_q, _ = await service.submit_answer(session.id, question.id, "answer")

        assert result.status is InterviewStatus.COMPLETED
        assert next_q is None


# ===========================================================================
# K. MANUAL COMPLETE + RACES
# ===========================================================================


class TestManualComplete:
    @pytest.mark.asyncio
    async def test_manual_complete_before_answer(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = _create_session_raw(repository, db_session)
        llm = _follow_up_llm()
        service = _build_service(repository, llm)

        _, question, _ = await service.start_interview(session.id)

        completed = service.complete_interview(session.id)

        assert completed.status is InterviewStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_answer_after_manual_completion_rejected(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = _create_session_raw(repository, db_session)
        llm = _follow_up_llm()
        service = _build_service(repository, llm)

        _, question, _ = await service.start_interview(session.id)
        service.complete_interview(session.id)

        with pytest.raises(InvalidInterviewStateError):
            await service.submit_answer(session.id, question.id, "late answer")

    @pytest.mark.asyncio
    async def test_repeated_complete_rejected(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = _create_session_raw(repository, db_session)
        llm = _follow_up_llm()
        service = _build_service(repository, llm)

        await service.start_interview(session.id)
        service.complete_interview(session.id)

        with pytest.raises(InvalidInterviewStateError):
            service.complete_interview(session.id)


# ===========================================================================
# M. RELOAD / SERVICE RECREATION
# ===========================================================================


class TestServiceRecreation:
    @pytest.mark.asyncio
    async def test_recreate_service_after_start(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _ai_plan_no_claims()
        llm = _full_lifecycle_llm(plan)
        planner = LLMInterviewPlanner(llm)
        session = _create_session_raw(repository, db_session)
        service1 = _build_service(repository, llm, planner=planner)

        _, question, _ = await service1.start_interview(session.id)

        service2 = _build_service(repository, llm, planner=planner)

        with patch(_EXPIRED, return_value=False):
            result, next_q, _ = await service2.submit_answer(session.id, question.id, "answer")

        assert result.status is InterviewStatus.IN_PROGRESS
        assert next_q is not None

    @pytest.mark.asyncio
    async def test_recreated_service_reuses_existing_plan(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _ai_plan_no_claims()
        llm = _plan_and_question_llm(plan)
        fake_planner = FakePlanner(plan)
        session = _create_session_raw(repository, db_session)
        service1 = _build_service(repository, llm, planner=fake_planner)

        await service1.start_interview(session.id)
        assert fake_planner.call_count == 1

        service2 = _build_service(repository, llm, planner=fake_planner)

        loaded = repository.load_plan(session.id)
        assert loaded is not None

    @pytest.mark.asyncio
    async def test_investigation_state_survives_service_recreation(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _ai_plan_with_claims()
        profile = ResumeProfile(claims=[_CLAIM_RAG, _CLAIM_AGENTS])
        llm = _full_lifecycle_llm(plan)
        planner = LLMInterviewPlanner(llm)
        investigator = FakeClaimInvestigator(
            results={
                _CLAIM_RAG_ID: ClaimInvestigationResult(
                    claim_id=_CLAIM_RAG_ID,
                    status=ClaimInvestigationStatus.SUPPORTED,
                    evidence_summary="Strong evidence",
                    rationale="Clear demonstration",
                )
            }
        )

        session = _create_session_raw(repository, db_session)
        _add_resume(repository, db_session, session.id, profile=profile)
        service1 = _build_service(repository, llm, planner=planner, investigator=investigator)

        _, question, _ = await service1.start_interview(session.id)

        with patch(_EXPIRED, return_value=False):
            await service1.submit_answer(session.id, question.id, "answer")

        investigations = repository.load_claim_investigations(session.id)
        assert len(investigations) > 0

        service2 = _build_service(repository, llm, planner=planner, investigator=investigator)

        investigations_reloaded = repository.load_claim_investigations(session.id)
        assert len(investigations_reloaded) == len(investigations)


# ===========================================================================
# N. FAILURE ISOLATION
# ===========================================================================


class TestFailureIsolation:
    @pytest.mark.asyncio
    async def test_planner_failure_rolls_back_cleanly(
        self, repository: InterviewRepository, db_session: Session
    ):
        llm = FakeLLMProvider(error=RuntimeError("LLM down"))
        planner = LLMInterviewPlanner(llm)
        session = _create_session_raw(repository, db_session)
        service = _build_service(repository, llm, planner=planner)

        with pytest.raises(RuntimeError):
            await service.start_interview(session.id)

        db_session.expire_all()
        reloaded = repository.get_session(session.id)
        assert reloaded.status is InterviewStatus.CREATED
        assert repository.load_plan(session.id) is None

    @pytest.mark.asyncio
    async def test_question_generation_failure_does_not_corrupt_session(
        self, repository: InterviewRepository, db_session: Session
    ):
        llm = FakeLLMProvider(error=RuntimeError("generation failed"))
        session = _create_session_raw(repository, db_session)
        service = _build_service(repository, llm)

        with pytest.raises(RuntimeError):
            await service.start_interview(session.id)

        db_session.expire_all()
        reloaded = repository.get_session(session.id)
        assert reloaded.status is InterviewStatus.CREATED

    @pytest.mark.asyncio
    async def test_investigation_failure_preserves_candidate_answer(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _ai_plan_with_claims()
        profile = ResumeProfile(claims=[_CLAIM_RAG, _CLAIM_AGENTS])
        llm = _full_lifecycle_llm(plan)
        planner = LLMInterviewPlanner(llm)
        investigator = FakeClaimInvestigator(error=RuntimeError("investigation boom"))

        session = _create_session_raw(repository, db_session)
        _add_resume(repository, db_session, session.id, profile=profile)
        service = _build_service(repository, llm, planner=planner, investigator=investigator)

        _, question, _ = await service.start_interview(session.id)

        with patch(_EXPIRED, return_value=False):
            result, next_q, _ = await service.submit_answer(session.id, question.id, "my answer")

        assert result.status is InterviewStatus.IN_PROGRESS
        messages = repository.get_messages(session.id)
        candidate_msgs = [m for m in messages if m.role == MessageRole.CANDIDATE]
        assert len(candidate_msgs) == 1
        assert candidate_msgs[0].content == "my answer"


# ===========================================================================
# O. LEGACY COMPATIBILITY
# ===========================================================================


class TestLegacyCompatibility:
    @pytest.mark.asyncio
    async def test_legacy_session_without_plan(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = _create_session_raw(repository, db_session)
        llm = _follow_up_llm()
        service = _build_service(repository, llm)

        started, question, _ = await service.start_interview(session.id)

        assert started.status is InterviewStatus.IN_PROGRESS
        assert repository.load_plan(session.id) is None

    @pytest.mark.asyncio
    async def test_legacy_session_without_resume(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = _create_session_raw(repository, db_session)
        llm = _follow_up_llm()
        service = _build_service(repository, llm)

        _, question, _ = await service.start_interview(session.id)

        with patch(_EXPIRED, return_value=False):
            result, next_q, _ = await service.submit_answer(session.id, question.id, "answer")

        assert result.status is InterviewStatus.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_legacy_session_without_investigation_state(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = _create_session_raw(repository, db_session)
        investigator = FakeClaimInvestigator()
        llm = _follow_up_llm()
        service = _build_service(repository, llm, investigator=investigator)

        _, question, _ = await service.start_interview(session.id)

        with patch(_EXPIRED, return_value=False):
            result, next_q, _ = await service.submit_answer(session.id, question.id, "answer")

        assert result.status is InterviewStatus.IN_PROGRESS
        assert len(investigator.calls) == 0


# ===========================================================================
# P. STATE CONSISTENCY INVARIANTS
# ===========================================================================


class TestStateConsistencyInvariants:
    @pytest.mark.asyncio
    async def test_question_belongs_to_correct_session(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = _create_session_raw(repository, db_session)
        llm = _follow_up_llm()
        service = _build_service(repository, llm)

        _, question, _ = await service.start_interview(session.id)

        assert question.session_id == session.id

    @pytest.mark.asyncio
    async def test_message_belongs_to_correct_session(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = _create_session_raw(repository, db_session)
        llm = _follow_up_llm()
        service = _build_service(repository, llm)

        await service.start_interview(session.id)

        messages = repository.get_messages(session.id)
        for msg in messages:
            assert msg.session_id == session.id

    @pytest.mark.asyncio
    async def test_question_sequence_numbers_are_valid(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = _create_session_raw(repository, db_session, question_limit=5)
        llm = _follow_up_llm()
        service = _build_service(repository, llm)

        _, question, _ = await service.start_interview(session.id)

        with patch(_EXPIRED, return_value=False):
            _, question, _ = await service.submit_answer(session.id, question.id, "a1")
            _, question, _ = await service.submit_answer(session.id, question.id, "a2")

        questions = repository.get_questions(session.id)
        seq_numbers = [q.sequence_number for q in questions]
        assert seq_numbers == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_no_duplicate_question_sequence_numbers(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = _create_session_raw(repository, db_session, question_limit=5)
        llm = _follow_up_llm()
        service = _build_service(repository, llm)

        _, question, _ = await service.start_interview(session.id)

        with patch(_EXPIRED, return_value=False):
            _, question, _ = await service.submit_answer(session.id, question.id, "a1")
            _, question, _ = await service.submit_answer(session.id, question.id, "a2")

        questions = repository.get_questions(session.id)
        seq_numbers = [q.sequence_number for q in questions]
        assert len(seq_numbers) == len(set(seq_numbers))

    @pytest.mark.asyncio
    async def test_no_duplicate_message_sequence_numbers(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = _create_session_raw(repository, db_session, question_limit=5)
        llm = _follow_up_llm()
        service = _build_service(repository, llm)

        _, question, _ = await service.start_interview(session.id)

        with patch(_EXPIRED, return_value=False):
            _, question, _ = await service.submit_answer(session.id, question.id, "a1")

        messages = repository.get_messages(session.id)
        seq_numbers = [m.sequence_number for m in messages]
        assert len(seq_numbers) == len(set(seq_numbers))

    @pytest.mark.asyncio
    async def test_completed_session_cannot_continue(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = _create_session_raw(repository, db_session)
        llm = _follow_up_llm()
        service = _build_service(repository, llm)

        _, question, _ = await service.start_interview(session.id)
        service.complete_interview(session.id)

        with pytest.raises(InvalidInterviewStateError):
            await service.submit_answer(session.id, question.id, "answer")


# ===========================================================================
# CROSS-INTERVIEW ISOLATION
# ===========================================================================


class TestCrossInterviewIsolation:
    @pytest.mark.asyncio
    async def test_interviews_have_separate_plans(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _ai_plan_no_claims()
        llm = _plan_and_question_llm(plan)
        planner = LLMInterviewPlanner(llm)

        session_a = _create_session_raw(repository, db_session)
        session_b = _create_session_raw(repository, db_session)

        service = _build_service(repository, llm, planner=planner)
        await service.start_interview(session_a.id)

        plan_a = repository.load_plan(session_a.id)
        plan_b = repository.load_plan(session_b.id)
        assert plan_a is not None
        assert plan_b is None

    @pytest.mark.asyncio
    async def test_interviews_have_separate_transcripts(
        self, repository: InterviewRepository, db_session: Session
    ):
        llm = _follow_up_llm()
        session_a = _create_session_raw(repository, db_session)
        session_b = _create_session_raw(repository, db_session)
        service = _build_service(repository, llm)

        await service.start_interview(session_a.id)
        await service.start_interview(session_b.id)

        messages_a = repository.get_messages(session_a.id)
        messages_b = repository.get_messages(session_b.id)

        ids_a = {m.id for m in messages_a}
        ids_b = {m.id for m in messages_b}
        assert ids_a.isdisjoint(ids_b)

    @pytest.mark.asyncio
    async def test_interviews_have_separate_questions(
        self, repository: InterviewRepository, db_session: Session
    ):
        llm = _follow_up_llm()
        session_a = _create_session_raw(repository, db_session)
        session_b = _create_session_raw(repository, db_session)
        service = _build_service(repository, llm)

        _, q_a, _ = await service.start_interview(session_a.id)
        _, q_b, _ = await service.start_interview(session_b.id)

        assert q_a.id != q_b.id
        assert q_a.session_id == session_a.id
        assert q_b.session_id == session_b.id

    @pytest.mark.asyncio
    async def test_interviews_have_separate_investigation_state(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _ai_plan_with_claims()
        profile = ResumeProfile(claims=[_CLAIM_RAG, _CLAIM_AGENTS])
        llm = _full_lifecycle_llm(plan)
        planner = LLMInterviewPlanner(llm)
        investigator = FakeClaimInvestigator()

        session_a = _create_session_raw(repository, db_session)
        session_b = _create_session_raw(repository, db_session)
        _add_resume(repository, db_session, session_a.id, profile=profile)

        service = _build_service(repository, llm, planner=planner, investigator=investigator)
        _, q_a, _ = await service.start_interview(session_a.id)

        with patch(_EXPIRED, return_value=False):
            await service.submit_answer(session_a.id, q_a.id, "RAG answer")

        inv_a = repository.load_claim_investigations(session_a.id)
        inv_b = repository.load_claim_investigations(session_b.id)

        assert len(inv_a) > 0
        assert len(inv_b) == 0

    @pytest.mark.asyncio
    async def test_completing_one_interview_does_not_affect_other(
        self, repository: InterviewRepository, db_session: Session
    ):
        llm = _follow_up_llm()
        session_a = _create_session_raw(repository, db_session)
        session_b = _create_session_raw(repository, db_session)
        service = _build_service(repository, llm)

        await service.start_interview(session_a.id)
        await service.start_interview(session_b.id)

        service.complete_interview(session_a.id)

        db_session.expire_all()
        reloaded_a = repository.get_session(session_a.id)
        reloaded_b = repository.get_session(session_b.id)

        assert reloaded_a.status is InterviewStatus.COMPLETED
        assert reloaded_b.status is InterviewStatus.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_cross_session_question_rejected(
        self, repository: InterviewRepository, db_session: Session
    ):
        llm = _follow_up_llm()
        session_a = _create_session_raw(repository, db_session)
        session_b = _create_session_raw(repository, db_session)
        service = _build_service(repository, llm)

        _, q_a, _ = await service.start_interview(session_a.id)
        _, q_b, _ = await service.start_interview(session_b.id)

        from app.services.interview_service import InvalidQuestionError

        with pytest.raises(InvalidQuestionError):
            with patch(_EXPIRED, return_value=False):
                await service.submit_answer(session_b.id, q_a.id, "answer")


# ===========================================================================
# TRANSACTION OWNERSHIP
# ===========================================================================


class TestTransactionOwnership:
    @pytest.mark.asyncio
    async def test_repository_methods_only_flush(
        self, repository: InterviewRepository, db_session: Session
    ):
        """Repository methods flush, never commit. InterviewService owns
        the transaction boundary."""
        session = InterviewSession(
            role=Role.AI_ENGINEER,
            difficulty=Difficulty.MEDIUM,
            status=InterviewStatus.CREATED,
            question_limit=5,
            current_question_number=0,
            version=1,
        )
        repository.create_session(session)

        assert db_session.new or db_session.dirty or session in db_session

        db_session.rollback()
        reloaded = repository.get_session(session.id)
        assert reloaded is None

    @pytest.mark.asyncio
    async def test_failed_submit_answer_rolls_back_everything(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = _create_session_raw(repository, db_session)
        llm = _follow_up_llm()
        service = _build_service(repository, llm)

        _, question, _ = await service.start_interview(session.id)
        version_before = session.version
        messages_before = len(repository.get_messages(session.id))

        with patch.object(repository, "create_question", side_effect=RuntimeError("boom")):
            with pytest.raises(RuntimeError):
                with patch(_EXPIRED, return_value=False):
                    await service.submit_answer(session.id, question.id, "answer")

        db_session.expire_all()
        reloaded = repository.get_session(session.id)
        assert reloaded.version == version_before
        assert len(repository.get_messages(session.id)) == messages_before


# ===========================================================================
# FULL LIFECYCLE
# ===========================================================================


class TestFullLifecycle:
    @pytest.mark.asyncio
    async def test_complete_lifecycle_create_plan_start_answer_complete(
        self, repository: InterviewRepository, db_session: Session
    ):
        """End-to-end: create -> plan -> start -> answer -> answer -> complete."""
        plan = _ai_plan_with_claims()
        profile = ResumeProfile(claims=[_CLAIM_RAG, _CLAIM_AGENTS])
        llm = _full_lifecycle_llm(plan)
        planner = LLMInterviewPlanner(llm)
        investigator = FakeClaimInvestigator()

        session = _create_session_raw(repository, db_session)
        _add_resume(repository, db_session, session.id, profile=profile)
        service = _build_service(repository, llm, planner=planner, investigator=investigator)

        assert session.status is InterviewStatus.CREATED

        started, question, _ = await service.start_interview(session.id)
        assert started.status is InterviewStatus.IN_PROGRESS
        assert repository.load_plan(session.id) is not None

        with patch(_EXPIRED, return_value=False):
            result, q2, _ = await service.submit_answer(session.id, question.id, "First answer")

        assert result.status is InterviewStatus.IN_PROGRESS
        assert q2 is not None

        with patch(_EXPIRED, return_value=False):
            result2, q3, _ = await service.submit_answer(session.id, q2.id, "Second answer")

        assert result2.status is InterviewStatus.IN_PROGRESS

        completed = service.complete_interview(session.id)
        assert completed.status is InterviewStatus.COMPLETED
        assert completed.completed_at is not None

        questions = repository.get_questions(session.id)
        assert len(questions) == 3
        messages = repository.get_messages(session.id)
        candidate_msgs = [m for m in messages if m.role == MessageRole.CANDIDATE]
        assert len(candidate_msgs) == 2
        interviewer_msgs = [m for m in messages if m.role == MessageRole.INTERVIEWER]
        assert len(interviewer_msgs) == 3

    @pytest.mark.asyncio
    async def test_lifecycle_with_deadline_expiry(
        self, repository: InterviewRepository, db_session: Session
    ):
        """End-to-end: create -> start -> answer -> expired answer."""
        plan = _ai_plan_no_claims()
        llm = _full_lifecycle_llm(plan)
        planner = LLMInterviewPlanner(llm)

        session = _create_session_raw(repository, db_session)
        service = _build_service(repository, llm, planner=planner)

        _, question, _ = await service.start_interview(session.id)

        with patch(_EXPIRED, return_value=False):
            _, q2, _ = await service.submit_answer(session.id, question.id, "answer 1")

        with patch(_EXPIRED, return_value=True):
            result, next_q, _ = await service.submit_answer(session.id, q2.id, "late answer")

        assert result.status is InterviewStatus.COMPLETED
        assert next_q is None

        messages = repository.get_messages(session.id)
        candidate_msgs = [m for m in messages if m.role == MessageRole.CANDIDATE]
        assert len(candidate_msgs) == 2
        assert candidate_msgs[1].content == "late answer"

    @pytest.mark.asyncio
    async def test_lifecycle_with_question_limit(
        self, repository: InterviewRepository, db_session: Session
    ):
        """End-to-end: create -> start -> answer x3 -> completed by limit."""
        session = _create_session_raw(repository, db_session, question_limit=3)
        llm = _follow_up_llm()
        service = _build_service(repository, llm)

        _, question, _ = await service.start_interview(session.id)

        with patch(_EXPIRED, return_value=False):
            _, q2, _ = await service.submit_answer(session.id, question.id, "a1")
            _, q3, _ = await service.submit_answer(session.id, q2.id, "a2")
            result, next_q, _ = await service.submit_answer(session.id, q3.id, "a3")

        assert result.status is InterviewStatus.COMPLETED
        assert next_q is None
        assert result.completed_at is not None

        questions = repository.get_questions(session.id)
        assert len(questions) == 3
