"""The planner-autonomy contract: the candidate chooses only a role (and optionally a resume); the planner
decides topics, starting difficulty and the maximum question ceiling, and its output is validated, never trusted."""

import pytest
from pydantic import ValidationError

from app.domain.competencies import get_role_competencies
from app.domain.enums import CompetencyRequirement, Difficulty, InterviewTopic, PlannedTopicPriority, Role
from app.planning import validator as validator_module
from app.planning.models import (
    PLAN_MAX_QUESTIONS,
    PLAN_MAX_TOPICS,
    PLAN_MIN_QUESTIONS,
    PLAN_MIN_TOPICS,
    InterviewPlan,
    InterviewPlanningConstraints,
    InterviewPlanningInput,
    PlannedTopic,
    build_planning_input,
)
from app.planning.prompts import build_planning_messages
from app.planning.validator import InvalidInterviewPlanError, validate_interview_plan
from tests.plan_helpers import complete_plan

T = InterviewTopic
CONSTRAINTS = InterviewPlanningConstraints(max_duration_minutes=45)


def _topic(topic=T.LLM_FUNDAMENTALS, keys=("llm_fundamentals",), minutes=5) -> PlannedTopic:
    return PlannedTopic(
        topic=topic,
        competency_keys=list(keys),
        priority=PlannedTopicPriority.MEDIUM,
        rationale="Planner's choice.",
        suggested_time_budget_minutes=minutes,
    )


def _valid_plan(role: Role = Role.AI_ENGINEER, seed: PlannedTopic | None = None, **fields) -> InterviewPlan:
    plan = complete_plan(
        InterviewPlan(role=role, objectives=["Assess the role."], planned_topics=[seed or _topic()])
    )
    return plan.model_copy(update=fields)


def _raw(topics: list[PlannedTopic], **fields) -> InterviewPlan:
    return InterviewPlan(
        role=Role.AI_ENGINEER, objectives=["x"], planned_topics=topics, **fields
    )


def _validate(plan: InterviewPlan, role: Role = Role.AI_ENGINEER) -> None:
    validate_interview_plan(build_planning_input(role, CONSTRAINTS), plan)


# --------------------------------------------------------------------------- input contract


def test_planning_input_needs_only_role_and_max_duration():
    planning_input = build_planning_input(Role.AI_ENGINEER, InterviewPlanningConstraints(max_duration_minutes=45))

    assert planning_input.constraints.max_duration_minutes == 45
    assert set(InterviewPlanningConstraints.model_fields) == {"max_duration_minutes"}


@pytest.mark.parametrize("stale", [{"difficulty": Difficulty.MEDIUM}, {"question_limit": 5}])
def test_constraints_no_longer_accept_candidate_controlled_fields(stale):
    with pytest.raises(ValidationError):
        InterviewPlanningConstraints(max_duration_minutes=45, **stale)


def test_planning_input_has_no_selected_topics_and_rejects_them():
    assert "selected_topics" not in InterviewPlanningInput.model_fields
    with pytest.raises(ValidationError):
        InterviewPlanningInput(
            role=Role.AI_ENGINEER,
            competencies=get_role_competencies(Role.AI_ENGINEER),
            constraints=CONSTRAINTS,
            selected_topics=[T.RAG],
        )


@pytest.mark.parametrize("role", list(Role))
def test_full_role_competency_catalog_reaches_the_planner(role):
    planning_input = build_planning_input(role, CONSTRAINTS)
    assert planning_input.competencies == get_role_competencies(role)

    user_prompt = build_planning_messages(planning_input)[1].content
    for competency in get_role_competencies(role):
        assert f"key: {competency.key}" in user_prompt


def test_prompt_states_planner_autonomy_and_no_candidate_constraints():
    messages = build_planning_messages(build_planning_input(Role.AI_ENGINEER, CONSTRAINTS))
    system, user = messages[0].content, messages[1].content

    assert "does NOT choose interview topics, difficulty, or question count" in system
    assert "starting_difficulty" in system and "max_questions" in system
    assert "SAFETY CEILING" in system
    assert "may end earlier" in system
    assert "max_duration_minutes" in user
    for stale in ("question_limit", "CANDIDATE-SELECTED", "difficulty:"):
        assert stale not in user
        assert stale not in system


