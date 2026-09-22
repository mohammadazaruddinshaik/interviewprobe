import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import Difficulty, InterviewTopic, QuestionType

if TYPE_CHECKING:
    from app.models.interview_message import InterviewMessage
    from app.models.interview_session import InterviewSession


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"
    __table_args__ = (
        CheckConstraint("sequence_number >= 1", name="ck_interview_questions_sequence_number_min"),
        # Replaces the old plain index of the same columns: a unique
        # constraint already creates a covering unique index, so keeping
        # both would just be a redundant index maintained on every insert.
        # Same approach as InterviewTopicEntry's (session_id,
        # sequence_number) constraint.
        UniqueConstraint(
            "session_id", "sequence_number", name="uq_interview_questions_session_id_sequence_number"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    topic: Mapped[InterviewTopic] = mapped_column(
        Enum(InterviewTopic, native_enum=False, create_constraint=False, validate_strings=True, length=50),
        nullable=False,
    )
    difficulty: Mapped[Difficulty] = mapped_column(
        Enum(Difficulty, native_enum=False, create_constraint=False, validate_strings=True, length=50),
        nullable=False,
    )
    question_type: Mapped[QuestionType] = mapped_column(
        Enum(QuestionType, native_enum=False, create_constraint=False, validate_strings=True, length=50),
        nullable=False,
    )
    agent_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    session: Mapped["InterviewSession"] = relationship(back_populates="questions")
    messages: Mapped[list["InterviewMessage"]] = relationship(back_populates="question")
