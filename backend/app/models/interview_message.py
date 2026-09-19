import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import MessageRole

if TYPE_CHECKING:
    from app.models.interview_question import InterviewQuestion
    from app.models.interview_session import InterviewSession


class InterviewMessage(Base):
    __tablename__ = "interview_messages"
    __table_args__ = (
        CheckConstraint("sequence_number >= 1", name="ck_interview_messages_sequence_number_min"),
        Index("ix_interview_messages_session_id_sequence_number", "session_id", "sequence_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_questions.id"),
        nullable=True,
    )
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, native_enum=False, create_constraint=False, validate_strings=True, length=50),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    session: Mapped["InterviewSession"] = relationship(back_populates="messages")
    question: Mapped["InterviewQuestion | None"] = relationship(back_populates="messages")
