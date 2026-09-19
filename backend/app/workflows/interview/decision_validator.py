"""Backend validation for the LLM's proposed `NextAction`.

Core principle: the LLM proposes, the backend validates and executes.
Everything in this module is pure and deterministic — no LLM calls, no
Redis, no PostgreSQL. It is the single place that enforces:

* the question limit always wins, regardless of what the LLM proposed
* only the session's selected topics may be chosen for NEW_TOPIC
* a COMPLETED (or the current) topic may not be re-selected
* FOLLOW_UP/CLARIFY always stay on the current topic

and provides a deterministic, safe fallback whenever a proposal can't be
trusted — either because the LLM call itself failed, or because its
structurally-valid proposal fails one of the checks above.
"""

from app.domain.enums import InterviewTopic, InterviewTopicStatus
from app.workflows.interview.models import (
    DecisionContext,
    NextAction,
    TopicState,
    TopicTransition,
    ValidatedDecision,
)


def _first_pending_topic(topics: list[TopicState]) -> InterviewTopic | None:
    pending = [t for t in topics if t.status == InterviewTopicStatus.PENDING]
    if not pending:
        return None
    return min(pending, key=lambda t: t.sequence_number).topic


def _topic_status(context: DecisionContext, topic: InterviewTopic | None) -> InterviewTopicStatus | None:
    if topic is None:
        return None
    for entry in context.topics:
        if entry.topic == topic:
            return entry.status
    return None


def fallback_decision(context: DecisionContext, *, reason: str) -> NextAction:
    """Deterministic, safe default used whenever a proposal cannot be
    trusted:

    question limit reached -> END
    else, mid-topic         -> FOLLOW_UP (stay on the current topic)
    else, a topic is PENDING -> NEW_TOPIC (the earliest one, by sequence)
    else                     -> END (nothing left to ask about)
    """
    if context.question_number >= context.question_limit:
        action, topic = "END", None
    elif context.current_topic is not None:
        action, topic = "FOLLOW_UP", context.current_topic
    else:
        next_topic = _first_pending_topic(context.topics)
        action, topic = ("NEW_TOPIC", next_topic) if next_topic is not None else ("END", None)

    return NextAction(action=action, topic=topic, difficulty=context.difficulty, rationale=f"Fallback: {reason}")


def validate_decision(proposed: NextAction, context: DecisionContext) -> ValidatedDecision:
    """Validate (and, if necessary, replace) the LLM's proposed action."""

    # The question limit always wins — this cannot be overridden by any
    # proposal, valid-looking or not.
    if context.question_number >= context.question_limit:
        action = fallback_decision(context, reason="question limit reached")
        return ValidatedDecision(action=action, fallback_used=True)

    if proposed.action in ("FOLLOW_UP", "CLARIFY"):
        # Always normalize to the current topic — an unrelated topic on a
        # FOLLOW_UP/CLARIFY proposal is not something we trust blindly.
        normalized = NextAction(
            action=proposed.action,
            topic=context.current_topic,
            difficulty=proposed.difficulty,
            rationale=proposed.rationale,
        )
        return ValidatedDecision(action=normalized)

    if proposed.action == "NEW_TOPIC":
        # A valid NEW_TOPIC target must be one of the session's selected
        # topics, currently PENDING (not COMPLETED, and not the topic
        # already IN_PROGRESS — under this lifecycle only one topic is
        # ever IN_PROGRESS at a time, so "PENDING" and "not the current
        # topic" are equivalent here), and must actually differ from the
        # current topic.
        status = _topic_status(context, proposed.topic)
        is_valid = (
            proposed.topic is not None
            and proposed.topic != context.current_topic
            and status == InterviewTopicStatus.PENDING
        )
        if is_valid:
            transition = TopicTransition(from_topic=context.current_topic, to_topic=proposed.topic)
            return ValidatedDecision(action=proposed, topic_transition=transition)

        fallback = fallback_decision(context, reason="proposed topic invalid or unavailable")
        transition = (
            TopicTransition(from_topic=context.current_topic, to_topic=fallback.topic)
            if fallback.action == "NEW_TOPIC"
            else TopicTransition()
        )
        return ValidatedDecision(action=fallback, topic_transition=transition, fallback_used=True)

    if proposed.action == "END":
        return ValidatedDecision(action=proposed)

    # Unreachable given NextAction.action's Pydantic Literal validation,
    # but never silently accept an unrecognized action string.
    fallback = fallback_decision(context, reason="unrecognized action")
    return ValidatedDecision(action=fallback, fallback_used=True)
