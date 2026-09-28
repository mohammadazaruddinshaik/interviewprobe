import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import InterviewTopicStatus
from app.models.evaluation import Evaluation
from app.models.interview_message import InterviewMessage
from app.models.interview_plan import InterviewPlanRecord
from app.models.interview_question import InterviewQuestion
from app.models.interview_resume import InterviewResume
from app.models.interview_session import InterviewSession
from app.models.interview_topic import InterviewTopicEntry
from app.planning.models import InterviewPlan


class InterviewRepository:
    """SQLAlchemy data access for the interview domain.

    Owns queries, persistence, and flushes. Does not commit or manage the
    overall transaction boundary — that belongs to the caller (eventually
    the service layer).
    """

    def __init__(self, session: Session):
        self.session = session

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    def create_session(self, interview_session: InterviewSession) -> InterviewSession:
        self.session.add(interview_session)
        self.session.flush()
        return interview_session

    def get_session(self, session_id: uuid.UUID) -> InterviewSession | None:
        return self.session.get(InterviewSession, session_id)

    def update_session(self, interview_session: InterviewSession, **changes: Any) -> InterviewSession:
        for field, value in changes.items():
            setattr(interview_session, field, value)
        self.session.flush()
        return interview_session

    # ------------------------------------------------------------------
    # Questions
    # ------------------------------------------------------------------

    def create_question(self, question: InterviewQuestion) -> InterviewQuestion:
        self.session.add(question)
        self.session.flush()
        return question

    def get_question(self, question_id: uuid.UUID) -> InterviewQuestion | None:
        return self.session.get(InterviewQuestion, question_id)

    def get_current_question(self, session_id: uuid.UUID) -> InterviewQuestion | None:
        stmt = (
            select(InterviewQuestion)
            .join(InterviewSession, InterviewSession.id == InterviewQuestion.session_id)
            .where(
                InterviewQuestion.session_id == session_id,
                InterviewQuestion.sequence_number == InterviewSession.current_question_number,
            )
        )
        return self.session.scalars(stmt).one_or_none()

    def get_questions(self, session_id: uuid.UUID) -> list[InterviewQuestion]:
        stmt = (
            select(InterviewQuestion)
            .where(InterviewQuestion.session_id == session_id)
            .order_by(InterviewQuestion.sequence_number.asc())
        )
        return list(self.session.scalars(stmt).all())

    # ------------------------------------------------------------------
    # Topics
    # ------------------------------------------------------------------

    def create_topic(self, topic: InterviewTopicEntry) -> InterviewTopicEntry:
        self.session.add(topic)
        self.session.flush()
        return topic

    def create_topics(self, topics: list[InterviewTopicEntry]) -> list[InterviewTopicEntry]:
        self.session.add_all(topics)
        self.session.flush()
        return topics

    def get_topics(self, session_id: uuid.UUID) -> list[InterviewTopicEntry]:
        stmt = (
            select(InterviewTopicEntry)
            .where(InterviewTopicEntry.session_id == session_id)
            .order_by(InterviewTopicEntry.sequence_number.asc())
        )
        return list(self.session.scalars(stmt).all())

    def get_topic(self, topic_id: uuid.UUID) -> InterviewTopicEntry | None:
        return self.session.get(InterviewTopicEntry, topic_id)

    def delete_topics(self, session_id: uuid.UUID) -> None:
        """Remove all topic entries for a session. Flushes only."""
        topics = self.get_topics(session_id)
        for topic in topics:
            self.session.delete(topic)
        self.session.flush()

    def get_current_topic(self, session_id: uuid.UUID) -> InterviewTopicEntry | None:
        stmt = select(InterviewTopicEntry).where(
            InterviewTopicEntry.session_id == session_id,
            InterviewTopicEntry.status == InterviewTopicStatus.IN_PROGRESS,
        )
        return self.session.scalars(stmt).one_or_none()

    def update_topic_status(
        self, topic: InterviewTopicEntry, status: InterviewTopicStatus
    ) -> InterviewTopicEntry:
        topic.status = status
        self.session.flush()
        return topic

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    def create_message(self, message: InterviewMessage) -> InterviewMessage:
        self.session.add(message)
        self.session.flush()
        return message

    def get_messages(self, session_id: uuid.UUID) -> list[InterviewMessage]:
        stmt = (
            select(InterviewMessage)
            .where(InterviewMessage.session_id == session_id)
            .order_by(InterviewMessage.sequence_number.asc())
        )
        return list(self.session.scalars(stmt).all())

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def get_evaluation(self, session_id: uuid.UUID) -> Evaluation | None:
        stmt = select(Evaluation).where(Evaluation.session_id == session_id)
        return self.session.scalars(stmt).one_or_none()

    def create_evaluation(self, evaluation: Evaluation) -> Evaluation:
        self.session.add(evaluation)
        self.session.flush()
        return evaluation

    # ------------------------------------------------------------------
    # Resume
    # ------------------------------------------------------------------

    def get_resume(self, session_id: uuid.UUID) -> InterviewResume | None:
        stmt = select(InterviewResume).where(InterviewResume.session_id == session_id)
        return self.session.scalars(stmt).one_or_none()

    def create_resume(self, resume: InterviewResume) -> InterviewResume:
        self.session.add(resume)
        self.session.flush()
        return resume

    def update_resume(self, resume: InterviewResume, **changes: Any) -> InterviewResume:
        for field, value in changes.items():
            setattr(resume, field, value)
        self.session.flush()
        return resume

    def delete_resume(self, resume: InterviewResume) -> None:
        self.session.delete(resume)
        self.session.flush()

    # ------------------------------------------------------------------
    # Plan
    # ------------------------------------------------------------------

    def create_plan(
        self, session_id: uuid.UUID, plan: InterviewPlan
    ) -> InterviewPlanRecord:
        """Persist a validated InterviewPlan. The role and plan_version are
        derived from the domain plan — callers cannot supply different
        values. Only flushes; the caller owns the transaction boundary."""
        record = InterviewPlanRecord(
            session_id=session_id,
            plan_version=plan.plan_version,
            role=plan.role,
            plan=plan.model_dump(mode="json"),
        )
        self.session.add(record)
        self.session.flush()
        return record

    def get_plan(self, session_id: uuid.UUID) -> InterviewPlanRecord | None:
        """The most recent plan for a session (highest plan_version)."""
        stmt = (
            select(InterviewPlanRecord)
            .where(InterviewPlanRecord.session_id == session_id)
            .order_by(InterviewPlanRecord.plan_version.desc())
            .limit(1)
        )
        return self.session.scalars(stmt).one_or_none()

    def get_plan_by_id(self, plan_id: uuid.UUID) -> InterviewPlanRecord | None:
        return self.session.get(InterviewPlanRecord, plan_id)

    def load_plan(self, session_id: uuid.UUID) -> InterviewPlan | None:
        """Load and reconstruct the domain InterviewPlan for a session.
        Returns None when no plan is persisted. Raises ValidationError
        (via Pydantic) if the persisted JSONB is structurally invalid —
        corrupted plans do not silently become arbitrary dicts."""
        record = self.get_plan(session_id)
        if record is None:
            return None
        return InterviewPlan.model_validate(record.plan)
