"""add composite index for dashboard queries

Revision ID: d4b8c2e1a7f3
Revises: c7a1e4f29b10
Create Date: 2026-10-01 00:00:00.000000

Every dashboard query filters interview_sessions by user_id and status, and
the recent/streak/month queries additionally range-filter or order by
completed_at. (user_id, status, completed_at) serves all of them. Topic and
evaluation access already use existing indexes (interview_topics.session_id,
evaluations.session_id unique), so nothing else is added.
"""
from typing import Sequence, Union

from alembic import op

revision: str = 'd4b8c2e1a7f3'
down_revision: Union[str, None] = 'c7a1e4f29b10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        'ix_interview_sessions_user_id_status_completed_at',
        'interview_sessions',
        ['user_id', 'status', 'completed_at'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_interview_sessions_user_id_status_completed_at', table_name='interview_sessions')
