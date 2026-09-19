import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import InterviewTopic, InterviewTopicStatus

if TYPE_CHECKING:
    from app.models.interview_session import InterviewSession


class InterviewTopicEntry(Base):
    """One selected topic for an interview session (`interview_topics` row).

    Named `InterviewTopicEntry` rather than `InterviewTopic` to avoid
    colliding with the `InterviewTopic` domain enum this model references.
    """

    __tablename__ = "interview_topics"
    __table_args__ = (
        CheckConstraint("sequence_number >= 1", name="ck_interview_topics_sequence_number_min"),
        UniqueConstraint("session_id", "topic", name="uq_interview_topics_session_id_topic"),
        UniqueConstraint(
            "session_id", "sequence_number", name="uq_interview_topics_session_id_sequence_number"
        ),
        Index("ix_interview_topics_session_id_status", "session_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    topic: Mapped[InterviewTopic] = mapped_column(
        Enum(InterviewTopic, native_enum=False, create_constraint=False, validate_strings=True, length=50),
        nullable=False,
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[InterviewTopicStatus] = mapped_column(
        Enum(
            InterviewTopicStatus,
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=50,
        ),
        nullable=False,
        default=InterviewTopicStatus.PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    session: Mapped["InterviewSession"] = relationship(back_populates="topics")
