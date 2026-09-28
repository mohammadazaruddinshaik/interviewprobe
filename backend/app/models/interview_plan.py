import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import Role

if TYPE_CHECKING:
    from app.models.interview_session import InterviewSession


class InterviewPlanRecord(Base):
    """A persisted, validated InterviewPlan for an interview session.

    The JSONB `plan` column stores the serialized domain InterviewPlan
    (app/planning/models.py) — the same provider-neutral structure the
    planner produces. It contains objectives, planned topics, competency
    keys, claim IDs, priorities, and time budgets, but never raw resume
    text, contact details, prompts, or provider metadata.

    `role` is stored as a top-level column as well as inside the JSONB
    plan for easier querying/debugging; the repository ensures they match.

    Today only plan_version=1 is created. The UNIQUE(session_id,
    plan_version) constraint allows future re-planning to persist
    additional versions without requiring a schema migration.
    """

    __tablename__ = "interview_plans"
    __table_args__ = (
        UniqueConstraint(
            "session_id", "plan_version",
            name="uq_interview_plans_session_id_plan_version",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    plan_version: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[Role] = mapped_column(
        Enum(Role, native_enum=False, create_constraint=False,
             validate_strings=True, length=50),
        nullable=False,
    )
    plan: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
        onupdate=func.now(),
    )

    session: Mapped["InterviewSession"] = relationship(back_populates="plan")
