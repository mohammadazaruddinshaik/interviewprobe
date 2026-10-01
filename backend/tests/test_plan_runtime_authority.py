"""Task B3 — InterviewPlan is the runtime authority at interview start.

`start_interview` copies the validated plan's `starting_difficulty` / `max_questions` into the session's
`difficulty` / `question_limit` BEFORE the first question or any runtime state reads them. The workflow, the decision
validator, `submit_answer` and Redis keep reading the session — never the plan. In-memory SQLite + fake LLM/Redis."""

import pytest

from app.domain.enums import Difficulty, InterviewStatus, InterviewTopic, PlannedTopicPriority, Role
from app.models.interview_session import InterviewSession
from app.planning.models import InterviewPlan, PlannedTopic
from app.planning.planner import LLMInterviewPlanner
from app.redis.keys import InterviewRedisKeys
from app.redis.runtime_state_service import RuntimeStateService
from app.domain.enums import QuestionType
from app.services.interview_service import PLACEHOLDER_DIFFICULTY, PLACEHOLDER_QUESTION_LIMIT, InterviewService
from app.workflows.interview.graph import InterviewWorkflow
from app.workflows.interview.models import GeneratedQuestion
from tests.fakes import FakeAsyncRedis, FakeLLMProvider
from tests.plan_helpers import complete_plan

# Reuse the SQLite fixtures (and dialect hooks) of the plan-aware progression tests.
from tests.test_plan_aware_progression import db_session, repository, session_factory  # noqa: F401

_TOPICS = (
    (InterviewTopic.LLM_FUNDAMENTALS, "llm_fundamentals"),
    (InterviewTopic.RAG, "retrieval_augmented_generation"),
    (InterviewTopic.EMBEDDINGS_VECTOR_DB, "embeddings_vector_search"),
)


def _plan(difficulty=Difficulty.HARD, max_questions=8) -> InterviewPlan:
    raw = InterviewPlan(
        role=Role.AI_ENGINEER,
        objectives=["Test objective."],
        planned_topics=[
            PlannedTopic(
                topic=t,
                competency_keys=[k],
                priority=PlannedTopicPriority.HIGH,
                rationale="Test coverage.",
                suggested_time_budget_minutes=10,
            )
            for t, k in _TOPICS
        ],
    )
    return complete_plan(raw, starting_difficulty=difficulty, max_questions=max_questions)


def _llm(plan: InterviewPlan | None = None, error: Exception | None = None) -> FakeLLMProvider:
    responses = {
        "GeneratedQuestion": GeneratedQuestion(
            question="First question?",
            topic=InterviewTopic.LLM_FUNDAMENTALS,
            difficulty=Difficulty.MEDIUM,
            question_type=QuestionType.INITIAL,
        )
    }
    if plan is not None:
        responses["InterviewPlan"] = plan
    return FakeLLMProvider(structured_responses=responses, error=error)


def _created(repository, db_session) -> InterviewSession:
    session = InterviewSession(
        role=Role.AI_ENGINEER,
        difficulty=PLACEHOLDER_DIFFICULTY,
        status=InterviewStatus.CREATED,
        question_limit=PLACEHOLDER_QUESTION_LIMIT,
        current_question_number=0,
        version=1,
    )
    repository.create_session(session)
    db_session.commit()
    return session


def _service(repository, llm) -> InterviewService:
    workflow = InterviewWorkflow(repository=repository, llm_provider=llm)
    return InterviewService(repository, workflow, planner=LLMInterviewPlanner(llm))


def _calls(llm, schema):
    return [messages for name, messages in llm.calls if name == schema]


def _assert_untouched(repository, db_session, session):
    db_session.expire_all()
    assert session.status is InterviewStatus.CREATED
    assert session.difficulty is PLACEHOLDER_DIFFICULTY
    assert session.question_limit == PLACEHOLDER_QUESTION_LIMIT
    assert repository.get_topics(session.id) == []
    assert repository.get_questions(session.id) == []


def test_placeholders_differ_from_test_plan():
    # Guards the regressions below: the plan's values must be distinguishable from the placeholders.
    assert PLACEHOLDER_DIFFICULTY is Difficulty.MEDIUM and PLACEHOLDER_QUESTION_LIMIT == 5


@pytest.mark.asyncio
async def test_fresh_plan_sets_session_runtime_values_and_first_question_uses_them(repository, db_session):
    llm = _llm(_plan(Difficulty.HARD, 8))
    session = _created(repository, db_session)

    started, question, _ = await _service(repository, llm).start_interview(session.id)

    assert started.difficulty is Difficulty.HARD
    assert started.question_limit == 8
    assert question.difficulty is Difficulty.HARD
    # The first-question generation prompt itself saw HARD, not the MEDIUM placeholder.
    (prompt,) = _calls(llm, "GeneratedQuestion")
    text = "\n".join(m.content for m in prompt)
    assert "Difficulty: HARD" in text
    assert "Difficulty: MEDIUM" not in text
    db_session.expire_all()
    assert repository.get_session(session.id).question_limit == 8


@pytest.mark.asyncio
async def test_plan_topics_are_materialized_in_order(repository, db_session):
    plan = _plan()
    session = _created(repository, db_session)
    assert repository.get_topics(session.id) == []

    await _service(repository, _llm(plan)).start_interview(session.id)

    topics = repository.get_topics(session.id)
    assert [t.topic for t in topics] == [p.topic for p in plan.planned_topics]
    assert [t.sequence_number for t in topics] == list(range(1, len(topics) + 1))
    assert topics[0].status.value == "IN_PROGRESS"


