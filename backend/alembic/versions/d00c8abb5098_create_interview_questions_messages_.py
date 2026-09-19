"""create interview questions messages evaluations tables

Revision ID: d00c8abb5098
Revises: a451a0225842
Create Date: 2026-09-16 15:15:59.904285

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd00c8abb5098'
down_revision: Union[str, None] = 'a451a0225842'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "interview_questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("interview_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("topic", sa.String(), nullable=False),
        sa.Column("difficulty", sa.String(), nullable=False),
        sa.Column("question_type", sa.String(), nullable=False),
        sa.Column("agent_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "sequence_number >= 1",
            name="ck_interview_questions_sequence_number_min",
        ),
    )
    op.create_index(
        "ix_interview_questions_session_id_sequence_number",
        "interview_questions",
        ["session_id", "sequence_number"],
    )

    op.create_table(
        "interview_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("interview_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "question_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("interview_questions.id"),
            nullable=True,
        ),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "sequence_number >= 1",
            name="ck_interview_messages_sequence_number_min",
        ),
    )
    op.create_index(
        "ix_interview_messages_session_id_sequence_number",
        "interview_messages",
        ["session_id", "sequence_number"],
    )

    op.create_table(
        "evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("interview_sessions.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("technical_knowledge_score", sa.Numeric(4, 2), nullable=False),
        sa.Column("reasoning_score", sa.Numeric(4, 2), nullable=False),
        sa.Column("depth_score", sa.Numeric(4, 2), nullable=False),
        sa.Column("communication_score", sa.Numeric(4, 2), nullable=False),
        sa.Column("overall_score", sa.Numeric(4, 2), nullable=False),
        sa.Column("strengths", postgresql.JSONB(), nullable=False),
        sa.Column("weaknesses", postgresql.JSONB(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "technical_knowledge_score >= 0 AND technical_knowledge_score <= 10",
            name="ck_evaluations_technical_knowledge_score_range",
        ),
        sa.CheckConstraint(
            "reasoning_score >= 0 AND reasoning_score <= 10",
            name="ck_evaluations_reasoning_score_range",
        ),
        sa.CheckConstraint(
            "depth_score >= 0 AND depth_score <= 10",
            name="ck_evaluations_depth_score_range",
        ),
        sa.CheckConstraint(
            "communication_score >= 0 AND communication_score <= 10",
            name="ck_evaluations_communication_score_range",
        ),
        sa.CheckConstraint(
            "overall_score >= 0 AND overall_score <= 10",
            name="ck_evaluations_overall_score_range",
        ),
    )


def downgrade() -> None:
    op.drop_table("evaluations")
    op.drop_index("ix_interview_messages_session_id_sequence_number", table_name="interview_messages")
    op.drop_table("interview_messages")
    op.drop_index("ix_interview_questions_session_id_sequence_number", table_name="interview_questions")
    op.drop_table("interview_questions")
