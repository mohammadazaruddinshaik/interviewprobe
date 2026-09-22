"""add unique constraint on session sequence numbers

Revision ID: 373850180458
Revises: 538fb309b1be
Create Date: 2026-09-22 13:14:43.574867

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '373850180458'
down_revision: Union[str, None] = '538fb309b1be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The plain (session_id, sequence_number) indexes are dropped in favor
    # of unique constraints on the same columns: a unique constraint
    # already creates a covering unique index, so keeping both would just
    # be a redundant index maintained on every insert. Same approach as
    # interview_topics' (session_id, sequence_number) constraint.
    op.drop_index("ix_interview_questions_session_id_sequence_number", table_name="interview_questions")
    op.create_unique_constraint(
        "uq_interview_questions_session_id_sequence_number",
        "interview_questions",
        ["session_id", "sequence_number"],
    )

    op.drop_index("ix_interview_messages_session_id_sequence_number", table_name="interview_messages")
    op.create_unique_constraint(
        "uq_interview_messages_session_id_sequence_number",
        "interview_messages",
        ["session_id", "sequence_number"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_interview_messages_session_id_sequence_number", "interview_messages", type_="unique"
    )
    op.create_index(
        "ix_interview_messages_session_id_sequence_number",
        "interview_messages",
        ["session_id", "sequence_number"],
    )

    op.drop_constraint(
        "uq_interview_questions_session_id_sequence_number", "interview_questions", type_="unique"
    )
    op.create_index(
        "ix_interview_questions_session_id_sequence_number",
        "interview_questions",
        ["session_id", "sequence_number"],
    )
