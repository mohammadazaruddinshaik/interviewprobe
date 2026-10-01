from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from app.domain.enums import InterviewStatus
from app.repositories.dashboard_repository import DashboardRepository
from app.schemas.dashboard import (
    DashboardActivityDay,
    DashboardNextInterview,
    DashboardRecentInterview,
    DashboardResponse,
    DashboardStats,
    DashboardStreak,
)

RECENT_INTERVIEWS_LIMIT = 5
ACTIVITY_WINDOW_DAYS = 7
# The streak is computed from at most this many days of activity (one row per
# active day), so a streak longer than this is reported as STREAK_LOOKBACK_DAYS.
STREAK_LOOKBACK_DAYS = 365


def _month_start(moment: datetime) -> datetime:
    return moment.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _add_month(month_start: datetime, delta: int) -> datetime:
    index = month_start.year * 12 + (month_start.month - 1) + delta
    return month_start.replace(year=index // 12, month=index % 12 + 1)


def _to_float(value: Decimal | float | None, places: int = 2) -> float | None:
    return None if value is None else round(float(value), places)


def compute_streak_days(active_dates: set[date], today: date) -> int:
    """Consecutive active UTC calendar days ending today — or ending
    yesterday when today has no activity YET (a streak is still alive until
    the day is over). Several interviews on one day count once. A gap of a
    full inactive day before today resets it to 0."""
    cursor = today if today in active_dates else today - timedelta(days=1)
    days = 0
    while cursor in active_dates and days < STREAK_LOOKBACK_DAYS:
        days += 1
        cursor -= timedelta(days=1)
    return days


class DashboardService:
    """Assembles the dashboard from persisted data only. Everything is UTC
    (no per-user time zones yet). No LLM, LangGraph or EvaluationService.

    Semantics:
    - completed_interviews / averages / recents: sessions with status COMPLETED.
    - average_score: mean of persisted evaluations.overall_score (0-10); sessions
      without an evaluation are excluded from the mean.
    - average_score_change: (current-month avg - previous-month avg) / previous-month avg.
    - topics_practiced: distinct topics whose interview_topics.status is IN_PROGRESS
      or COMPLETED (the last topic of a finished interview stays IN_PROGRESS, so
      requiring COMPLETED would undercount; PENDING topics were never asked).
    - new_topics_this_month: NOT provided. interview_topics.created_at is when the
      topic was SELECTED for a session, not when it was first practiced, so a
      "first practiced" date cannot be derived reliably.
    - next_interview: the latest IN_PROGRESS session, else the latest CREATED one.
    - streak: see compute_streak_days.
    """

    def __init__(self, repository: DashboardRepository):
        self.repository = repository

    def get_dashboard(self, now: datetime | None = None) -> DashboardResponse:
        now = (now or datetime.now(UTC)).astimezone(UTC)
        month_start = _month_start(now)
        next_month_start = _add_month(month_start, 1)
        previous_month_start = _add_month(month_start, -1)

        stats = self.repository.completion_stats(month_start, next_month_start, previous_month_start)
        current_avg = _to_float(stats.average_score_current_month, 6)
        previous_avg = _to_float(stats.average_score_previous_month, 6)
        change = None
        if current_avg is not None and previous_avg:  # previous_avg None or 0 -> no meaningful comparison
            change = round((current_avg - previous_avg) / previous_avg, 4)

        next_session = self.repository.get_next_interview()
        recent_rows = self.repository.recent_completed(RECENT_INTERVIEWS_LIMIT)
        topics_by_session = self.repository.topics_for_sessions([row.session.id for row in recent_rows])

        today = now.date()
        lookback_start = (now - timedelta(days=STREAK_LOOKBACK_DAYS)).replace(hour=0, minute=0, second=0, microsecond=0)
        active_dates = self.repository.active_dates_since(lookback_start)

        return DashboardResponse(
            stats=DashboardStats(
                completed_interviews=stats.completed_total,
                average_score=_to_float(stats.average_score),
                completed_this_month=stats.completed_in_current_month,
                average_score_change=change,
                topics_practiced=self.repository.count_practiced_topics(),
            ),
            next_interview=(
                None
                if next_session is None
                else DashboardNextInterview(
                    id=next_session.id,
                    role=next_session.role,
                    difficulty=None if next_session.status is InterviewStatus.CREATED else next_session.difficulty,
                    question_limit=(
                        None if next_session.status is InterviewStatus.CREATED else next_session.question_limit
                    ),
                    status=next_session.status,
                )
            ),
            recent_interviews=[
                DashboardRecentInterview(
                    id=row.session.id,
                    role=row.session.role,
                    difficulty=row.session.difficulty,
                    status=row.session.status,
                    topics=[t.topic for t in topics_by_session.get(row.session.id, [])],
                    overall_score=_to_float(row.overall_score),
                    completed_at=row.session.completed_at,
                    created_at=row.session.created_at,
                )
                for row in recent_rows
            ],
            streak=DashboardStreak(
                days=compute_streak_days(active_dates, today),
                activity=[
                    DashboardActivityDay(date=day, active=day in active_dates)
                    for day in (today - timedelta(days=offset) for offset in range(ACTIVITY_WINDOW_DAYS - 1, -1, -1))
                ],
            ),
        )
