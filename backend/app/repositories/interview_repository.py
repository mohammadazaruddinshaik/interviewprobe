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
from app.investigation.models import ClaimInvestigation
from app.planning.models import InterviewPlan


class InterviewRepository:
    """SQLAlchemy data access for the interview domain.

    Owns queries, persistence, and flushes. Does not commit or manage the
    overall transaction boundary — that belongs to the caller (eventually
    the service layer).
    """

    def __init__(self, session: Session, owner_id: uuid.UUID | None = None):
        self.session = session
        # When set, every interview-session lookup is scoped to this owner
        # and newly created sessions are stamped with it. The HTTP layer
        # always constructs the repository with the authenticated user's id.
        self.owner_id = owner_id

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    def create_session(self, interview_session: InterviewSession) -> InterviewSession:
        if self.owner_id is not None:
            if interview_session.user_id not in (None, self.owner_id):
                raise ValueError("Cannot create an interview owned by a different user.")
            interview_session.user_id = self.owner_id
        self.session.add(interview_session)
        self.session.flush()
        return interview_session

    def get_session(self, session_id: uuid.UUID) -> InterviewSession | None:
        if self.owner_id is None:
            return self.session.get(InterviewSession, session_id)
        return self.session.execute(
            select(InterviewSession).where(
                InterviewSession.id == session_id, InterviewSession.user_id == self.owner_id
            )
        ).scalar_one_or_none()

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

    def delete_plan(self, session_id: uuid.UUID) -> None:
        """Delete every persisted plan version for a session. Only flushes."""
        stmt = select(InterviewPlanRecord).where(InterviewPlanRecord.session_id == session_id)
        for record in self.session.scalars(stmt).all():
            self.session.delete(record)
        self.session.flush()

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
        corrupted plans do not silently become arbitrary dicts.

        Strips the ``_claim_investigations`` key (written by
        ``save_claim_investigations``) before validating, since
        ``InterviewPlan`` has ``extra="forbid"``."""
        record = self.get_plan(session_id)
        if record is None:
            return None
        plan_data = record.plan
        if "_claim_investigations" in plan_data:
            plan_data = {k: v for k, v in plan_data.items() if k != "_claim_investigations"}
        return InterviewPlan.model_validate(plan_data)

    # ------------------------------------------------------------------
    # Claim investigation (stored alongside plan in plan JSONB)
    # ------------------------------------------------------------------

    def load_claim_investigations(self, session_id: uuid.UUID) -> list[ClaimInvestigation]:
        """Load persisted claim investigations for a session.

        Returns an empty list when no plan exists or no investigations
        have been recorded yet."""
        record = self.get_plan(session_id)
        if record is None:
            return []
        raw = record.plan.get("_claim_investigations", [])
        return [ClaimInvestigation.model_validate(item) for item in raw]

    def save_claim_investigations(
        self, session_id: uuid.UUID, investigations: list[ClaimInvestigation]
    ) -> None:
        """Persist claim investigations into the plan record's JSONB.

        Reassigns the entire column value so SQLAlchemy detects the
        mutation (JSONB in-place mutation is not tracked by default).
        Only flushes; the caller owns the transaction boundary."""
        record = self.get_plan(session_id)
        if record is None:
            return
        plan_data = dict(record.plan)
        plan_data["_claim_investigations"] = [
            inv.model_dump(mode="json") for inv in investigations
        ]
        record.plan = plan_data
        self.session.flush()
