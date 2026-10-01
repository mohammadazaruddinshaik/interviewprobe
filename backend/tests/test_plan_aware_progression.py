"""Phase 3 Task 6 — Plan-aware adaptive topic progression verification.

Proves that personalized InterviewPlan topics correctly drive the existing
multi-turn adaptive interview lifecycle. All scenarios use in-memory SQLite
+ FakeLLMProvider: no live LLM, no live DB.

Key invariant tested: the runtime topic progression operates ONLY over the
materialized planned topics. The existing adaptive engine (decision
validator, topic progression service, question-limit enforcement) already
handles this because it operates on `interview_topics` rows — the plan
changes WHAT those rows contain, not HOW the engine processes them.
"""

import uuid

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from tests.plan_helpers import complete_plan, completed
from app.db.base import Base
from app.domain.enums import (
    Difficulty,
    InterviewStatus,
    InterviewTopic,
    InterviewTopicStatus,
    PlannedTopicPriority,
    QuestionType,
    ResumeRelevance,
    Role,
)
from app.models.interview_resume import InterviewResume
from app.models.interview_session import InterviewSession
from app.models.interview_topic import InterviewTopicEntry
from app.planning.models import (
    InterviewPlan,
    PlannedTopic,
    identify_resume_claims,
)
from app.planning.planner import LLMInterviewPlanner
from app.repositories.interview_repository import InterviewRepository
from app.resume.models import ResumeClaim, ResumeProfile
from app.services.interview_service import InterviewService
from app.workflows.interview.graph import InterviewWorkflow
from app.workflows.interview.models import AnswerAnalysis, GeneratedQuestion, NextAction
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
# Helpers
# ---------------------------------------------------------------------------

@completed
def _ai_plan(*topic_tuples) -> InterviewPlan:
    """Build an AI_ENGINEER plan from (topic, competency_key) tuples."""
    planned = []
    for topic, key in topic_tuples:
        planned.append(PlannedTopic(
            topic=topic,
            competency_keys=[key],
            priority=PlannedTopicPriority.HIGH,
            rationale="Test coverage.",
            suggested_time_budget_minutes=10,
        ))
    return InterviewPlan(
        role=Role.AI_ENGINEER,
        objectives=["Test objective."],
        planned_topics=planned,
    )


def _default_plan() -> InterviewPlan:
    return _ai_plan(
        (InterviewTopic.LLM_FUNDAMENTALS, "llm_fundamentals"),
        (InterviewTopic.RAG, "retrieval_augmented_generation"),
        (InterviewTopic.EMBEDDINGS_VECTOR_DB, "embeddings_vector_search"),
    )


def _make_llm(plan: InterviewPlan, *answer_actions) -> FakeLLMProvider:
    """Build a FakeLLMProvider that returns `plan` for planning, then
    cycles through `answer_actions` for each answer turn. Each action is
    a (action_str, topic_or_none, difficulty) tuple.

    The provider is stateful: each `generate_structured` call for
    `NextAction` pops the next configured action from the list.
    """
    action_queue = list(answer_actions)

    class SequentialFakeLLM(FakeLLMProvider):
        def __init__(self):
            super().__init__(structured_responses={
                "InterviewPlan": plan,
                "GeneratedQuestion": GeneratedQuestion(
                    question="Test question.",
                    topic=plan.planned_topics[0].topic,
                    difficulty=Difficulty.MEDIUM,
                    question_type=QuestionType.INITIAL,
                ),
                "AnswerAnalysis": AnswerAnalysis(
                    understanding="BASIC",
                    correctness=0.5,
                    depth=0.4,
                    concepts_demonstrated=[],
                    concepts_missing=[],
                    reasoning_quality="MODERATE",
                    needs_follow_up=True,
                ),
            })
            self._action_index = 0

        async def generate_structured(self, messages, output_schema):
            if output_schema.__name__ == "NextAction":
                if self._action_index < len(action_queue):
                    action_str, topic, difficulty = action_queue[self._action_index]
                    self._action_index += 1
                    from app.llm.models import StructuredLLMResponse
                    return StructuredLLMResponse(
                        data=NextAction(
                            action=action_str,
                            topic=topic,
                            difficulty=difficulty,
                            rationale="Test decision.",
                        ),
                        model="fake-model",
                    )
                from app.llm.models import StructuredLLMResponse
                return StructuredLLMResponse(
                    data=NextAction(
                        action="FOLLOW_UP",
                        topic=plan.planned_topics[0].topic,
                        difficulty=Difficulty.MEDIUM,
                        rationale="Default fallback in test.",
                    ),
                    model="fake-model",
                )
            if output_schema.__name__ == "GeneratedQuestion":
                from app.llm.models import StructuredLLMResponse
                return StructuredLLMResponse(
                    data=GeneratedQuestion(
                        question="Next test question.",
                        topic=plan.planned_topics[0].topic,
                        difficulty=Difficulty.MEDIUM,
                        question_type=QuestionType.FOLLOW_UP,
                    ),
                    model="fake-model",
                )
            return await super().generate_structured(messages, output_schema)

    return SequentialFakeLLM()


