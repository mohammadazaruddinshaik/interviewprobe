"""Integration tests: interview planning wired into the interview START lifecycle.

Verifies that `InterviewService.start_interview` correctly:
- generates and persists a plan when a planner is configured
- materializes planned topics into `interview_topics`
- handles resume-free, resume-aware, and failed-resume cases
- reuses an existing plan (idempotency)
- rolls back on planner failure (no partial state)
- is backward compatible when no planner is configured

Uses the same in-memory SQLite / FakeLLMProvider strategy as
test_interview_service.py — no live LLM, no live DB.
"""

import uuid

import pytest
from sqlalchemy import create_engine, event
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
    PlannedTopicPriority,
    QuestionType,
    ResumeExtractionStatus,
    ResumeRelevance,
    Role,
)
from app.models.interview_resume import InterviewResume
from app.models.interview_session import InterviewSession
from app.models.interview_topic import InterviewTopicEntry
from app.planning.models import (
    InterviewPlan,
    PlannedTopic,
    build_planning_input,
    identify_resume_claims,
)
from app.planning.planner import InterviewPlanner, LLMInterviewPlanner
from app.planning.validator import InvalidInterviewPlanError
from app.repositories.interview_repository import InterviewRepository
from app.resume.models import ResumeClaim, ResumeProfile
from app.services.interview_service import InterviewService, InvalidInterviewStateError
from app.workflows.interview.graph import InterviewWorkflow
from app.workflows.interview.models import GeneratedQuestion
from tests.fakes import FakeLLMProvider


# ---------------------------------------------------------------------------
# SQLite dialect hooks
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


# ---------------------------------------------------------------------------
# Plan / LLM helpers
# ---------------------------------------------------------------------------

def _ai_plan() -> InterviewPlan:
    """A valid plan for AI_ENGINEER with two topics."""
    return InterviewPlan(
        role=Role.AI_ENGINEER,
        objectives=["Assess core AI engineering competency."],
        planned_topics=[
            PlannedTopic(
                topic=InterviewTopic.LLM_FUNDAMENTALS,
                competency_keys=["llm_fundamentals"],
                priority=PlannedTopicPriority.HIGH,
                rationale="Core LLM knowledge.",
                suggested_time_budget_minutes=15,
            ),
            PlannedTopic(
                topic=InterviewTopic.RAG,
                competency_keys=["retrieval_augmented_generation"],
                priority=PlannedTopicPriority.MEDIUM,
                rationale="Retrieval pipeline design.",
                suggested_time_budget_minutes=12,
            ),
        ],
    )


def _ai_plan_with_claims() -> InterviewPlan:
    """A plan that references resume claims."""
    claim = ResumeClaim(claim="Built RAG with Qdrant", category="project", source="Projects")
    claims = identify_resume_claims([claim])
    return InterviewPlan(
        role=Role.AI_ENGINEER,
        objectives=["Probe candidate's RAG experience."],
        planned_topics=[
            PlannedTopic(
                topic=InterviewTopic.RAG,
                competency_keys=["retrieval_augmented_generation"],
                priority=PlannedTopicPriority.HIGH,
                rationale="Candidate claims RAG experience.",
                resume_relevance=ResumeRelevance.PRIMARY,
                related_claim_ids=[c.claim_id for c in claims],
                suggested_time_budget_minutes=15,
            ),
            PlannedTopic(
                topic=InterviewTopic.LLM_FUNDAMENTALS,
                competency_keys=["llm_fundamentals"],
                priority=PlannedTopicPriority.MEDIUM,
                rationale="Baseline knowledge.",
                suggested_time_budget_minutes=10,
            ),
        ],
    )


def _backend_plan() -> InterviewPlan:
    """A valid plan for BACKEND_DEVELOPER."""
    return InterviewPlan(
        role=Role.BACKEND_DEVELOPER,
        objectives=["Assess backend engineering depth."],
        planned_topics=[
            PlannedTopic(
                topic=InterviewTopic.REST_APIS,
                competency_keys=["api_design"],
                priority=PlannedTopicPriority.HIGH,
                rationale="Core API design skills.",
                suggested_time_budget_minutes=15,
            ),
            PlannedTopic(
                topic=InterviewTopic.DATABASES,
                competency_keys=["data_modeling"],
                priority=PlannedTopicPriority.MEDIUM,
                rationale="Data modeling fundamentals.",
                suggested_time_budget_minutes=10,
            ),
        ],
    )


