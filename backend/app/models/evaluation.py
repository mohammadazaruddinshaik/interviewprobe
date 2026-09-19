import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.interview_session import InterviewSession


class Evaluation(Base):
    __tablename__ = "evaluations"
    __table_args__ = (
        CheckConstraint(
            "technical_knowledge_score >= 0 AND technical_knowledge_score <= 10",
            name="ck_evaluations_technical_knowledge_score_range",
        ),
        CheckConstraint(
            "reasoning_score >= 0 AND reasoning_score <= 10",
            name="ck_evaluations_reasoning_score_range",
        ),
        CheckConstraint(
            "depth_score >= 0 AND depth_score <= 10",
            name="ck_evaluations_depth_score_range",
        ),
        CheckConstraint(
            "communication_score >= 0 AND communication_score <= 10",
            name="ck_evaluations_communication_score_range",
        ),
        CheckConstraint(
            "overall_score >= 0 AND overall_score <= 10",
            name="ck_evaluations_overall_score_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    technical_knowledge_score: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    reasoning_score: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    depth_score: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    communication_score: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    overall_score: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    strengths: Mapped[dict] = mapped_column(JSONB, nullable=False)
    weaknesses: Mapped[dict] = mapped_column(JSONB, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    session: Mapped["InterviewSession"] = relationship(back_populates="evaluation")
