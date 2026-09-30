import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, case, func, select
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import FunctionElement

from app.domain.enums import InterviewStatus, InterviewTopicStatus
from app.models.evaluation import Evaluation
from app.models.interview_session import InterviewSession
from app.models.interview_topic import InterviewTopicEntry


class utc_date(FunctionElement):
    """The UTC calendar date of a timestamptz column (never the DB session's
    time zone). SQLite (tests) stores UTC, so plain `date()` is equivalent."""

    type = Date()
    name = "utc_date"
    inherit_cache = True


@compiles(utc_date)
def _utc_date_default(element, compiler, **kw):
    return f"CAST(timezone('UTC', {compiler.process(element.clauses, **kw)}) AS DATE)"


@compiles(utc_date, "sqlite")
def _utc_date_sqlite(element, compiler, **kw):
    return f"date({compiler.process(element.clauses, **kw)})"


@dataclass(frozen=True)
class CompletionStats:
    completed_total: int
    completed_in_current_month: int
    average_score: Decimal | float | None
    average_score_current_month: Decimal | float | None
    average_score_previous_month: Decimal | float | None


@dataclass(frozen=True)
class RecentInterviewRow:
    session: InterviewSession
    overall_score: Decimal | float | None


class DashboardRepository:
    """Read-only, aggregate queries for the dashboard. Every query is scoped
    by `user_id` in SQL (never filtered in Python) and reads only persisted
    rows — no LLM, no EvaluationService, no transcripts."""

    def __init__(self, session: Session, user_id: uuid.UUID):
        self.session = session
        self.user_id = user_id

    def completion_stats(
        self, month_start: datetime, next_month_start: datetime, previous_month_start: datetime
    ) -> CompletionStats:
        s, e = InterviewSession, Evaluation
        in_current = (s.completed_at >= month_start) & (s.completed_at < next_month_start)
        in_previous = (s.completed_at >= previous_month_start) & (s.completed_at < month_start)
        row = self.session.execute(
            select(
                func.count(s.id),
                func.count(case((in_current, s.id))),
                func.avg(e.overall_score),
                func.avg(case((in_current, e.overall_score))),
                func.avg(case((in_previous, e.overall_score))),
            )
            .select_from(s)
            .outerjoin(e, e.session_id == s.id)  # 1:1 (evaluations.session_id is unique), so no row fan-out
            .where(s.user_id == self.user_id, s.status == InterviewStatus.COMPLETED)
        ).one()
        return CompletionStats(*row)

    def count_practiced_topics(self) -> int:
        t, s = InterviewTopicEntry, InterviewSession
        return self.session.execute(
            select(func.count(func.distinct(t.topic)))
            .select_from(t)
            .join(s, s.id == t.session_id)
            .where(
                s.user_id == self.user_id,
                t.status.in_([InterviewTopicStatus.IN_PROGRESS, InterviewTopicStatus.COMPLETED]),
            )
        ).scalar_one()

    def get_next_interview(self) -> InterviewSession | None:
        s = InterviewSession
        return self.session.execute(
            select(s)
            .where(s.user_id == self.user_id, s.status.in_([InterviewStatus.IN_PROGRESS, InterviewStatus.CREATED]))
            .order_by(case((s.status == InterviewStatus.IN_PROGRESS, 0), else_=1), s.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()

    def recent_completed(self, limit: int) -> list[RecentInterviewRow]:
        s, e = InterviewSession, Evaluation
        rows = self.session.execute(
            select(s, e.overall_score)
            .outerjoin(e, e.session_id == s.id)
            .where(s.user_id == self.user_id, s.status == InterviewStatus.COMPLETED)
            .order_by(func.coalesce(s.completed_at, s.created_at).desc(), s.id)
            .limit(limit)
        ).all()
        return [RecentInterviewRow(session=row[0], overall_score=row[1]) for row in rows]

    def topics_for_sessions(self, session_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[InterviewTopicEntry]]:
        if not session_ids:
            return {}
        t = InterviewTopicEntry
        grouped: dict[uuid.UUID, list[InterviewTopicEntry]] = {sid: [] for sid in session_ids}
        # Scoped through the owner's sessions (defense in depth) and bounded by `session_ids` (<= the recent limit).
        rows = self.session.execute(
            select(t)
            .join(InterviewSession, InterviewSession.id == t.session_id)
            .where(InterviewSession.user_id == self.user_id, t.session_id.in_(session_ids))
            .order_by(t.session_id, t.sequence_number)
        ).scalars()
        for topic in rows:
            grouped[topic.session_id].append(topic)
        return grouped

    def active_dates_since(self, since: datetime) -> set[date]:
        """Distinct UTC calendar dates with at least one completed interview
        since `since` — at most one row per day, so the result is bounded."""
        s = InterviewSession
        day = utc_date(s.completed_at)
        rows = self.session.execute(
            select(day)
            .where(s.user_id == self.user_id, s.status == InterviewStatus.COMPLETED, s.completed_at >= since)
            .group_by(day)
        ).scalars()
        return set(rows)
