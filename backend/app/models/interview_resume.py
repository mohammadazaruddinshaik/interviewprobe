import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import ResumeExtractionStatus

if TYPE_CHECKING:
    from app.models.interview_session import InterviewSession


class InterviewResume(Base):
    """One candidate's optional resume for an interview session.

    `session_id` is unique — this project supports at most one resume per
    interview (a re-upload replaces the existing row rather than adding a
    second one; see `ResumeService`), so there is no need for a
    sequence/ordering column the way `interview_topics`/`interview_
    questions` have one. `extracted_text` is kept even when `status` is
    FAILED (whenever extraction itself succeeded but structuring did not)
    — it is the durable source evidence a later retry or later phase can
    reuse without re-parsing the original file, which is never stored.
    """

    __tablename__ = "interview_resumes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    extraction_status: Mapped[ResumeExtractionStatus] = mapped_column(
        Enum(
            ResumeExtractionStatus,
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=50,
        ),
        nullable=False,
        default=ResumeExtractionStatus.UPLOADED,
    )
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # The provider-neutral ResumeProfile (see app/resume/models.py),
    # already backend-validated (app/resume/validator.py) before it ever
    # reaches this column — never a raw, unvalidated LLM response.
    structured_profile: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    extraction_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    session: Mapped["InterviewSession"] = relationship(back_populates="resume")
