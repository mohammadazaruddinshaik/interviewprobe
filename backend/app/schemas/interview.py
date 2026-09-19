from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import (
    Difficulty,
    InterviewStatus,
    InterviewTopic,
    InterviewTopicStatus,
    QuestionType,
    Role,
)


class CreateInterviewRequest(BaseModel):
    role: Role
    difficulty: Difficulty
    topics: list[InterviewTopic] = Field(min_length=1, max_length=6)
    question_limit: int = Field(ge=3, le=10)

    @field_validator("topics")
    @classmethod
    def topics_must_be_unique(cls, value: list[InterviewTopic]) -> list[InterviewTopic]:
        if len(set(value)) != len(value):
            raise ValueError("topics must not contain duplicates")
        return value


class CreateInterviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: Role
    difficulty: Difficulty
    topics: list[InterviewTopic]
    question_limit: int
    status: InterviewStatus


class QuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sequence: int
    text: str
    topic: InterviewTopic
    difficulty: Difficulty
    type: QuestionType


class StartInterviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: UUID
    status: InterviewStatus
    question: QuestionResponse


class SubmitAnswerRequest(BaseModel):
    question_id: UUID
    answer: str = Field(max_length=10_000)

    @field_validator("answer", mode="before")
    @classmethod
    def strip_and_reject_empty_answer(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("answer must not be empty")
            return stripped
        return value


class SubmitAnswerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: UUID
    status: InterviewStatus
    action: str
    question: QuestionResponse | None = None
    evaluation_status: str | None = None


class InterviewTopicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    topic: InterviewTopic
    sequence_number: int
    status: InterviewTopicStatus


class InterviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: UUID
    role: Role
    difficulty: Difficulty
    status: InterviewStatus
    question_limit: int
    current_topic: InterviewTopic | None
    current_question_number: int
    questions_answered: int
    topics: list[InterviewTopicResponse]
    # Task 27: the question currently awaiting a candidate answer — null
    # before the interview is started (CREATED) and once it's COMPLETED
    # (its last question has already been answered). Reuses QuestionResponse
    # rather than a new schema, since the shape is identical to start/answer.
    current_question: QuestionResponse | None = None


class CompleteInterviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: UUID
    status: InterviewStatus
    evaluation_status: str


class EvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: UUID
    technical_knowledge_score: float = Field(ge=0, le=10)
    reasoning_score: float = Field(ge=0, le=10)
    depth_score: float = Field(ge=0, le=10)
    communication_score: float = Field(ge=0, le=10)
    overall_score: float = Field(ge=0, le=10)
    strengths: list[str]
    weaknesses: list[str]
    evidence: list[dict]


# ---------------------------------------------------------------------------
# Result (Task 22) — the candidate-facing interview report. Reuses
# `InterviewTopicResponse`/`EvaluationResponse` as-is; `ResultQuestionResponse`
# is `QuestionResponse` plus the one field a report needs that a live
# in-progress view doesn't: the candidate's answer to that question.
# ---------------------------------------------------------------------------


class ResultInterviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: UUID
    role: Role
    difficulty: Difficulty
    status: InterviewStatus
    question_limit: int
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class ResultQuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sequence: int
    text: str
    topic: InterviewTopic
    difficulty: Difficulty
    type: QuestionType
    # `None` when the candidate never answered this question (e.g. the
    # interview was completed via `/complete` before reaching it) — never
    # fabricated, never omitted from the list.
    candidate_answer: str | None = None


class InterviewResultResponse(BaseModel):
    interview: ResultInterviewResponse
    topics: list[InterviewTopicResponse]
    questions: list[ResultQuestionResponse]
    evaluation: EvaluationResponse