def test_prompt_keeps_resume_claims_as_unverified_evidence():
    system = build_planning_messages(build_planning_input(Role.AI_ENGINEER, CONSTRAINTS))[0].content
    assert "CANDIDATE-REPORTED EVIDENCE, never verified facts" in system


# --------------------------------------------------------------------------- output: difficulty & max_questions


@pytest.mark.parametrize("difficulty", list(Difficulty))
def test_valid_starting_difficulty_accepted(difficulty):
    _validate(_valid_plan(starting_difficulty=difficulty))


def test_invalid_starting_difficulty_rejected():
    with pytest.raises(ValidationError):
        _raw([_topic()], starting_difficulty="EXTREME")


def test_missing_starting_difficulty_rejected_by_validator():
    with pytest.raises(InvalidInterviewPlanError, match="starting_difficulty"):
        _validate(_valid_plan(starting_difficulty=None))


@pytest.mark.parametrize("value", [5, PLAN_MAX_QUESTIONS])
def test_valid_max_questions_accepted(value):
    _validate(_valid_plan(max_questions=value))


def test_minimum_max_questions_accepted_when_the_plan_is_small_enough():
    # SDE_INTERN has only two required topics, so a two-topic plan fits under a ceiling of 3.
    role = Role.SDE_INTERN
    required = [c for c in get_role_competencies(role) if c.requirement is CompetencyRequirement.REQUIRED]
    topics = {}
    for c in required:
        topics.setdefault(c.topic, []).append(c.key)
    plan = InterviewPlan(
        role=role,
        objectives=["x"],
        planned_topics=[_topic(topic, tuple(keys)) for topic, keys in topics.items()],
        starting_difficulty=Difficulty.EASY,
        max_questions=PLAN_MIN_QUESTIONS,
    )
    validate_interview_plan(build_planning_input(role, CONSTRAINTS), plan)


def test_bounds_mirror_the_runtime_question_limit_contract():
    assert (PLAN_MIN_QUESTIONS, PLAN_MAX_QUESTIONS) == (3, 10)


@pytest.mark.parametrize("value", [PLAN_MIN_QUESTIONS - 1, 0, -1, PLAN_MAX_QUESTIONS + 1])
def test_out_of_range_max_questions_rejected_by_the_model(value):
    with pytest.raises(ValidationError):
        _raw([_topic()], max_questions=value)


@pytest.mark.parametrize("value", [PLAN_MIN_QUESTIONS - 1, PLAN_MAX_QUESTIONS + 1])
def test_out_of_range_max_questions_rejected_even_if_model_validation_is_bypassed(value):
    plan = _valid_plan().model_copy(update={"max_questions": value})  # model_copy skips validation
    with pytest.raises(InvalidInterviewPlanError, match="max_questions"):
        _validate(plan)


def test_missing_max_questions_rejected_by_validator():
    with pytest.raises(InvalidInterviewPlanError, match="max_questions"):
        _validate(_valid_plan(max_questions=None))


def test_max_questions_must_leave_room_for_one_question_per_topic():
    plan = _valid_plan()
    assert len(plan.planned_topics) > PLAN_MIN_QUESTIONS
    with pytest.raises(InvalidInterviewPlanError, match="at least one question per topic"):
        _validate(plan.model_copy(update={"max_questions": PLAN_MIN_QUESTIONS}))


# --------------------------------------------------------------------------- output: topics


def test_planner_chooses_its_own_topics_from_the_full_catalog():
    planning_input = build_planning_input(Role.BACKEND_DEVELOPER, CONSTRAINTS)
    plan = _valid_plan(Role.BACKEND_DEVELOPER, seed=_topic(T.REST_APIS, ("api_design",)))

    validate_interview_plan(planning_input, plan)  # no candidate selection involved

    catalog_topics = {c.topic for c in planning_input.competencies}
    assert {t.topic for t in plan.planned_topics} <= catalog_topics


def test_duplicate_topic_rejected():
    with pytest.raises(ValidationError, match="must not repeat a topic"):
        _raw([_topic(), _topic()])


