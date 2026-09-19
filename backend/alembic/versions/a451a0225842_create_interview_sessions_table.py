"""create interview_sessions table

Revision ID: a451a0225842
Revises: 
Create Date: 2026-09-16 13:45:36.918121

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a451a0225842'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "interview_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("difficulty", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="CREATED"),
        sa.Column("question_limit", sa.Integer(), nullable=False),
        sa.Column("current_topic", sa.String(), nullable=True),
        sa.Column("current_question_number", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "question_limit >= 3",
            name="ck_interview_sessions_question_limit_min",
        ),
        sa.CheckConstraint(
            "current_question_number >= 0",
            name="ck_interview_sessions_current_question_number_non_negative",
        ),
        sa.CheckConstraint(
            "version >= 1",
            name="ck_interview_sessions_version_positive",
        ),
    )


def downgrade() -> None:
    op.drop_table("interview_sessions")
