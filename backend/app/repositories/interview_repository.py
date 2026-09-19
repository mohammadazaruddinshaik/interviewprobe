import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import InterviewTopicStatus
from app.models.evaluation import Evaluation
from app.models.interview_message import InterviewMessage
from app.models.interview_question import InterviewQuestion
from app.models.interview_session import InterviewSession
from app.models.interview_topic import InterviewTopicEntry


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
