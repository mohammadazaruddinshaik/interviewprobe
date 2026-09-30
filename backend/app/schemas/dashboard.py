from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel

from app.domain.enums import Difficulty, InterviewStatus, InterviewTopic, Role


class DashboardStats(BaseModel):
    # Completed interviews owned by the current user.
    completed_interviews: int
    # Mean of persisted `evaluations.overall_score` (native 0-10 scale) over
    # the user's completed interviews that HAVE an evaluation; null if none.
    average_score: float | None
    # Completed interviews whose `completed_at` is in the current UTC month.
    completed_this_month: int
    # Relative change of the current-UTC-month average score vs the previous
    # UTC month's, as a fraction (0.12 == +12%). Null unless both months have
    # at least one evaluated interview and the previous average is > 0.
    average_score_change: float | None
    # Distinct topics the user actually reached (interview_topics.status is
    # IN_PROGRESS or COMPLETED; PENDING topics were never asked).
    topics_practiced: int
    # Deliberately not returned: the schema has no reliable "first practiced"
    # timestamp (see DashboardService docs), so `new_topics_this_month` is omitted.


class DashboardNextInterview(BaseModel):
    id: UUID
    role: Role
    difficulty: Difficulty
    question_limit: int
    status: InterviewStatus


class DashboardRecentInterview(BaseModel):
    id: UUID
    role: Role
    difficulty: Difficulty
    status: InterviewStatus
    # Enum values (e.g. REST_APIS), in the order the user selected them.
    topics: list[InterviewTopic]
    overall_score: float | None
    completed_at: datetime | None
    created_at: datetime


class DashboardActivityDay(BaseModel):
    date: date
    active: bool


class DashboardStreak(BaseModel):
    days: int
    # The last 7 UTC calendar days, oldest first, ending today.
    activity: list[DashboardActivityDay]


class DashboardResponse(BaseModel):
    stats: DashboardStats
    next_interview: DashboardNextInterview | None
    recent_interviews: list[DashboardRecentInterview]
    streak: DashboardStreak
