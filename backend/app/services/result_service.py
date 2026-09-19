"""The candidate-facing interview result: a read-model layer assembled
from persisted PostgreSQL state plus the existing, already-idempotent
`EvaluationService` — never a new source of truth.

Preserves this separation:

    InterviewService  -> conducts the interview
    EvaluationService -> evaluates a completed interview
    ResultService      -> assembles the candidate-facing report

`ResultService` never mutates interview-lifecycle fields, never calls
Qdrant, never calls Redis, and never calls the LLM directly — only
`EvaluationService` does, exactly once per interview (its own idempotency
guarantee, reused here rather than duplicated).
"""

from dataclasses import dataclass
from uuid import UUID

from app.domain.enums import MessageRole
from app.evaluation.service import EvaluationService
from app.models.evaluation import Evaluation
from app.models.interview_question import InterviewQuestion
from app.models.interview_session import InterviewSession
from app.models.interview_topic import InterviewTopicEntry
from app.repositories.interview_repository import InterviewRepository


@dataclass(frozen=True)
class QuestionWithAnswer:
    """One persisted question paired with the candidate's answer to it.

    Paired by `question_id` (never by array position or ordering
    assumptions) — `candidate_answer` is `None`, not fabricated, when the
    candidate never answered this particular question.
    """

    question: InterviewQuestion
    candidate_answer: str | None


@dataclass(frozen=True)
class InterviewResult:
    """The assembled read model for a completed interview's result — every
    piece of persisted state the API route needs to build
    `InterviewResultResponse`, with no PostgreSQL/SQLAlchemy detail left
    for the route to reach for itself."""

    session: InterviewSession
    topics: list[InterviewTopicEntry]
    questions: list[QuestionWithAnswer]
    evaluation: Evaluation


class ResultService:
    def __init__(self, repository: InterviewRepository, evaluation_service: EvaluationService):
        self.repository = repository
        self.evaluation_service = evaluation_service

    async def get_result(self, session_id: UUID) -> InterviewResult:
        # Delegates ALL existence/completion validation to
        # `EvaluationService.get_or_create_evaluation` (InterviewNotFoundError
        # / InvalidInterviewStateError, and lazy evaluation generation)
        # rather than duplicating any of that logic here. By the time this
        # call returns successfully, the session is guaranteed to exist
        # and be COMPLETED, and a persisted evaluation is guaranteed to
        # exist — generated on this call if it didn't already.
        evaluation = await self.evaluation_service.get_or_create_evaluation(session_id)

        session = self.repository.get_session(session_id)
        topics = self.repository.get_topics(session_id)
        questions = self.repository.get_questions(session_id)
        messages = self.repository.get_messages(session_id)

        candidate_answers_by_question_id = {
            message.question_id: message.content
            for message in messages
            if message.role == MessageRole.CANDIDATE and message.question_id is not None
        }
        questions_with_answers = [
            QuestionWithAnswer(
                question=question,
                candidate_answer=candidate_answers_by_question_id.get(question.id),
            )
            for question in questions
        ]

        return InterviewResult(
            session=session,
            topics=topics,
            questions=questions_with_answers,
            evaluation=evaluation,
        )