def _fake_llm(plan: InterviewPlan) -> FakeLLMProvider:
    """A FakeLLMProvider configured for both planning and initial question."""
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


def _fake_llm_question_only() -> FakeLLMProvider:
    """A FakeLLMProvider that only handles question generation (no planning)."""
    return FakeLLMProvider(
        structured_responses={
            "GeneratedQuestion": GeneratedQuestion(
                question="Explain RAG pipelines.",
                topic=InterviewTopic.RAG,
                difficulty=Difficulty.MEDIUM,
                question_type=QuestionType.INITIAL,
            ),
        }
    )


def _create_session(
    repository: InterviewRepository,
    db_session: Session,
    role: Role = Role.AI_ENGINEER,
    difficulty: Difficulty = Difficulty.MEDIUM,
    question_limit: int = 5,
    topics: list[InterviewTopic] | None = None,
) -> InterviewSession:
    """Create a CREATED session with topics, committed."""
    if topics is None:
        topics = [InterviewTopic.RAG]
    session = InterviewSession(
        role=role,
        difficulty=difficulty,
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
    status: ResumeExtractionStatus = ResumeExtractionStatus.READY,
    profile: ResumeProfile | None = None,
) -> InterviewResume:
    """Attach a resume to a session."""
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
) -> InterviewService:
    workflow = InterviewWorkflow(repository=repository, llm_provider=llm)
    return InterviewService(repository, workflow, planner=planner)


# ===================================================================
# Plan generation and persistence
# ===================================================================


