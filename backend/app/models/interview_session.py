import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Enum, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import Difficulty, InterviewStatus, Role

if TYPE_CHECKING:
    from app.models.evaluation import Evaluation
    from app.models.interview_message import InterviewMessage
    from app.models.interview_question import InterviewQuestion
    from app.models.interview_topic import InterviewTopicEntry


class InterviewSession(Base):
    __tablename__ = "interview_sessions"
    __table_args__ = (
        CheckConstraint(
            "question_limit >= 3",
            name="ck_interview_sessions_question_limit_min",
        ),
        CheckConstraint(
            "current_question_number >= 0",
            name="ck_interview_sessions_current_question_number_non_negative",
        ),
        CheckConstraint(
            "version >= 1",
            name="ck_interview_sessions_version_positive",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role: Mapped[Role] = mapped_column(
        Enum(Role, native_enum=False, create_constraint=False, validate_strings=True, length=50),
        nullable=False,
    )
    difficulty: Mapped[Difficulty] = mapped_column(
        Enum(Difficulty, native_enum=False, create_constraint=False, validate_strings=True, length=50),
        nullable=False,
    )
    status: Mapped[InterviewStatus] = mapped_column(
        Enum(InterviewStatus, native_enum=False, create_constraint=False, validate_strings=True, length=50),
        nullable=False,
        default=InterviewStatus.CREATED,
    )
    question_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    current_topic: Mapped[str | None] = mapped_column(String, nullable=True)
    current_question_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    questions: Mapped[list["InterviewQuestion"]] = relationship(back_populates="session")
    messages: Mapped[list["InterviewMessage"]] = relationship(back_populates="session")
    evaluation: Mapped["Evaluation | None"] = relationship(back_populates="session", uselist=False)
    # passive_deletes=True: on session delete, let the DB's ON DELETE
    # CASCADE (the interview_topics.session_id foreign key) remove topic
    # rows, instead of the ORM loading them and nulling out session_id
    # (which would violate its NOT NULL constraint).
    topics: Mapped[list["InterviewTopicEntry"]] = relationship(
        back_populates="session",
        order_by="InterviewTopicEntry.sequence_number",
        passive_deletes=True,
    )
