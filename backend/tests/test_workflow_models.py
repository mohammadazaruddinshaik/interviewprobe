import pytest
from pydantic import ValidationError

from app.domain.enums import Difficulty, InterviewTopic, InterviewTopicStatus, QuestionType
from app.workflows.interview.models import (
    AnswerAnalysis,
    DecisionContext,
    GeneratedQuestion,
    NextAction,
    TopicState,
    TopicTransition,
    ValidatedDecision,
)


def test_generated_question_constructs():
    question = GeneratedQuestion(
        question="Explain how embeddings work.",
        topic=InterviewTopic.EMBEDDINGS_VECTOR_DB,
        difficulty=Difficulty.MEDIUM,
        question_type=QuestionType.INITIAL,
    )

    assert question.topic is InterviewTopic.EMBEDDINGS_VECTOR_DB


def test_generated_question_rejects_empty_question_text():
    with pytest.raises(ValidationError):
        GeneratedQuestion(
            question="",
            topic=InterviewTopic.RAG,
            difficulty=Difficulty.EASY,
            question_type=QuestionType.INITIAL,
        )


def test_answer_analysis_constructs_with_valid_scores():
    analysis = AnswerAnalysis(
        understanding="GOOD",
        correctness=0.8,
        depth=0.6,
        concepts_demonstrated=["retrieval"],
        concepts_missing=["reranking"],
        reasoning_quality="STRONG",
        needs_follow_up=False,
    )

    assert analysis.correctness == 0.8


@pytest.mark.parametrize("field", ["correctness", "depth"])
def test_answer_analysis_rejects_score_below_zero(field):
    kwargs = dict(
        understanding="GOOD",
        correctness=0.5,
        depth=0.5,
        concepts_demonstrated=[],
        concepts_missing=[],
        reasoning_quality="STRONG",
        needs_follow_up=False,
    )
    kwargs[field] = -0.01

    with pytest.raises(ValidationError):
        AnswerAnalysis(**kwargs)


@pytest.mark.parametrize("field", ["correctness", "depth"])
def test_answer_analysis_rejects_score_above_one(field):
    kwargs = dict(
        understanding="GOOD",
        correctness=0.5,
        depth=0.5,
        concepts_demonstrated=[],
        concepts_missing=[],
        reasoning_quality="STRONG",
        needs_follow_up=False,
    )
    kwargs[field] = 1.01

    with pytest.raises(ValidationError):
        AnswerAnalysis(**kwargs)


def test_answer_analysis_rejects_invalid_understanding_literal():
    with pytest.raises(ValidationError):
        AnswerAnalysis(
            understanding="EXCELLENT",
            correctness=0.5,
            depth=0.5,
            concepts_demonstrated=[],
            concepts_missing=[],
            reasoning_quality="STRONG",
            needs_follow_up=False,
        )


def test_next_action_constructs_with_no_topic():
    action = NextAction(action="END", topic=None, difficulty=Difficulty.MEDIUM, rationale="done")

    assert action.action == "END"
    assert action.topic is None


def test_next_action_rejects_invalid_action_literal():
    with pytest.raises(ValidationError):
        NextAction(action="SKIP", topic=None, difficulty=Difficulty.MEDIUM, rationale="x")


def test_next_action_rejects_empty_rationale():
    with pytest.raises(ValidationError):
        NextAction(action="END", topic=None, difficulty=Difficulty.MEDIUM, rationale="")


def test_topic_state_constructs():
    topic_state = TopicState(topic=InterviewTopic.RAG, status=InterviewTopicStatus.PENDING, sequence_number=1)

    assert topic_state.status is InterviewTopicStatus.PENDING


def test_topic_transition_defaults_to_no_transition():
    transition = TopicTransition()

    assert transition.from_topic is None
    assert transition.to_topic is None


def test_decision_context_defaults_topics_to_empty_list():
    context = DecisionContext(
        current_topic=None, difficulty=Difficulty.MEDIUM, question_number=1, question_limit=5
    )

    assert context.topics == []


def test_validated_decision_defaults_fallback_used_to_false():
    decision = ValidatedDecision(
        action=NextAction(action="END", topic=None, difficulty=Difficulty.MEDIUM, rationale="x")
    )

    assert decision.fallback_used is False
    assert decision.topic_transition == TopicTransition()
