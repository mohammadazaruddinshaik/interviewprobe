from sqlalchemy import CheckConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.models.interview_question import InterviewQuestion


def test_interview_question_importable():
    assert InterviewQuestion.__tablename__ == "interview_questions"


def test_interview_question_columns_present():
    columns = {c.name for c in InterviewQuestion.__table__.columns}
    expected = {
        "id",
        "session_id",
        "sequence_number",
        "question_text",
        "topic",
        "difficulty",
        "question_type",
        "agent_reason",
        "created_at",
    }
    assert expected == columns


def test_interview_question_primary_key_is_uuid():
    table = InterviewQuestion.__table__
    pk_columns = list(table.primary_key.columns)

    assert len(pk_columns) == 1
    assert pk_columns[0].name == "id"
    assert isinstance(table.c.id.type, UUID)


def test_interview_question_session_foreign_key():
    fks = list(InterviewQuestion.__table__.c.session_id.foreign_keys)

    assert len(fks) == 1
    assert fks[0].target_fullname == "interview_sessions.id"
    assert fks[0].ondelete == "CASCADE"


def test_interview_question_sequence_number_constraint():
    check_constraints = {
        constraint.name: str(constraint.sqltext)
        for constraint in InterviewQuestion.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert check_constraints["ck_interview_questions_sequence_number_min"] == "sequence_number >= 1"


def test_interview_question_session_sequence_index():
    index_names = {index.name: [c.name for c in index.columns] for index in InterviewQuestion.__table__.indexes}

    assert index_names["ix_interview_questions_session_id_sequence_number"] == [
        "session_id",
        "sequence_number",
    ]
