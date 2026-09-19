from enum import StrEnum

from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import configure_mappers

from app.domain.enums import (
    Difficulty,
    InterviewStatus,
    InterviewTopic,
    MessageRole,
    QuestionType,
    Role,
)
from app.models.interview_message import InterviewMessage
from app.models.interview_question import InterviewQuestion
from app.models.interview_session import InterviewSession


def test_enums_are_str_enums():
    for enum_cls in (Role, Difficulty, InterviewStatus, InterviewTopic, QuestionType, MessageRole):
        assert issubclass(enum_cls, StrEnum)


def test_role_members():
    # Task 16 made this role-agnostic — assert the full, exact set so a
    # future accidental addition/removal is still caught.
    assert {member.value for member in Role} == {
        "AI_ENGINEER",
        "FRONTEND_DEVELOPER",
        "BACKEND_DEVELOPER",
        "JAVA_DEVELOPER",
    }


def test_difficulty_members():
    assert {member.value for member in Difficulty} == {"EASY", "MEDIUM", "HARD"}


def test_interview_status_members():
    assert {member.value for member in InterviewStatus} == {
        "CREATED",
        "IN_PROGRESS",
        "COMPLETED",
        "FAILED",
    }


def test_interview_topic_members():
    # The original AI Engineer topics must remain exactly as they were —
    # Task 16 must not rename/remove any of them, since they're already
    # used throughout the workflow/tests. New roles only ever *add*
    # topics, so this is a subset check, not an exact-set check.
    original_ai_engineer_topics = {
        "LLM_FUNDAMENTALS",
        "RAG",
        "EMBEDDINGS_VECTOR_DB",
        "AI_AGENTS",
        "LLM_EVALUATION",
        "AI_SYSTEM_DESIGN",
    }
    assert original_ai_engineer_topics <= {member.value for member in InterviewTopic}


def test_question_type_members():
    assert {member.value for member in QuestionType} == {
        "INITIAL",
        "FOLLOW_UP",
        "CLARIFICATION",
        "TOPIC_TRANSITION",
    }


def test_message_role_members():
    assert {member.value for member in MessageRole} == {"INTERVIEWER", "CANDIDATE", "SYSTEM"}


def test_interview_session_uses_domain_enums():
    table = InterviewSession.__table__

    for column_name, enum_cls in (
        ("role", Role),
        ("difficulty", Difficulty),
        ("status", InterviewStatus),
    ):
        column_type = table.c[column_name].type
        assert isinstance(column_type, SAEnum)
        assert column_type.enum_class is enum_cls
        assert column_type.native_enum is False


def test_interview_question_uses_domain_enums():
    table = InterviewQuestion.__table__

    for column_name, enum_cls in (
        ("topic", InterviewTopic),
        ("difficulty", Difficulty),
        ("question_type", QuestionType),
    ):
        column_type = table.c[column_name].type
        assert isinstance(column_type, SAEnum)
        assert column_type.enum_class is enum_cls
        assert column_type.native_enum is False


def test_interview_message_uses_domain_enum():
    column_type = InterviewMessage.__table__.c["role"].type

    assert isinstance(column_type, SAEnum)
    assert column_type.enum_class is MessageRole
    assert column_type.native_enum is False


def test_mapper_configuration_still_succeeds():
    configure_mappers()