@pytest.mark.asyncio
async def test_existing_plan_wins_over_placeholders_and_is_not_regenerated(repository, db_session):
    plan = _plan(Difficulty.EASY, 6)
    session = _created(repository, db_session)
    repository.create_plan(session.id, plan)
    # A topic selection materialized by the earlier attempt.
    llm = _llm(plan=None)  # no InterviewPlan response: regenerating would fail
    service = _service(repository, llm)
    service._materialize_plan_topics(session, plan)
    db_session.commit()

    started, question, _ = await service.start_interview(session.id)

    assert started.difficulty is Difficulty.EASY
    assert started.question_limit == 6
    assert question.difficulty is Difficulty.EASY
    assert _calls(llm, "InterviewPlan") == []
    assert len(repository.get_topics(session.id)) == len(plan.planned_topics)


@pytest.mark.asyncio
async def test_legacy_plan_without_decisions_is_regenerated(repository, db_session):
    fresh = _plan(Difficulty.HARD, 7)
    legacy = InterviewPlan(
        role=fresh.role, objectives=fresh.objectives, planned_topics=fresh.planned_topics
    )
    assert legacy.starting_difficulty is None and legacy.max_questions is None
    session = _created(repository, db_session)
    repository.create_plan(session.id, legacy)
    db_session.commit()
    llm = _llm(fresh)

    started, _, _ = await _service(repository, llm).start_interview(session.id)

    assert len(_calls(llm, "InterviewPlan")) == 1
    assert (started.difficulty, started.question_limit) == (Difficulty.HARD, 7)
    stored = repository.load_plan(session.id)
    assert (stored.starting_difficulty, stored.max_questions) == (Difficulty.HARD, 7)


@pytest.mark.asyncio
async def test_planner_failure_leaves_session_untouched(repository, db_session):
    session = _created(repository, db_session)
    service = _service(repository, _llm(error=RuntimeError("llm down")))

    with pytest.raises(Exception):
        await service.start_interview(session.id)

    _assert_untouched(repository, db_session, session)
    assert repository.load_plan(session.id) is None


@pytest.mark.asyncio
async def test_invalid_plan_leaves_session_untouched(repository, db_session):
    good = _plan()
    invalid = good.model_copy(update={"max_questions": None})
    session = _created(repository, db_session)
    service = _service(repository, _llm(invalid))

    with pytest.raises(Exception):
        await service.start_interview(session.id)

    _assert_untouched(repository, db_session, session)
    assert repository.load_plan(session.id) is None


@pytest.mark.asyncio
async def test_first_question_failure_rolls_back_plan_values_then_retry_succeeds(repository, db_session):
    plan = _plan(Difficulty.HARD, 8)
    session = _created(repository, db_session)
    failing = _llm(plan)
    failing._structured_responses.pop("GeneratedQuestion")  # first-question generation raises

    with pytest.raises(Exception):
        await _service(repository, failing).start_interview(session.id)
    _assert_untouched(repository, db_session, session)

    started, _, _ = await _service(repository, _llm(plan)).start_interview(session.id)
    assert (started.difficulty, started.question_limit) == (Difficulty.HARD, 8)


@pytest.mark.asyncio
async def test_repeated_start_is_rejected_without_changing_anything(repository, db_session):
    session = _created(repository, db_session)
    llm = _llm(_plan(Difficulty.HARD, 8))
    service = _service(repository, llm)
    await service.start_interview(session.id)

    with pytest.raises(Exception):
        await service.start_interview(session.id)

    db_session.expire_all()
    assert (session.difficulty, session.question_limit) == (Difficulty.HARD, 8)
    assert len(repository.get_topics(session.id)) == len(_plan().planned_topics)
    assert len(repository.get_questions(session.id)) == 1
    assert len(_calls(llm, "InterviewPlan")) == 1


@pytest.mark.asyncio
async def test_redis_runtime_state_carries_planner_values(repository, db_session):
    session = _created(repository, db_session)
    started, _, _ = await _service(repository, _llm(_plan(Difficulty.HARD, 8))).start_interview(session.id)
    redis = FakeAsyncRedis()
    runtime = RuntimeStateService(redis_client=redis, repository=repository)

    state = runtime.build_state(session=started, last_action=None)
    await runtime.set_state(state)

    stored = await runtime.get_state(session.id)
    assert redis.store[InterviewRedisKeys.state(session.id)]
    assert stored.difficulty is Difficulty.HARD
    assert stored.question_limit == 8


@pytest.mark.asyncio
async def test_planner_max_questions_is_the_answer_ceiling(repository, db_session):
    from app.workflows.interview.models import AnswerAnalysis, NextAction

    plan = _plan(Difficulty.MEDIUM, 6)  # differs from the placeholder limit (5)
    llm = _llm(plan)
    llm._structured_responses.update(
        {
            "AnswerAnalysis": AnswerAnalysis(
                understanding="BASIC", correctness=0.5, depth=0.4, concepts_demonstrated=[],
                concepts_missing=[], reasoning_quality="MODERATE", needs_follow_up=True,
            ),
            "NextAction": NextAction(
                action="FOLLOW_UP", topic=InterviewTopic.LLM_FUNDAMENTALS,
                difficulty=Difficulty.MEDIUM, rationale="Keep going.",
            ),
        }
    )
    session = _created(repository, db_session)
    service = _service(repository, llm)
    _, question, _ = await service.start_interview(session.id)

    for _ in range(5):  # Q1 + 5 answers -> Q2..Q6, all under the planner ceiling of 6
        _, question, _ = await service.submit_answer(session.id, question.id, "answer")
        assert question is not None
    final, next_question, _ = await service.submit_answer(session.id, question.id, "answer")

    assert final.status is InterviewStatus.COMPLETED
    assert next_question is None
