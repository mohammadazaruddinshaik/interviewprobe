import uuid

import pytest
from pydantic import ValidationError

from app.domain.enums import (
    Difficulty,
    InterviewStatus,
    InterviewTopic,
    InterviewTopicStatus,
    QuestionType,
    Role,
)
from app.schemas.interview import (
    CompleteInterviewResponse,
    CreateInterviewRequest,
    CreateInterviewResponse,
    EvaluationResponse,
    InterviewResponse,
    InterviewTopicResponse,
    QuestionResponse,
    StartInterviewResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
)


# ---------------------------------------------------------------------------
# CreateInterviewRequest
# ---------------------------------------------------------------------------


def test_create_interview_request_valid():
    request = CreateInterviewRequest(
        role=Role.AI_ENGINEER,
        difficulty=Difficulty.MEDIUM,
        topics=[InterviewTopic.LLM_FUNDAMENTALS, InterviewTopic.RAG],
        question_limit=5,
    )

    assert request.role is Role.AI_ENGINEER
    assert request.topics == [InterviewTopic.LLM_FUNDAMENTALS, InterviewTopic.RAG]
    assert request.question_limit == 5


def test_create_interview_request_invalid_role_rejected():
    with pytest.raises(ValidationError):
        CreateInterviewRequest(
            role="NOT_A_ROLE",
            difficulty=Difficulty.MEDIUM,
            topics=[InterviewTopic.RAG],
            question_limit=5,
        )


def test_create_interview_request_invalid_difficulty_rejected():
    with pytest.raises(ValidationError):
        CreateInterviewRequest(
            role=Role.AI_ENGINEER,
            difficulty="NOT_A_DIFFICULTY",
            topics=[InterviewTopic.RAG],
            question_limit=5,
        )


def test_create_interview_request_invalid_topic_rejected():
    with pytest.raises(ValidationError):
        CreateInterviewRequest(
            role=Role.AI_ENGINEER,
            difficulty=Difficulty.MEDIUM,
            topics=["NOT_A_TOPIC"],
            question_limit=5,
        )


def test_create_interview_request_fewer_than_one_topic_rejected():
    with pytest.raises(ValidationError):
        CreateInterviewRequest(
            role=Role.AI_ENGINEER,
            difficulty=Difficulty.MEDIUM,
            topics=[],
            question_limit=5,
        )


def test_create_interview_request_more_than_six_topics_rejected():
    # Seven distinct topics, decoupled from the total size of the
    # InterviewTopic enum (Task 16 added topics for other roles) — this
    # only needs to exceed CreateInterviewRequest's max_length=6.
    seven_topics = [
        InterviewTopic.LLM_FUNDAMENTALS,
        InterviewTopic.RAG,
        InterviewTopic.EMBEDDINGS_VECTOR_DB,
        InterviewTopic.AI_AGENTS,
        InterviewTopic.LLM_EVALUATION,
        InterviewTopic.AI_SYSTEM_DESIGN,
        InterviewTopic.JAVASCRIPT,
    ]
    assert len(seven_topics) == 7

    with pytest.raises(ValidationError):
        CreateInterviewRequest(
            role=Role.AI_ENGINEER,
            difficulty=Difficulty.MEDIUM,
            topics=seven_topics,
            question_limit=5,
        )


def test_create_interview_request_duplicate_topics_rejected():
    with pytest.raises(ValidationError):
        CreateInterviewRequest(
            role=Role.AI_ENGINEER,
            difficulty=Difficulty.MEDIUM,
            topics=[InterviewTopic.RAG, InterviewTopic.RAG],
            question_limit=5,
        )


def test_create_interview_request_question_limit_below_minimum_rejected():
    with pytest.raises(ValidationError):
        CreateInterviewRequest(
            role=Role.AI_ENGINEER,
            difficulty=Difficulty.MEDIUM,
            topics=[InterviewTopic.RAG],
            question_limit=2,
        )


def test_create_interview_request_question_limit_above_maximum_rejected():
    with pytest.raises(ValidationError):
        CreateInterviewRequest(
            role=Role.AI_ENGINEER,
            difficulty=Difficulty.MEDIUM,
            topics=[InterviewTopic.RAG],
            question_limit=11,
        )


# ---------------------------------------------------------------------------
# SubmitAnswerRequest
# ---------------------------------------------------------------------------


def test_submit_answer_request_valid():
    request = SubmitAnswerRequest(question_id=uuid.uuid4(), answer="  A thoughtful answer.  ")

    assert request.answer == "A thoughtful answer."


def test_submit_answer_request_empty_answer_rejected():
    with pytest.raises(ValidationError):
        SubmitAnswerRequest(question_id=uuid.uuid4(), answer="")