def test_topic_unknown_to_the_role_rejected():
    with pytest.raises(ValidationError, match="not valid for role"):
        _raw([_topic(T.REST_APIS, ("api_design",))])


def test_topic_outside_the_planner_catalog_rejected_by_validator():
    # A planning input whose catalog lacks the topic (hand-built; the real one always has the full catalog).
    full = get_role_competencies(Role.AI_ENGINEER)
    planning_input = InterviewPlanningInput(
        role=Role.AI_ENGINEER,
        competencies=[c for c in full if c.topic is not T.RAG],
        constraints=CONSTRAINTS,
    )
    plan = _valid_plan()
    assert T.RAG in {t.topic for t in plan.planned_topics}
    with pytest.raises(InvalidInterviewPlanError, match="RAG"):
        validate_interview_plan(planning_input, plan)


def test_invalid_competency_key_rejected():
    with pytest.raises(ValidationError, match="no_such_key"):
        _raw([_topic(keys=("no_such_key",))])


def test_competency_key_under_the_wrong_topic_rejected():
    with pytest.raises(ValidationError, match="retrieval_augmented_generation"):
        _raw([_topic(T.LLM_FUNDAMENTALS, ("retrieval_augmented_generation",))])


def test_too_few_topics_rejected():
    plan = _valid_plan().model_copy(update={"planned_topics": [_topic()]})
    with pytest.raises(InvalidInterviewPlanError, match=f"{PLAN_MIN_TOPICS}-{PLAN_MAX_TOPICS}"):
        _validate(plan)


def test_too_many_topics_rejected(monkeypatch):
    # No role catalog has more than PLAN_MAX_TOPICS topics, so the ceiling is exercised by tightening it.
    monkeypatch.setattr(validator_module, "PLAN_MAX_TOPICS", 3)
    plan = _valid_plan()
    assert len(plan.planned_topics) > 3
    with pytest.raises(InvalidInterviewPlanError, match="planned topics"):
        _validate(plan)


@pytest.mark.parametrize("role", list(Role))
def test_every_role_can_satisfy_the_topic_bounds_with_required_coverage(role):
    required_topics = {
        c.topic for c in get_role_competencies(role) if c.requirement is CompetencyRequirement.REQUIRED
    }
    assert PLAN_MIN_TOPICS <= len(required_topics) <= PLAN_MAX_TOPICS


def test_missing_required_competency_rejected():
    plan = _valid_plan()
    # Drop one required competency's topic entirely (keeping the plan otherwise valid).
    plan = plan.model_copy(update={"planned_topics": plan.planned_topics[:-1]})
    dropped = [
        c.key
        for c in get_role_competencies(Role.AI_ENGINEER)
        if c.requirement is CompetencyRequirement.REQUIRED
        and c.key not in {k for t in plan.planned_topics for k in t.competency_keys}
    ]
    assert dropped
    with pytest.raises(InvalidInterviewPlanError, match="required competencies"):
        _validate(plan)


def test_optional_competencies_may_be_skipped():
    plan = _valid_plan()
    planned_keys = {k for t in plan.planned_topics for k in t.competency_keys}
    optional = [c.key for c in get_role_competencies(Role.AI_ENGINEER) if c.requirement is CompetencyRequirement.OPTIONAL]
    assert optional and not (set(optional) & planned_keys)
    _validate(plan)


def test_selected_topics_validator_is_gone():
    assert not hasattr(validator_module, "_check_selected_topics")


# --------------------------------------------------------------------------- backward compatibility


def test_old_plan_json_without_planner_decisions_still_loads():
    legacy = _valid_plan().model_dump(mode="json")
    del legacy["starting_difficulty"], legacy["max_questions"]

    plan = InterviewPlan.model_validate(legacy)

    assert plan.starting_difficulty is None
    assert plan.max_questions is None
    assert plan.plan_version == 1


def test_new_plan_round_trips_planner_decisions():
    plan = _valid_plan(starting_difficulty=Difficulty.HARD, max_questions=8)
    again = InterviewPlan.model_validate(plan.model_dump(mode="json"))
    assert (again.starting_difficulty, again.max_questions) == (Difficulty.HARD, 8)