def _create_planned_session(
    repository: InterviewRepository,
    db_session: Session,
    plan: InterviewPlan,
    llm: FakeLLMProvider,
    question_limit: int = 5,
) -> tuple[InterviewService, InterviewSession]:
    """Create a CREATED session with placeholder topics, ready for planning."""
    session = InterviewSession(
        role=plan.role,
        difficulty=Difficulty.MEDIUM,
        status=InterviewStatus.CREATED,
        question_limit=question_limit,
        current_question_number=0,
        version=1,
    )
    repository.create_session(session)
    repository.create_topics([
        InterviewTopicEntry(
            session_id=session.id,
            topic=plan.planned_topics[0].topic,
            sequence_number=1,
            status=InterviewTopicStatus.PENDING,
        ),
    ])
    db_session.commit()

    planner = LLMInterviewPlanner(llm)
    workflow = InterviewWorkflow(repository=repository, llm_provider=llm)
    service = InterviewService(repository, workflow, planner=planner)
    return service, session


async def _start_and_get_question(service, session_id):
    """Start interview and return (session, question_id)."""
    session, question, _ = await service.start_interview(session_id)
    return session, question.id


async def _answer(service, session_id, question_id, answer="test answer"):
    """Submit an answer, return (session, next_question, lead_in)."""
    return await service.submit_answer(session_id, question_id, answer)


# ===================================================================
# Scenario A — Same-topic DEEP_DIVE
# ===================================================================


