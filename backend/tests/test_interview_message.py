from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.models.interview_message import InterviewMessage


def test_interview_message_importable():
    assert InterviewMessage.__tablename__ == "interview_messages"


def test_interview_message_columns_present():
    columns = {c.name for c in InterviewMessage.__table__.columns}
    expected = {
        "id",
        "session_id",
        "question_id",
        "role",
        "content",
        "sequence_number",
        "created_at",
    }
    assert expected == columns


def test_interview_message_primary_key_is_uuid():
    table = InterviewMessage.__table__
    pk_columns = list(table.primary_key.columns)

    assert len(pk_columns) == 1
    assert pk_columns[0].name == "id"
    assert isinstance(table.c.id.type, UUID)


def test_interview_message_foreign_keys():
    table = InterviewMessage.__table__

    session_fks = list(table.c.session_id.foreign_keys)
    assert len(session_fks) == 1
    assert session_fks[0].target_fullname == "interview_sessions.id"
    assert session_fks[0].ondelete == "CASCADE"

    question_fks = list(table.c.question_id.foreign_keys)
    assert len(question_fks) == 1
    assert question_fks[0].target_fullname == "interview_questions.id"


def test_interview_message_question_id_nullable():
    assert InterviewMessage.__table__.c.question_id.nullable is True


def test_interview_message_sequence_number_constraint():
    check_constraints = {
        constraint.name: str(constraint.sqltext)
        for constraint in InterviewMessage.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert check_constraints["ck_interview_messages_sequence_number_min"] == "sequence_number >= 1"


def test_interview_message_session_sequence_unique_constraint():
    unique_constraints = {
        constraint.name: [c.name for c in constraint.columns]
        for constraint in InterviewMessage.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert unique_constraints["uq_interview_messages_session_id_sequence_number"] == [
        "session_id",
        "sequence_number",
    ]
