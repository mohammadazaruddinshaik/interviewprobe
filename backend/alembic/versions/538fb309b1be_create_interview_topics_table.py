"""create interview_topics table

Revision ID: 538fb309b1be
Revises: d00c8abb5098
Create Date: 2026-09-16 16:13:40.301989

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '538fb309b1be'
down_revision: Union[str, None] = 'd00c8abb5098'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "interview_topics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("interview_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # `topic` and `status` are plain strings, not native PostgreSQL
        # ENUM types — consistent with every other enum-backed column in
        # this project (see app/models/*.py, all using
        # sqlalchemy.Enum(..., native_enum=False)).
        sa.Column("topic", sa.String(length=50), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "sequence_number >= 1",
            name="ck_interview_topics_sequence_number_min",
        ),
        sa.UniqueConstraint("session_id", "topic", name="uq_interview_topics_session_id_topic"),
        sa.UniqueConstraint(
            "session_id",
            "sequence_number",
            name="uq_interview_topics_session_id_sequence_number",
        ),
    )
    # (session_id, sequence_number) already has a unique index from the
    # UniqueConstraint above; this adds the separate (session_id, status)
    # index requested for status-filtered lookups.
    op.create_index(
        "ix_interview_topics_session_id_status",
        "interview_topics",
        ["session_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_interview_topics_session_id_status", table_name="interview_topics")
    op.drop_table("interview_topics")