class TestSameTopicDepthScenarioA:
    @pytest.mark.asyncio
    async def test_deep_dive_preserves_current_topic(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _default_plan()
        llm = _make_llm(plan,
            ("DEEP_DIVE", InterviewTopic.LLM_FUNDAMENTALS, Difficulty.MEDIUM),
        )
        service, session = _create_planned_session(repository, db_session, plan, llm)

        session, q1_id = await _start_and_get_question(service, session.id)
        session, q2, _ = await _answer(service, session.id, q1_id)

        topics = repository.get_topics(session.id)
        current = [t for t in topics if t.status == InterviewTopicStatus.IN_PROGRESS]
        assert len(current) == 1
        assert current[0].topic is InterviewTopic.LLM_FUNDAMENTALS
        assert q2.topic is InterviewTopic.LLM_FUNDAMENTALS


# ===================================================================
# Scenario B — Clarification
# ===================================================================


class TestClarificationScenarioB:
    @pytest.mark.asyncio
    async def test_clarify_preserves_current_topic(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _default_plan()
        llm = _make_llm(plan,
            ("CLARIFY", InterviewTopic.LLM_FUNDAMENTALS, Difficulty.MEDIUM),
        )
        service, session = _create_planned_session(repository, db_session, plan, llm)

        session, q1_id = await _start_and_get_question(service, session.id)
        session, q2, _ = await _answer(service, session.id, q1_id)

        topics = repository.get_topics(session.id)
        current = [t for t in topics if t.status == InterviewTopicStatus.IN_PROGRESS]
        assert len(current) == 1
        assert current[0].topic is InterviewTopic.LLM_FUNDAMENTALS
        assert q2.topic is InterviewTopic.LLM_FUNDAMENTALS


# ===================================================================
# Scenario C — Challenge
# ===================================================================


class TestChallengeScenarioC:
    @pytest.mark.asyncio
    async def test_challenge_preserves_current_topic(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _default_plan()
        llm = _make_llm(plan,
            ("CHALLENGE", InterviewTopic.LLM_FUNDAMENTALS, Difficulty.HARD),
        )
        service, session = _create_planned_session(repository, db_session, plan, llm)

        session, q1_id = await _start_and_get_question(service, session.id)
        session, q2, _ = await _answer(service, session.id, q1_id)

        topics = repository.get_topics(session.id)
        current = [t for t in topics if t.status == InterviewTopicStatus.IN_PROGRESS]
        assert len(current) == 1
        assert current[0].topic is InterviewTopic.LLM_FUNDAMENTALS


# ===================================================================
# Scenario D — Follow-up
# ===================================================================


class TestFollowUpScenarioD:
    @pytest.mark.asyncio
    async def test_follow_up_preserves_current_topic(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _default_plan()
        llm = _make_llm(plan,
            ("FOLLOW_UP", InterviewTopic.LLM_FUNDAMENTALS, Difficulty.MEDIUM),
        )
        service, session = _create_planned_session(repository, db_session, plan, llm)

        session, q1_id = await _start_and_get_question(service, session.id)
        session, q2, _ = await _answer(service, session.id, q1_id)

        topics = repository.get_topics(session.id)
        current = [t for t in topics if t.status == InterviewTopicStatus.IN_PROGRESS]
        assert len(current) == 1
        assert current[0].topic is InterviewTopic.LLM_FUNDAMENTALS


# ===================================================================
# Scenario E — New topic progression
# ===================================================================


class TestNewTopicScenarioE:
    @pytest.mark.asyncio
    async def test_new_topic_transitions_correctly(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _default_plan()
        llm = _make_llm(plan,
            ("NEW_TOPIC", InterviewTopic.RAG, Difficulty.MEDIUM),
        )
        service, session = _create_planned_session(repository, db_session, plan, llm)

        session, q1_id = await _start_and_get_question(service, session.id)
        session, q2, _ = await _answer(service, session.id, q1_id)

        topics = repository.get_topics(session.id)
        statuses = {t.topic: t.status for t in topics}
        assert statuses[InterviewTopic.LLM_FUNDAMENTALS] == InterviewTopicStatus.COMPLETED
        assert statuses[InterviewTopic.RAG] == InterviewTopicStatus.IN_PROGRESS
        assert statuses[InterviewTopic.EMBEDDINGS_VECTOR_DB] == InterviewTopicStatus.PENDING

    @pytest.mark.asyncio
    async def test_sequential_new_topic_transitions(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _default_plan()
        llm = _make_llm(plan,
            ("NEW_TOPIC", InterviewTopic.RAG, Difficulty.MEDIUM),
            ("NEW_TOPIC", InterviewTopic.EMBEDDINGS_VECTOR_DB, Difficulty.MEDIUM),
        )
        service, session = _create_planned_session(repository, db_session, plan, llm)

        session, q1_id = await _start_and_get_question(service, session.id)
        session, q2, _ = await _answer(service, session.id, q1_id)
        session, q3, _ = await _answer(service, session.id, q2.id)

        topics = repository.get_topics(session.id)
        statuses = {t.topic: t.status for t in topics}
        assert statuses[InterviewTopic.LLM_FUNDAMENTALS] == InterviewTopicStatus.COMPLETED
        assert statuses[InterviewTopic.RAG] == InterviewTopicStatus.COMPLETED
        assert statuses[InterviewTopic.EMBEDDINGS_VECTOR_DB] == InterviewTopicStatus.IN_PROGRESS


# ===================================================================
# Scenario F — Invalid topic attempt
# ===================================================================


class TestInvalidTopicScenarioF:
    @pytest.mark.asyncio
    async def test_topic_not_in_plan_gets_rejected(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _default_plan()
        # LLM proposes AI_AGENTS, which is in the role catalog but NOT in our plan
        llm = _make_llm(plan,
            ("NEW_TOPIC", InterviewTopic.AI_AGENTS, Difficulty.MEDIUM),
        )
        service, session = _create_planned_session(repository, db_session, plan, llm)

        session, q1_id = await _start_and_get_question(service, session.id)
        session, q2, _ = await _answer(service, session.id, q1_id)

        topics = repository.get_topics(session.id)
        topic_enums = [t.topic for t in topics]
        assert InterviewTopic.AI_AGENTS not in topic_enums
        # The validator should have fallen back (FOLLOW_UP on current topic
        # or NEW_TOPIC to a valid pending topic).
        assert q2 is not None

    @pytest.mark.asyncio
    async def test_completed_topic_cannot_be_revisited(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _default_plan()
        llm = _make_llm(plan,
            ("NEW_TOPIC", InterviewTopic.RAG, Difficulty.MEDIUM),
            # Try to go BACK to LLM_FUNDAMENTALS (now COMPLETED)
            ("NEW_TOPIC", InterviewTopic.LLM_FUNDAMENTALS, Difficulty.MEDIUM),
        )
        service, session = _create_planned_session(repository, db_session, plan, llm)

        session, q1_id = await _start_and_get_question(service, session.id)
        session, q2, _ = await _answer(service, session.id, q1_id)
        session, q3, _ = await _answer(service, session.id, q2.id)

        # LLM_FUNDAMENTALS should stay COMPLETED, not become IN_PROGRESS again
        topics = repository.get_topics(session.id)
        statuses = {t.topic: t.status for t in topics}
        assert statuses[InterviewTopic.LLM_FUNDAMENTALS] == InterviewTopicStatus.COMPLETED


# ===================================================================
# Scenario G — Question limit
# ===================================================================


class TestQuestionLimitScenarioG:
    @pytest.mark.asyncio
    async def test_question_limit_forces_end(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _default_plan()
        llm = _make_llm(plan,
            ("FOLLOW_UP", InterviewTopic.LLM_FUNDAMENTALS, Difficulty.MEDIUM),
            ("FOLLOW_UP", InterviewTopic.LLM_FUNDAMENTALS, Difficulty.MEDIUM),
            ("FOLLOW_UP", InterviewTopic.LLM_FUNDAMENTALS, Difficulty.MEDIUM),
        )
        # The planner's max_questions is the session's question_limit once started.
        # 5 is the smallest ceiling that covers this plan's five planned topics:
        # Q1 (start), Q2..Q5 (ans 1-4), END (ans 5)
        plan = complete_plan(plan, max_questions=5)
        llm = _make_llm(plan, *[("FOLLOW_UP", InterviewTopic.LLM_FUNDAMENTALS, Difficulty.MEDIUM)] * 5)
        service, session = _create_planned_session(repository, db_session, plan, llm)

        session, q1_id = await _start_and_get_question(service, session.id)
        session, q2, _ = await _answer(service, session.id, q1_id)
        session, q3, _ = await _answer(service, session.id, q2.id)
        session, q4, _ = await _answer(service, session.id, q3.id)
        session, q5, _ = await _answer(service, session.id, q4.id)
        session, q4, _ = await _answer(service, session.id, q5.id)

        # After answering Q5 (the limit), interview completes — even
        # though RAG and EMBEDDINGS topics were never visited.
        assert session.status is InterviewStatus.COMPLETED
        assert q4 is None

        # Plan remains intact with unvisited topics
        topics = repository.get_topics(session.id)
        pending = [t for t in topics if t.status == InterviewTopicStatus.PENDING]
        assert len(pending) >= 1


# ===================================================================
# Scenario H — Resume-aware plan progression
# ===================================================================


class TestResumeAwarePlanScenarioH:
    @pytest.mark.asyncio
    async def test_resume_linked_topic_progresses_normally(
        self, repository: InterviewRepository, db_session: Session
    ):
        claim = ResumeClaim(claim="Built RAG with Qdrant", category="project", source="Projects")
        claims = identify_resume_claims([claim])
        plan = complete_plan(InterviewPlan(
            role=Role.AI_ENGINEER,
            objectives=["Probe RAG experience."],
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
        ))
        llm = _make_llm(plan,
            ("NEW_TOPIC", InterviewTopic.LLM_FUNDAMENTALS, Difficulty.MEDIUM),
        )
        service, session = _create_planned_session(repository, db_session, plan, llm)

        # Add resume
        profile = ResumeProfile(
            summary="AI engineer.",
            claims=[claim],
        )
        resume = InterviewResume(
            session_id=session.id,
            original_filename="resume.pdf",
            content_type="application/pdf",
            file_size=1024,
            extraction_status="READY",
            structured_profile=profile.model_dump(mode="json"),
        )
        repository.create_resume(resume)
        db_session.commit()

        session, q1_id = await _start_and_get_question(service, session.id)
        session, q2, _ = await _answer(service, session.id, q1_id)

        # Plan stays intact — claim IDs not mutated
        loaded_plan = repository.load_plan(session.id)
        assert loaded_plan is not None
        rag_topic = next(t for t in loaded_plan.planned_topics if t.topic == InterviewTopic.RAG)
        assert len(rag_topic.related_claim_ids) == 1
        assert rag_topic.related_claim_ids[0].startswith("claim_")


# ===================================================================
# Scenario I — Legacy session (no plan)
# ===================================================================


class TestLegacySessionScenarioI:
    @pytest.mark.asyncio
    async def test_legacy_session_without_plan_works(
        self, repository: InterviewRepository, db_session: Session
    ):
        llm = FakeLLMProvider(
            structured_responses={
                "GeneratedQuestion": GeneratedQuestion(
                    question="Explain RAG.",
                    topic=InterviewTopic.RAG,
                    difficulty=Difficulty.MEDIUM,
                    question_type=QuestionType.INITIAL,
                ),
                "AnswerAnalysis": AnswerAnalysis(
                    understanding="BASIC",
                    correctness=0.5,
                    depth=0.4,
                    concepts_demonstrated=[],
                    concepts_missing=[],
                    reasoning_quality="MODERATE",
                    needs_follow_up=True,
                ),
                "NextAction": NextAction(
                    action="FOLLOW_UP",
                    topic=InterviewTopic.RAG,
                    difficulty=Difficulty.MEDIUM,
                    rationale="Continue probing.",
                ),
            }
        )
        session = InterviewSession(
            role=Role.AI_ENGINEER,
            difficulty=Difficulty.MEDIUM,
            status=InterviewStatus.CREATED,
            question_limit=5,
            current_question_number=0,
            version=1,
        )
        repository.create_session(session)
        repository.create_topics([
            InterviewTopicEntry(
                session_id=session.id,
                topic=InterviewTopic.RAG,
                sequence_number=1,
                status=InterviewTopicStatus.PENDING,
            ),
        ])
        db_session.commit()

        workflow = InterviewWorkflow(repository=repository, llm_provider=llm)
        service = InterviewService(repository, workflow, planner=None)

        session, q1_id = await _start_and_get_question(service, session.id)
        session, q2, _ = await _answer(service, session.id, q1_id)

        assert repository.load_plan(session.id) is None
        assert q2.topic is InterviewTopic.RAG
        assert session.status is InterviewStatus.IN_PROGRESS


# ===================================================================
# Scenario J — Reload/resume
# ===================================================================


class TestReloadResumeScenarioJ:
    @pytest.mark.asyncio
    async def test_recreated_service_continues_without_replanning(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _default_plan()
        llm = _make_llm(plan,
            ("FOLLOW_UP", InterviewTopic.LLM_FUNDAMENTALS, Difficulty.MEDIUM),
        )
        service, session = _create_planned_session(repository, db_session, plan, llm)

        session, q1_id = await _start_and_get_question(service, session.id)
        plan_calls_after_start = sum(1 for c in llm.calls if c[0] == "InterviewPlan")

        # Simulate service recreation (new request context)
        workflow2 = InterviewWorkflow(repository=repository, llm_provider=llm)
        service2 = InterviewService(repository, workflow2, planner=LLMInterviewPlanner(llm))

        session, q2, _ = await service2.submit_answer(session.id, q1_id, "answer")

        plan_calls_after_answer = sum(1 for c in llm.calls if c[0] == "InterviewPlan")
        assert plan_calls_after_answer == plan_calls_after_start

        topics = repository.get_topics(session.id)
        assert len(topics) == len(plan.planned_topics)
        assert topics[0].topic is InterviewTopic.LLM_FUNDAMENTALS


# ===================================================================
# Planner never called during answers
# ===================================================================


class TestPlannerNotCalledDuringAnswers:
    @pytest.mark.asyncio
    async def test_planner_call_count_unchanged_across_answers(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _default_plan()
        llm = _make_llm(plan,
            ("FOLLOW_UP", InterviewTopic.LLM_FUNDAMENTALS, Difficulty.MEDIUM),
            ("NEW_TOPIC", InterviewTopic.RAG, Difficulty.MEDIUM),
            ("FOLLOW_UP", InterviewTopic.RAG, Difficulty.MEDIUM),
        )
        service, session = _create_planned_session(
            repository, db_session, plan, llm, question_limit=5,
        )

        session, q1_id = await _start_and_get_question(service, session.id)
        plan_calls = sum(1 for c in llm.calls if c[0] == "InterviewPlan")

        session, q2, _ = await _answer(service, session.id, q1_id)
        session, q3, _ = await _answer(service, session.id, q2.id)
        session, q4, _ = await _answer(service, session.id, q3.id)

        plan_calls_after = sum(1 for c in llm.calls if c[0] == "InterviewPlan")
        assert plan_calls_after == plan_calls


# ===================================================================
# Plan not mutated during answers
# ===================================================================


class TestPlanNotMutated:
    @pytest.mark.asyncio
    async def test_plan_unchanged_after_multiple_answers(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _default_plan()
        llm = _make_llm(plan,
            ("NEW_TOPIC", InterviewTopic.RAG, Difficulty.MEDIUM),
            ("NEW_TOPIC", InterviewTopic.EMBEDDINGS_VECTOR_DB, Difficulty.MEDIUM),
        )
        service, session = _create_planned_session(repository, db_session, plan, llm)

        session, q1_id = await _start_and_get_question(service, session.id)
        plan_before = repository.load_plan(session.id)

        session, q2, _ = await _answer(service, session.id, q1_id)
        session, q3, _ = await _answer(service, session.id, q2.id)

        plan_after = repository.load_plan(session.id)
        assert plan_after == plan_before
        assert plan_after.plan_version == 1

        # No extra plan records created
        record = repository.get_plan(session.id)
        assert record.plan_version == 1


# ===================================================================
# END behavior
# ===================================================================


class TestEndBehavior:
    @pytest.mark.asyncio
    async def test_end_does_not_generate_question(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _default_plan()
        llm = _make_llm(plan,
            ("END", None, Difficulty.MEDIUM),
        )
        service, session = _create_planned_session(repository, db_session, plan, llm)

        session, q1_id = await _start_and_get_question(service, session.id)
        session, next_q, _ = await _answer(service, session.id, q1_id)

        assert next_q is None
        assert session.status is InterviewStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_end_does_not_mutate_plan(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _default_plan()
        llm = _make_llm(plan,
            ("END", None, Difficulty.MEDIUM),
        )
        service, session = _create_planned_session(repository, db_session, plan, llm)

        session, q1_id = await _start_and_get_question(service, session.id)
        plan_before = repository.load_plan(session.id)

        await _answer(service, session.id, q1_id)

        plan_after = repository.load_plan(session.id)
        assert plan_after == plan_before

    @pytest.mark.asyncio
    async def test_end_allows_unvisited_planned_topics(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _default_plan()
        llm = _make_llm(plan,
            ("END", None, Difficulty.MEDIUM),
        )
        service, session = _create_planned_session(repository, db_session, plan, llm)

        session, q1_id = await _start_and_get_question(service, session.id)
        await _answer(service, session.id, q1_id)

        topics = repository.get_topics(session.id)
        pending = [t for t in topics if t.status == InterviewTopicStatus.PENDING]
        assert len(pending) == len(plan.planned_topics) - 1


# ===================================================================
# Resume-free plan progression
# ===================================================================


class TestResumeFreeProgression:
    @pytest.mark.asyncio
    async def test_resume_free_plan_full_progression(
        self, repository: InterviewRepository, db_session: Session
    ):
        plan = _ai_plan(
            (InterviewTopic.LLM_FUNDAMENTALS, "llm_fundamentals"),
            (InterviewTopic.RAG, "retrieval_augmented_generation"),
        )
        llm = _make_llm(plan,
            ("NEW_TOPIC", InterviewTopic.RAG, Difficulty.MEDIUM),
        )
        service, session = _create_planned_session(repository, db_session, plan, llm)

        session, q1_id = await _start_and_get_question(service, session.id)
        session, q2, _ = await _answer(service, session.id, q1_id)

        topics = repository.get_topics(session.id)
        statuses = {t.topic: t.status for t in topics}
        assert statuses[InterviewTopic.LLM_FUNDAMENTALS] == InterviewTopicStatus.COMPLETED
        assert statuses[InterviewTopic.RAG] == InterviewTopicStatus.IN_PROGRESS
