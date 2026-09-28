"""create interview_resumes table

Revision ID: 910709f7043a
Revises: 373850180458
Create Date: 2026-09-28 23:35:44.192563

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '910709f7043a'
down_revision: Union[str, None] = '373850180458'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "interview_resumes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("interview_sessions.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        # Plain string, not a native PostgreSQL ENUM type — consistent with
        # every other enum-backed column in this project (see
        # app/models/*.py, all using sqlalchemy.Enum(..., native_enum=False)).
        sa.Column("extraction_status", sa.String(length=50), nullable=False, server_default="UPLOADED"),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("structured_profile", postgresql.JSONB(), nullable=True),
        sa.Column("extraction_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("interview_resumes")
