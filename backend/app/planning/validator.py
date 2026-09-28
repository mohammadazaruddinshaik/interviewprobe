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
    • every related_claim_id actually exists in the input's resume claims
    • total planned time ≤ max_duration_minutes

The evaluation validator (app/evaluation/validator.py) uses
`LLMInvalidResponseError` for LLM-proposed data that fails backend
checks. This module follows the same principle — a future LLM planner's
output will pass through here — but uses a domain-level exception since
there is no HTTP layer involved yet.

Pure and deterministic: no LLM, no database, no Redis.
"""

from app.planning.models import InterviewPlan, InterviewPlanningInput


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