class TestPlanGeneration:
    @pytest.mark.asyncio
    async def test_start_generates_plan_when_planner_configured(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _ai_plan()
        llm = _fake_llm(plan)
        planner = LLMInterviewPlanner(llm)
        session = _create_session(repository, db_session)
        service = _build_service(repository, llm, planner=planner)

        await service.start_interview(session.id)

        loaded = repository.load_plan(session.id)
        assert loaded is not None
        assert loaded.role is Role.AI_ENGINEER

    @pytest.mark.asyncio
    async def test_persisted_plan_matches_generated_plan(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _ai_plan()
        llm = _fake_llm(plan)
        planner = LLMInterviewPlanner(llm)
        session = _create_session(repository, db_session)
        service = _build_service(repository, llm, planner=planner)

        await service.start_interview(session.id)

        loaded = repository.load_plan(session.id)
        assert loaded == plan

    @pytest.mark.asyncio
    async def test_plan_version_is_1(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _ai_plan()
        llm = _fake_llm(plan)
        planner = LLMInterviewPlanner(llm)
        session = _create_session(repository, db_session)
        service = _build_service(repository, llm, planner=planner)

        await service.start_interview(session.id)

        record = repository.get_plan(session.id)
        assert record.plan_version == 1


# ===================================================================
# Topic materialization
# ===================================================================


class TestTopicMaterialization:
    @pytest.mark.asyncio
    async def test_plan_topics_replace_original_selection(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _ai_plan()
        llm = _fake_llm(plan)
        planner = LLMInterviewPlanner(llm)
        session = _create_session(
            repository, db_session,
            topics=[InterviewTopic.RAG],
        )
        service = _build_service(repository, llm, planner=planner)

        await service.start_interview(session.id)

        topics = repository.get_topics(session.id)
        topic_enums = [t.topic for t in topics]
        assert topic_enums == [InterviewTopic.LLM_FUNDAMENTALS, InterviewTopic.RAG]

    @pytest.mark.asyncio
    async def test_materialized_topics_preserve_plan_order(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _ai_plan()
        llm = _fake_llm(plan)
        planner = LLMInterviewPlanner(llm)
        session = _create_session(repository, db_session)
        service = _build_service(repository, llm, planner=planner)

        await service.start_interview(session.id)

        topics = repository.get_topics(session.id)
        assert topics[0].sequence_number == 1
        assert topics[1].sequence_number == 2
        assert topics[0].topic is InterviewTopic.LLM_FUNDAMENTALS
        assert topics[1].topic is InterviewTopic.RAG

    @pytest.mark.asyncio
    async def test_materialized_topics_start_as_pending(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _ai_plan()
        llm = _fake_llm(plan)
        planner = LLMInterviewPlanner(llm)
        session = _create_session(repository, db_session)
        service = _build_service(repository, llm, planner=planner)

        await service.start_interview(session.id)

        topics = repository.get_topics(session.id)
        # First topic should be IN_PROGRESS (after apply_initial_progression)
        assert topics[0].status is InterviewTopicStatus.IN_PROGRESS
        # Rest should remain PENDING
        assert topics[1].status is InterviewTopicStatus.PENDING

    @pytest.mark.asyncio
    async def test_first_question_uses_first_planned_topic(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _ai_plan()
        llm = _fake_llm(plan)
        planner = LLMInterviewPlanner(llm)
        session = _create_session(repository, db_session)
        service = _build_service(repository, llm, planner=planner)

        _, question, _ = await service.start_interview(session.id)

        assert question.topic is InterviewTopic.LLM_FUNDAMENTALS

    @pytest.mark.asyncio
    async def test_original_topics_are_removed(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _ai_plan()
        llm = _fake_llm(plan)
        planner = LLMInterviewPlanner(llm)
        session = _create_session(
            repository, db_session,
            topics=[InterviewTopic.AI_AGENTS, InterviewTopic.EMBEDDINGS_VECTOR_DB, InterviewTopic.RAG],
        )
        service = _build_service(repository, llm, planner=planner)

        await service.start_interview(session.id)

        topics = repository.get_topics(session.id)
        topic_enums = [t.topic for t in topics]
        # Plan only has LLM_FUNDAMENTALS and RAG — AI_AGENTS and EMBEDDINGS gone
        assert InterviewTopic.AI_AGENTS not in topic_enums
        assert InterviewTopic.EMBEDDINGS_VECTOR_DB not in topic_enums


# ===================================================================
# Resume handling
# ===================================================================


class TestResumeHandling:
    @pytest.mark.asyncio
    async def test_resume_free_plan_works(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _ai_plan()
        llm = _fake_llm(plan)
        planner = LLMInterviewPlanner(llm)
        session = _create_session(repository, db_session)
        service = _build_service(repository, llm, planner=planner)

        session_out, question, _ = await service.start_interview(session.id)

        assert session_out.status is InterviewStatus.IN_PROGRESS
        assert repository.load_plan(session.id) is not None

    @pytest.mark.asyncio
    async def test_resume_aware_plan_works(
        self, repository: InterviewRepository, db_session: Session
    ):
        profile = ResumeProfile(
            summary="AI engineer with RAG experience.",
            skills=["Python", "LLMs"],
            claims=[
                ResumeClaim(claim="Built RAG with Qdrant", category="project", source="Projects"),
            ],
        )
        plan = _ai_plan_with_claims()
        llm = _fake_llm(plan)
        planner = LLMInterviewPlanner(llm)
        session = _create_session(repository, db_session)
        _add_resume(repository, db_session, session.id, profile=profile)
        service = _build_service(repository, llm, planner=planner)

        session_out, question, _ = await service.start_interview(session.id)

        assert session_out.status is InterviewStatus.IN_PROGRESS
        loaded_plan = repository.load_plan(session.id)
        assert loaded_plan is not None
        rag_topic = next(t for t in loaded_plan.planned_topics if t.topic == InterviewTopic.RAG)
        assert rag_topic.resume_relevance is ResumeRelevance.PRIMARY

    @pytest.mark.asyncio
    async def test_failed_resume_treated_as_resume_free(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _ai_plan()
        llm = _fake_llm(plan)
        planner = LLMInterviewPlanner(llm)
        session = _create_session(repository, db_session)
        _add_resume(
            repository, db_session, session.id,
            status=ResumeExtractionStatus.FAILED,
        )
        service = _build_service(repository, llm, planner=planner)

        session_out, _, _ = await service.start_interview(session.id)

        assert session_out.status is InterviewStatus.IN_PROGRESS
        assert repository.load_plan(session.id) is not None

    @pytest.mark.asyncio
    async def test_uploaded_but_not_ready_resume_treated_as_resume_free(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _ai_plan()
        llm = _fake_llm(plan)
        planner = LLMInterviewPlanner(llm)
        session = _create_session(repository, db_session)
        _add_resume(
            repository, db_session, session.id,
            status=ResumeExtractionStatus.UPLOADED,
        )
        service = _build_service(repository, llm, planner=planner)

        session_out, _, _ = await service.start_interview(session.id)

        assert session_out.status is InterviewStatus.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_resume_claims_passed_to_planner(
        self, repository: InterviewRepository, db_session: Session
    ):
        profile = ResumeProfile(
            summary="AI engineer.",
            claims=[
                ResumeClaim(claim="Built RAG with Qdrant", category="project", source="Projects"),
            ],
        )
        plan = _ai_plan_with_claims()
        llm = _fake_llm(plan)
        planner = LLMInterviewPlanner(llm)
        session = _create_session(repository, db_session)
        _add_resume(repository, db_session, session.id, profile=profile)
        service = _build_service(repository, llm, planner=planner)

        await service.start_interview(session.id)

        # The planner was called — verify the LLM received the planning messages
        plan_calls = [c for c in llm.calls if c[0] == "InterviewPlan"]
        assert len(plan_calls) == 1


# ===================================================================
# Idempotency
# ===================================================================


class TestIdempotency:
    @pytest.mark.asyncio
    async def test_existing_plan_is_reused(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _ai_plan()
        llm = _fake_llm(plan)
        planner = LLMInterviewPlanner(llm)
        session = _create_session(repository, db_session)
        service = _build_service(repository, llm, planner=planner)

        # Pre-persist a plan
        repository.create_plan(session.id, plan)
        db_session.commit()

        # Replace topics to match plan (simulating a prior partial start)
        repository.delete_topics(session.id)
        repository.create_topics([
            InterviewTopicEntry(
                session_id=session.id,
                topic=InterviewTopic.LLM_FUNDAMENTALS,
                sequence_number=1,
                status=InterviewTopicStatus.PENDING,
            ),
            InterviewTopicEntry(
                session_id=session.id,
                topic=InterviewTopic.RAG,
                sequence_number=2,
                status=InterviewTopicStatus.PENDING,
            ),
        ])
        db_session.commit()

        await service.start_interview(session.id)

        # The planner should NOT have been called again
        plan_calls = [c for c in llm.calls if c[0] == "InterviewPlan"]
        assert len(plan_calls) == 0

    @pytest.mark.asyncio
    async def test_second_start_fails_after_successful_start(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _ai_plan()
        llm = _fake_llm(plan)
        planner = LLMInterviewPlanner(llm)
        session = _create_session(repository, db_session)
        service = _build_service(repository, llm, planner=planner)

        await service.start_interview(session.id)

        with pytest.raises(InvalidInterviewStateError):
            await service.start_interview(session.id)


# ===================================================================
# Planner failure and rollback
# ===================================================================


class TestPlannerFailure:
    @pytest.mark.asyncio
    async def test_planner_failure_rolls_back_entire_start(
        self, repository: InterviewRepository, db_session: Session
    ):
        failing_llm = FakeLLMProvider(error=RuntimeError("LLM unavailable"))
        planner = LLMInterviewPlanner(failing_llm)
        question_llm = _fake_llm_question_only()
        session = _create_session(repository, db_session)
        service = _build_service(repository, question_llm, planner=planner)

        with pytest.raises(RuntimeError, match="LLM unavailable"):
            await service.start_interview(session.id)

        # Session must remain CREATED
        reloaded = repository.get_session(session.id)
        assert reloaded.status is InterviewStatus.CREATED
        assert reloaded.current_question_number == 0

    @pytest.mark.asyncio
    async def test_planner_failure_leaves_no_plan(
        self, repository: InterviewRepository, db_session: Session
    ):
        failing_llm = FakeLLMProvider(error=RuntimeError("LLM unavailable"))
        planner = LLMInterviewPlanner(failing_llm)
        question_llm = _fake_llm_question_only()
        session = _create_session(repository, db_session)
        service = _build_service(repository, question_llm, planner=planner)

        with pytest.raises(RuntimeError):
            await service.start_interview(session.id)

        assert repository.load_plan(session.id) is None

    @pytest.mark.asyncio
    async def test_planner_failure_preserves_original_topics(
        self, repository: InterviewRepository, db_session: Session
    ):
        failing_llm = FakeLLMProvider(error=RuntimeError("LLM unavailable"))
        planner = LLMInterviewPlanner(failing_llm)
        question_llm = _fake_llm_question_only()
        session = _create_session(
            repository, db_session,
            topics=[InterviewTopic.RAG, InterviewTopic.LLM_FUNDAMENTALS],
        )
        service = _build_service(repository, question_llm, planner=planner)

        with pytest.raises(RuntimeError):
            await service.start_interview(session.id)

        topics = repository.get_topics(session.id)
        assert len(topics) == 2
        assert topics[0].topic is InterviewTopic.RAG
        assert topics[1].topic is InterviewTopic.LLM_FUNDAMENTALS

    @pytest.mark.asyncio
    async def test_validation_failure_rolls_back(
        self, repository: InterviewRepository, db_session: Session
    ):
        # A plan with wrong role — cross-object validation will fail
        bad_plan = InterviewPlan(
            role=Role.BACKEND_DEVELOPER,
            objectives=["Wrong role plan."],
            planned_topics=[
                PlannedTopic(
                    topic=InterviewTopic.REST_APIS,
                    competency_keys=["api_design"],
                    priority=PlannedTopicPriority.HIGH,
                    rationale="API design.",
                    suggested_time_budget_minutes=15,
                ),
            ],
        )
        llm = FakeLLMProvider(
            structured_responses={
                "InterviewPlan": bad_plan,
                "GeneratedQuestion": GeneratedQuestion(
                    question="Test",
                    topic=InterviewTopic.RAG,
                    difficulty=Difficulty.MEDIUM,
                    question_type=QuestionType.INITIAL,
                ),
            }
        )
        planner = LLMInterviewPlanner(llm)
        session = _create_session(repository, db_session, role=Role.AI_ENGINEER)
        service = _build_service(repository, llm, planner=planner)

        with pytest.raises(InvalidInterviewPlanError):
            await service.start_interview(session.id)

        assert repository.get_session(session.id).status is InterviewStatus.CREATED


# ===================================================================
# Backward compatibility (no planner)
# ===================================================================


class TestBackwardCompatibility:
    @pytest.mark.asyncio
    async def test_no_planner_uses_original_topics(
        self, repository: InterviewRepository, db_session: Session
    ):
        llm = _fake_llm_question_only()
        session = _create_session(
            repository, db_session,
            topics=[InterviewTopic.RAG],
        )
        service = _build_service(repository, llm, planner=None)

        _, question, _ = await service.start_interview(session.id)

        assert question.topic is InterviewTopic.RAG
        topics = repository.get_topics(session.id)
        assert len(topics) == 1
        assert topics[0].topic is InterviewTopic.RAG

    @pytest.mark.asyncio
    async def test_no_planner_creates_no_plan(
        self, repository: InterviewRepository, db_session: Session
    ):
        llm = _fake_llm_question_only()
        session = _create_session(repository, db_session)
        service = _build_service(repository, llm, planner=None)

        await service.start_interview(session.id)

        assert repository.load_plan(session.id) is None

    @pytest.mark.asyncio
    async def test_no_planner_transitions_to_in_progress(
        self, repository: InterviewRepository, db_session: Session
    ):
        llm = _fake_llm_question_only()
        session = _create_session(repository, db_session)
        service = _build_service(repository, llm, planner=None)

        session_out, _, _ = await service.start_interview(session.id)

        assert session_out.status is InterviewStatus.IN_PROGRESS


# ===================================================================
# Different roles
# ===================================================================


class TestMultipleRoles:
    @pytest.mark.asyncio
    async def test_backend_developer_plan(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _backend_plan()
        llm = _fake_llm(plan)
        planner = LLMInterviewPlanner(llm)
        session = _create_session(
            repository, db_session,
            role=Role.BACKEND_DEVELOPER,
            topics=[InterviewTopic.REST_APIS],
        )
        service = _build_service(repository, llm, planner=planner)

        session_out, question, _ = await service.start_interview(session.id)

        assert session_out.status is InterviewStatus.IN_PROGRESS
        topics = repository.get_topics(session.id)
        assert [t.topic for t in topics] == [InterviewTopic.REST_APIS, InterviewTopic.DATABASES]


# ===================================================================
# Session state after start with plan
# ===================================================================


class TestSessionState:
    @pytest.mark.asyncio
    async def test_session_transitions_to_in_progress(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _ai_plan()
        llm = _fake_llm(plan)
        planner = LLMInterviewPlanner(llm)
        session = _create_session(repository, db_session)
        service = _build_service(repository, llm, planner=planner)

        session_out, _, _ = await service.start_interview(session.id)

        assert session_out.status is InterviewStatus.IN_PROGRESS
        assert session_out.current_question_number == 1
        assert session_out.started_at is not None

    @pytest.mark.asyncio
    async def test_version_increments(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _ai_plan()
        llm = _fake_llm(plan)
        planner = LLMInterviewPlanner(llm)
        session = _create_session(repository, db_session)
        service = _build_service(repository, llm, planner=planner)

        session_out, _, _ = await service.start_interview(session.id)

        assert session_out.version == 2

    @pytest.mark.asyncio
    async def test_initial_question_is_created(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _ai_plan()
        llm = _fake_llm(plan)
        planner = LLMInterviewPlanner(llm)
        session = _create_session(repository, db_session)
        service = _build_service(repository, llm, planner=planner)

        _, question, _ = await service.start_interview(session.id)

        assert question.sequence_number == 1
        assert question.question_type is QuestionType.INITIAL
        assert question.question_text

    @pytest.mark.asyncio
    async def test_interviewer_message_is_created(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _ai_plan()
        llm = _fake_llm(plan)
        planner = LLMInterviewPlanner(llm)
        session = _create_session(repository, db_session)
        service = _build_service(repository, llm, planner=planner)

        await service.start_interview(session.id)

        messages = repository.get_messages(session.id)
        assert len(messages) == 1
        assert messages[0].role.value == "INTERVIEWER"

    @pytest.mark.asyncio
    async def test_lead_in_returned(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _ai_plan()
        llm = FakeLLMProvider(
            structured_responses={
                "InterviewPlan": plan,
                "GeneratedQuestion": GeneratedQuestion(
                    question="Tell me about LLMs.",
                    topic=InterviewTopic.LLM_FUNDAMENTALS,
                    difficulty=Difficulty.MEDIUM,
                    question_type=QuestionType.INITIAL,
                    lead_in="Let's start with the fundamentals.",
                ),
            }
        )
        planner = LLMInterviewPlanner(llm)
        session = _create_session(repository, db_session)
        service = _build_service(repository, llm, planner=planner)

        _, _, lead_in = await service.start_interview(session.id)

        assert lead_in == "Let's start with the fundamentals."


# ===================================================================
# Transaction correctness
# ===================================================================


class TestTransactionCorrectness:
    @pytest.mark.asyncio
    async def test_question_generation_failure_rolls_back_plan(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _ai_plan()
        # The LLM succeeds for planning but fails for question generation
        call_count = 0

        class PlanThenFailLLM(FakeLLMProvider):
            async def generate_structured(self, messages, output_schema):
                nonlocal call_count
                call_count += 1
                if output_schema.__name__ == "InterviewPlan":
                    return await super().generate_structured(messages, output_schema)
                raise RuntimeError("Question generation failed")

        llm = PlanThenFailLLM(structured_responses={"InterviewPlan": plan})
        planner = LLMInterviewPlanner(llm)
        service = _build_service(repository, llm, planner=planner)
        session = _create_session(repository, db_session)

        with pytest.raises(RuntimeError, match="Question generation failed"):
            await service.start_interview(session.id)

        # Plan should be rolled back since the whole transaction failed
        assert repository.load_plan(session.id) is None
        # Session should remain CREATED
        assert repository.get_session(session.id).status is InterviewStatus.CREATED

    @pytest.mark.asyncio
    async def test_successful_start_commits_plan_and_session(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _ai_plan()
        llm = _fake_llm(plan)
        planner = LLMInterviewPlanner(llm)
        session = _create_session(repository, db_session)
        service = _build_service(repository, llm, planner=planner)

        await service.start_interview(session.id)

        # Both plan and session state should be committed together
        assert repository.load_plan(session.id) is not None
        assert repository.get_session(session.id).status is InterviewStatus.IN_PROGRESS
