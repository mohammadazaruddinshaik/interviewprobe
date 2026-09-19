from sqlalchemy import CheckConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.models.interview_session import InterviewSession


def test_interview_session_importable():
    assert InterviewSession.__tablename__ == "interview_sessions"


def test_interview_session_columns_present():
    columns = {c.name for c in InterviewSession.__table__.columns}
    expected = {
        "id",
        "role",
        "difficulty",
        "status",
        "question_limit",
        "current_topic",
        "current_question_number",
        "version",
        "started_at",
        "completed_at",
        "created_at",
        "updated_at",
    }
    assert expected == columns


def test_interview_session_primary_key_is_uuid():
    table = InterviewSession.__table__
    pk_columns = list(table.primary_key.columns)

    assert len(pk_columns) == 1
    assert pk_columns[0].name == "id"
    assert isinstance(table.c.id.type, UUID)


def test_interview_session_nullable_fields():
    table = InterviewSession.__table__

    assert table.c.current_topic.nullable is True
    assert table.c.started_at.nullable is True
    assert table.c.completed_at.nullable is True

    for column_name in (
        "role",
        "difficulty",
        "status",
        "question_limit",
        "current_question_number",
        "version",
        "created_at",
        "updated_at",
    ):
        assert table.c[column_name].nullable is False


def test_interview_session_check_constraints_present():
    check_constraints = {
        constraint.name: str(constraint.sqltext)
        for constraint in InterviewSession.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert len(check_constraints) == 3
    assert check_constraints["ck_interview_sessions_question_limit_min"] == "question_limit >= 3"
    assert (
        check_constraints["ck_interview_sessions_current_question_number_non_negative"]
        == "current_question_number >= 0"
    )
    assert check_constraints["ck_interview_sessions_version_positive"] == "version >= 1"
