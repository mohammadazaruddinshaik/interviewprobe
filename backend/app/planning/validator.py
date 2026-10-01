"""Cross-object validation between an InterviewPlanningInput and an
InterviewPlan.

Pydantic model validators (app/planning/models.py) enforce structural
correctness: a PlannedTopic's competency keys must belong to its role
and anchor to its topic, resume_relevance NONE ↔ empty related_claim_ids,
no duplicate topics, no empty plan, etc.

This module validates invariants that can only be checked when both the
planner input and planner output are available — relationships the Pydantic
models cannot enforce on their own because they validate one object at a
time:

    • role agreement between input and plan
    • the planner's own decisions are present and in bounds: starting_difficulty,
      max_questions and the number of planned topics
    • every planned topic/competency belongs to the input's role competency catalog
    • every REQUIRED competency of the role is covered
    • every related_claim_id actually exists in the input's resume claims
    • total planned time ≤ max_duration_minutes

The candidate chooses none of this — the plan is the planner's decision, but
never authoritative: whatever an LLM returns is checked here.

The evaluation validator (app/evaluation/validator.py) uses
`LLMInvalidResponseError` for LLM-proposed data that fails backend
checks. This module follows the same principle — a future LLM planner's
output will pass through here — but uses a domain-level exception since
there is no HTTP layer involved yet.

Pure and deterministic: no LLM, no database, no Redis.
"""

from app.domain.enums import CompetencyRequirement
from app.planning.models import (
    PLAN_MAX_QUESTIONS,
    PLAN_MAX_TOPICS,
    PLAN_MIN_QUESTIONS,
    PLAN_MIN_TOPICS,
    InterviewPlan,
    InterviewPlanningInput,
)


class InvalidInterviewPlanError(Exception):
    """Raised when cross-object validation between a planning input and a
    plan finds an invariant violation. Analogous to `InvalidRoleTopicError`
    / `InvalidTopicConceptError` — a domain exception, not an HTTP one."""


def validate_interview_plan(
    planning_input: InterviewPlanningInput,
    plan: InterviewPlan,
) -> None:
    """Validate `plan` against `planning_input`.

    Raises `InvalidInterviewPlanError` with a descriptive message on the
    first violation found. Returns `None` (does not raise) when the plan
    is valid.

    Checks are ordered from cheapest/most fundamental to most specific so
    the first error a caller sees is the most useful one.
    """
    _check_role_consistency(planning_input, plan)
    _check_starting_difficulty(plan)
    _check_max_questions(plan)
    _check_topic_count(plan)
    _check_topics_belong_to_catalog(planning_input, plan)
    _check_required_coverage(planning_input, plan)
    _check_claim_references(planning_input, plan)
    _check_time_budget(planning_input, plan)


def _check_role_consistency(
    planning_input: InterviewPlanningInput,
    plan: InterviewPlan,
) -> None:
    if planning_input.role != plan.role:
        raise InvalidInterviewPlanError(
            f"Plan role {plan.role.value} does not match planning input role "
            f"{planning_input.role.value}."
        )


def _check_starting_difficulty(plan: InterviewPlan) -> None:
    # Optional on the model only so pre-existing persisted plans load; a newly generated plan must decide.
    if plan.starting_difficulty is None:
        raise InvalidInterviewPlanError("Plan must set starting_difficulty.")


def _check_max_questions(plan: InterviewPlan) -> None:
    if plan.max_questions is None:
        raise InvalidInterviewPlanError("Plan must set max_questions.")
    if not PLAN_MIN_QUESTIONS <= plan.max_questions <= PLAN_MAX_QUESTIONS:
        raise InvalidInterviewPlanError(
            f"max_questions {plan.max_questions} is outside the allowed range "
            f"{PLAN_MIN_QUESTIONS}-{PLAN_MAX_QUESTIONS}."
        )
    if plan.max_questions < len(plan.planned_topics):
        raise InvalidInterviewPlanError(
            f"max_questions {plan.max_questions} cannot cover {len(plan.planned_topics)} planned topics "
            "(at least one question per topic)."
        )


def _check_topic_count(plan: InterviewPlan) -> None:
    count = len(plan.planned_topics)
    if not PLAN_MIN_TOPICS <= count <= PLAN_MAX_TOPICS:
        raise InvalidInterviewPlanError(
            f"Plan has {count} planned topics; allowed range is {PLAN_MIN_TOPICS}-{PLAN_MAX_TOPICS}."
        )


def _check_topics_belong_to_catalog(
    planning_input: InterviewPlanningInput,
    plan: InterviewPlan,
) -> None:
    """Duplicate topics are already rejected structurally by `InterviewPlan`. Here every topic and competency
    key must come from the competency catalog the planner was actually given, and each key must sit under
    the topic that lists it."""
    catalog = {c.key: c for c in planning_input.competencies}
    for planned_topic in plan.planned_topics:
        if planned_topic.topic not in {c.topic for c in catalog.values()}:
            raise InvalidInterviewPlanError(
                f"Planned topic '{planned_topic.topic.value}' is not in the {planning_input.role.value} "
                "competency catalog."
            )
        for key in planned_topic.competency_keys:
            competency = catalog.get(key)
            if competency is None or competency.topic is not planned_topic.topic:
                raise InvalidInterviewPlanError(
                    f"Competency '{key}' does not belong to planned topic '{planned_topic.topic.value}'."
                )


def _check_required_coverage(
    planning_input: InterviewPlanningInput,
    plan: InterviewPlan,
) -> None:
    """OPTIONAL competencies may be skipped when time is short; REQUIRED ones are core role coverage."""
    covered = {key for t in plan.planned_topics for key in t.competency_keys}
    missing = sorted(
        c.key
        for c in planning_input.competencies
        if c.requirement is CompetencyRequirement.REQUIRED and c.key not in covered
    )
    if missing:
        raise InvalidInterviewPlanError(f"Plan does not cover required competencies: {missing}.")


def _check_claim_references(
    planning_input: InterviewPlanningInput,
    plan: InterviewPlan,
) -> None:
    known_claim_ids = {c.claim_id for c in planning_input.resume_claims}

    for planned_topic in plan.planned_topics:
        for claim_id in planned_topic.related_claim_ids:
            if claim_id not in known_claim_ids:
                raise InvalidInterviewPlanError(
                    f"Planned topic '{planned_topic.topic.value}' references unknown "
                    f"resume claim '{claim_id}'. Known claim IDs: "
                    f"{sorted(known_claim_ids) if known_claim_ids else '(none)'}."
                )


def _check_time_budget(
    planning_input: InterviewPlanningInput,
    plan: InterviewPlan,
) -> None:
    total_minutes = sum(t.suggested_time_budget_minutes for t in plan.planned_topics)
    max_minutes = planning_input.constraints.max_duration_minutes

    if total_minutes > max_minutes:
        raise InvalidInterviewPlanError(
            f"Planned interview time {total_minutes} minutes exceeds "
            f"maximum duration {max_minutes} minutes."
        )
