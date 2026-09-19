from sqlalchemy import CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.evaluation import Evaluation


def test_evaluation_importable():
    assert Evaluation.__tablename__ == "evaluations"


def test_evaluation_columns_present():
    columns = {c.name for c in Evaluation.__table__.columns}
    expected = {
        "id",
        "session_id",
        "technical_knowledge_score",
        "reasoning_score",
        "depth_score",
        "communication_score",
        "overall_score",
        "strengths",
        "weaknesses",
        "evidence",
        "created_at",
        "updated_at",
    }
    assert expected == columns


def test_evaluation_primary_key_is_uuid():
    table = Evaluation.__table__
    pk_columns = list(table.primary_key.columns)

    assert len(pk_columns) == 1
    assert pk_columns[0].name == "id"
    assert isinstance(table.c.id.type, UUID)


def test_evaluation_session_id_is_unique_foreign_key():
    table = Evaluation.__table__

    assert table.c.session_id.unique is True

    fks = list(table.c.session_id.foreign_keys)
    assert len(fks) == 1
    assert fks[0].target_fullname == "interview_sessions.id"
    assert fks[0].ondelete == "CASCADE"


def test_evaluation_score_columns_present():
    table = Evaluation.__table__
    for column_name in (
        "technical_knowledge_score",
        "reasoning_score",
        "depth_score",
        "communication_score",
        "overall_score",
    ):
        assert column_name in table.c
        assert table.c[column_name].nullable is False


def test_evaluation_jsonb_fields_present():
    table = Evaluation.__table__
    for column_name in ("strengths", "weaknesses", "evidence"):
        assert isinstance(table.c[column_name].type, JSONB)


def test_evaluation_score_check_constraints_present():
    check_constraints = {
        constraint.name: str(constraint.sqltext)
        for constraint in Evaluation.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert check_constraints["ck_evaluations_technical_knowledge_score_range"] == (
        "technical_knowledge_score >= 0 AND technical_knowledge_score <= 10"
    )
    assert check_constraints["ck_evaluations_reasoning_score_range"] == (
        "reasoning_score >= 0 AND reasoning_score <= 10"
    )
    assert check_constraints["ck_evaluations_depth_score_range"] == (
        "depth_score >= 0 AND depth_score <= 10"
    )
    assert check_constraints["ck_evaluations_communication_score_range"] == (
        "communication_score >= 0 AND communication_score <= 10"
    )
    assert check_constraints["ck_evaluations_overall_score_range"] == (
        "overall_score >= 0 AND overall_score <= 10"
    )
