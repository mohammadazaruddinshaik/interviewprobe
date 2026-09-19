from app.domain.enums import Difficulty, InterviewTopic, InterviewTopicStatus
from app.workflows.interview.decision_validator import fallback_decision, validate_decision
from app.workflows.interview.models import DecisionContext, NextAction, TopicState

RAG_IN_PROGRESS = TopicState(topic=InterviewTopic.RAG, status=InterviewTopicStatus.IN_PROGRESS, sequence_number=1)
AGENTS_PENDING = TopicState(topic=InterviewTopic.AI_AGENTS, status=InterviewTopicStatus.PENDING, sequence_number=2)
EVAL_PENDING = TopicState(
    topic=InterviewTopic.LLM_EVALUATION, status=InterviewTopicStatus.PENDING, sequence_number=3
)
EVAL_COMPLETED = TopicState(
    topic=InterviewTopic.LLM_EVALUATION, status=InterviewTopicStatus.COMPLETED, sequence_number=3
)


def context(**overrides) -> DecisionContext:
    defaults = dict(
        current_topic=InterviewTopic.RAG,
        difficulty=Difficulty.MEDIUM,
        question_number=2,
        question_limit=5,
        topics=[RAG_IN_PROGRESS, AGENTS_PENDING, EVAL_COMPLETED],
    )
    defaults.update(overrides)
    return DecisionContext(**defaults)


def proposal(action: str, topic=None, difficulty=Difficulty.MEDIUM) -> NextAction:
    return NextAction(action=action, topic=topic, difficulty=difficulty, rationale="LLM proposal")


# ---------------------------------------------------------------------------
# Question limit always wins
# ---------------------------------------------------------------------------


def test_question_limit_forces_end_overriding_follow_up():
    ctx = context(question_number=5, question_limit=5)

    result = validate_decision(proposal("FOLLOW_UP", InterviewTopic.RAG), ctx)

    assert result.action.action == "END"
    assert result.fallback_used is True


def test_question_limit_forces_end_overriding_new_topic():
    ctx = context(question_number=5, question_limit=5)

    result = validate_decision(proposal("NEW_TOPIC", InterviewTopic.AI_AGENTS), ctx)

    assert result.action.action == "END"
    assert result.fallback_used is True


def test_question_limit_not_yet_reached_allows_normal_processing():
    ctx = context(question_number=4, question_limit=5)

    result = validate_decision(proposal("FOLLOW_UP", InterviewTopic.RAG), ctx)

    assert result.action.action == "FOLLOW_UP"
    assert result.fallback_used is False


# ---------------------------------------------------------------------------
# FOLLOW_UP / CLARIFY always normalize to the current topic
# ---------------------------------------------------------------------------


def test_follow_up_is_normalized_to_current_topic_even_if_llm_proposed_another():
    ctx = context(current_topic=InterviewTopic.RAG)

    result = validate_decision(proposal("FOLLOW_UP", InterviewTopic.AI_AGENTS), ctx)

    assert result.action.action == "FOLLOW_UP"
    assert result.action.topic is InterviewTopic.RAG
    assert result.fallback_used is False


def test_clarify_is_normalized_to_current_topic():
    ctx = context(current_topic=InterviewTopic.RAG)

    result = validate_decision(proposal("CLARIFY", None), ctx)

    assert result.action.action == "CLARIFY"
    assert result.action.topic is InterviewTopic.RAG
    assert result.fallback_used is False


def test_follow_up_and_clarify_preserve_the_llm_proposed_difficulty():
    ctx = context()

    result = validate_decision(proposal("FOLLOW_UP", InterviewTopic.RAG, difficulty=Difficulty.HARD), ctx)

    assert result.action.difficulty == Difficulty.HARD


# ---------------------------------------------------------------------------
# NEW_TOPIC — valid
# ---------------------------------------------------------------------------


def test_new_topic_accepted_when_selected_and_pending():
    ctx = context()

    result = validate_decision(proposal("NEW_TOPIC", InterviewTopic.AI_AGENTS), ctx)

    assert result.action.action == "NEW_TOPIC"
    assert result.action.topic is InterviewTopic.AI_AGENTS
    assert result.fallback_used is False
    assert result.topic_transition.from_topic is InterviewTopic.RAG
    assert result.topic_transition.to_topic is InterviewTopic.AI_AGENTS


# ---------------------------------------------------------------------------
# NEW_TOPIC — invalid, must fall back safely
# ---------------------------------------------------------------------------