def test_submit_answer_request_whitespace_only_answer_rejected():
    with pytest.raises(ValidationError):
        SubmitAnswerRequest(question_id=uuid.uuid4(), answer="   \n\t  ")


def test_submit_answer_request_over_max_length_rejected():
    with pytest.raises(ValidationError):
        SubmitAnswerRequest(question_id=uuid.uuid4(), answer="x" * 10_001)


def test_submit_answer_request_at_max_length_accepted():
    request = SubmitAnswerRequest(question_id=uuid.uuid4(), answer="x" * 10_000)

    assert len(request.answer) == 10_000


# ---------------------------------------------------------------------------
# EvaluationResponse
# ---------------------------------------------------------------------------


def _evaluation_kwargs(**overrides):
    kwargs = {
        "session_id": uuid.uuid4(),
        "technical_knowledge_score": 8.5,
        "reasoning_score": 7.0,
        "depth_score": 6.5,
        "communication_score": 9.0,
        "overall_score": 7.75,
        "strengths": ["clear reasoning"],
        "weaknesses": ["shallow on RAG"],
        "evidence": [{"question_id": str(uuid.uuid4()), "note": "good answer"}],
    }
    kwargs.update(overrides)
    return kwargs


def test_evaluation_response_valid_scores_accepted():
    evaluation = EvaluationResponse(**_evaluation_kwargs())

    assert evaluation.overall_score == 7.75


def test_evaluation_response_score_below_zero_rejected():
    with pytest.raises(ValidationError):
        EvaluationResponse(**_evaluation_kwargs(overall_score=-0.01))


def test_evaluation_response_score_above_ten_rejected():
    with pytest.raises(ValidationError):
        EvaluationResponse(**_evaluation_kwargs(technical_knowledge_score=10.01))


# ---------------------------------------------------------------------------
# Response schemas — representative valid objects
# ---------------------------------------------------------------------------


def test_create_interview_response_constructs():
    response = CreateInterviewResponse(
        id=uuid.uuid4(),
        role=Role.AI_ENGINEER,
        difficulty=Difficulty.HARD,
        topics=[InterviewTopic.AI_AGENTS],
        question_limit=6,
        status=InterviewStatus.CREATED,
    )

    assert response.status is InterviewStatus.CREATED


def test_question_response_field_names():
    question = QuestionResponse(
        id=uuid.uuid4(),
        sequence=1,
        text="Explain RAG.",
        topic=InterviewTopic.RAG,
        difficulty=Difficulty.EASY,
        type=QuestionType.INITIAL,
    )

    assert question.sequence == 1
    assert question.text == "Explain RAG."
    assert question.type is QuestionType.INITIAL


def test_start_interview_response_constructs():
    question = QuestionResponse(
        id=uuid.uuid4(),
        sequence=1,
        text="Explain embeddings.",
        topic=InterviewTopic.EMBEDDINGS_VECTOR_DB,
        difficulty=Difficulty.MEDIUM,
        type=QuestionType.INITIAL,
    )
    response = StartInterviewResponse(
        session_id=uuid.uuid4(),
        status=InterviewStatus.IN_PROGRESS,
        question=question,
    )

    assert response.question.topic is InterviewTopic.EMBEDDINGS_VECTOR_DB


def test_submit_answer_response_constructs_without_optional_fields():
    response = SubmitAnswerResponse(
        session_id=uuid.uuid4(),
        status=InterviewStatus.IN_PROGRESS,
        action="ASK_FOLLOW_UP",
    )

    assert response.question is None
    assert response.evaluation_status is None


def test_interview_response_constructs():
    response = InterviewResponse(
        session_id=uuid.uuid4(),
        role=Role.AI_ENGINEER,
        difficulty=Difficulty.MEDIUM,
        status=InterviewStatus.IN_PROGRESS,
        question_limit=5,
        current_topic=InterviewTopic.LLM_EVALUATION,
        current_question_number=2,
        questions_answered=1,
        topics=[
            InterviewTopicResponse(
                topic=InterviewTopic.LLM_EVALUATION,
                sequence_number=1,
                status=InterviewTopicStatus.IN_PROGRESS,
            )
        ],
    )

    assert response.current_topic is InterviewTopic.LLM_EVALUATION
    assert response.topics[0].status is InterviewTopicStatus.IN_PROGRESS


def test_complete_interview_response_constructs():
    response = CompleteInterviewResponse(
        session_id=uuid.uuid4(),
        status=InterviewStatus.COMPLETED,
        evaluation_status="PENDING",
    )

    assert response.status is InterviewStatus.COMPLETED
