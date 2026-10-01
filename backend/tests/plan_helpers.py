"""Test helper: turn a hand-built `InterviewPlan` into one the planning validator accepts.

Many tests care about one plan detail (a topic order, a resume link) and hand-build a two- or three-topic plan.
`complete_plan` keeps exactly what they wrote and adds only what the planner contract now requires: the planner's
`starting_difficulty` / `max_questions` decisions, and coverage of every REQUIRED role competency. Missing required
competencies are attached to an already-planned topic when one matches, and only otherwise appended as a short LOW
topic, so existing topic order and topic counts are preserved wherever possible."""

import functools

from app.domain.competencies import get_role_competencies
from app.domain.enums import CompetencyRequirement, Difficulty, PlannedTopicPriority
from app.planning.models import InterviewPlan, PlannedTopic


def complete_plan(
    plan: InterviewPlan,
    *,
    starting_difficulty: Difficulty = Difficulty.MEDIUM,
    max_questions: int | None = None,
) -> InterviewPlan:
    topics = [t.model_copy(deep=True) for t in plan.planned_topics]
    by_topic = {t.topic: t for t in topics}
    covered = {key for t in topics for key in t.competency_keys}
    for competency in get_role_competencies(plan.role):
        if competency.requirement is not CompetencyRequirement.REQUIRED or competency.key in covered:
            continue
        existing = by_topic.get(competency.topic)
        if existing is not None:
            existing.competency_keys.append(competency.key)
        else:
            added = PlannedTopic(
                topic=competency.topic,
                competency_keys=[competency.key],
                priority=PlannedTopicPriority.LOW,
                rationale="Required role coverage.",
                suggested_time_budget_minutes=2,
            )
            topics.append(added)
            by_topic[competency.topic] = added
        covered.add(competency.key)
    return InterviewPlan(
        role=plan.role,
        plan_version=plan.plan_version,
        objectives=plan.objectives,
        planned_topics=topics,
        starting_difficulty=starting_difficulty,
        max_questions=max_questions if max_questions is not None else max(5, len(topics)),
    )


def completed(builder):
    """Decorator for a plan-building helper: its result goes through `complete_plan`."""

    @functools.wraps(builder)
    def wrapper(*args, **kwargs) -> InterviewPlan:
        return complete_plan(builder(*args, **kwargs))

    return wrapper