def test_new_topic_rejected_when_not_a_selected_topic():
    ctx = context()  # selected: RAG, AI_AGENTS, LLM_EVALUATION

    result = validate_decision(proposal("NEW_TOPIC", InterviewTopic.EMBEDDINGS_VECTOR_DB), ctx)

    assert result.fallback_used is True
    assert result.action.topic != InterviewTopic.EMBEDDINGS_VECTOR_DB


def test_new_topic_rejected_when_already_completed():
    ctx = context(topics=[RAG_IN_PROGRESS, EVAL_COMPLETED])

    result = validate_decision(proposal("NEW_TOPIC", InterviewTopic.LLM_EVALUATION), ctx)

    assert result.fallback_used is True
    assert result.action.action != "NEW_TOPIC" or result.action.topic != InterviewTopic.LLM_EVALUATION


def test_new_topic_rejected_when_it_equals_the_current_topic():
    ctx = context(current_topic=InterviewTopic.RAG, topics=[RAG_IN_PROGRESS, AGENTS_PENDING])

    result = validate_decision(proposal("NEW_TOPIC", InterviewTopic.RAG), ctx)

    assert result.fallback_used is True


def test_new_topic_rejected_when_no_topic_proposed():
    ctx = context()

    result = validate_decision(proposal("NEW_TOPIC", None), ctx)

    assert result.fallback_used is True


def test_invalid_new_topic_never_produces_a_topic_transition_to_the_rejected_topic():
    ctx = context()

    result = validate_decision(proposal("NEW_TOPIC", InterviewTopic.EMBEDDINGS_VECTOR_DB), ctx)

    assert result.topic_transition.to_topic != InterviewTopic.EMBEDDINGS_VECTOR_DB


def test_invalid_new_topic_falls_back_to_a_valid_pending_topic_when_current_topic_is_none():
    """Only reachable in the fallback tree when there is no current topic
    (never true in a real answer-graph turn, but a legitimate state for
    the pure validator/fallback function to handle)."""
    ctx = context(current_topic=None, topics=[EVAL_COMPLETED, AGENTS_PENDING])

    result = validate_decision(proposal("NEW_TOPIC", InterviewTopic.EMBEDDINGS_VECTOR_DB), ctx)

    assert result.fallback_used is True
    assert result.action.action == "NEW_TOPIC"
    assert result.action.topic is InterviewTopic.AI_AGENTS
    assert result.topic_transition.to_topic is InterviewTopic.AI_AGENTS


# ---------------------------------------------------------------------------
# END
# ---------------------------------------------------------------------------


def test_end_is_accepted_even_before_the_question_limit():
    ctx = context(question_number=2, question_limit=5)

    result = validate_decision(proposal("END", None), ctx)

    assert result.action.action == "END"
    assert result.fallback_used is False


# ---------------------------------------------------------------------------
# fallback_decision — the shared deterministic safe default
# ---------------------------------------------------------------------------


def test_fallback_decision_ends_when_limit_reached():
    ctx = context(question_number=5, question_limit=5)

    result = fallback_decision(ctx, reason="test")

    assert result.action == "END"
    assert result.topic is None


def test_fallback_decision_stays_on_current_topic_when_mid_topic():
    ctx = context(current_topic=InterviewTopic.RAG, question_number=2, question_limit=5)

    result = fallback_decision(ctx, reason="test")

    assert result.action == "FOLLOW_UP"
    assert result.topic is InterviewTopic.RAG


def test_fallback_decision_moves_to_earliest_pending_topic_when_no_current_topic():
    ctx = context(
        current_topic=None,
        question_number=2,
        question_limit=5,
        topics=[EVAL_PENDING, AGENTS_PENDING],  # AGENTS has the lower sequence_number
    )

    result = fallback_decision(ctx, reason="test")

    assert result.action == "NEW_TOPIC"
    assert result.topic is InterviewTopic.AI_AGENTS


def test_fallback_decision_ends_when_no_current_topic_and_nothing_pending():
    ctx = context(current_topic=None, question_number=2, question_limit=5, topics=[EVAL_COMPLETED])

    result = fallback_decision(ctx, reason="test")

    assert result.action == "END"
    assert result.topic is None


def test_fallback_decision_rationale_contains_the_given_reason():
    ctx = context(question_number=5, question_limit=5)

    result = fallback_decision(ctx, reason="a specific reason")

    assert "a specific reason" in result.rationale
