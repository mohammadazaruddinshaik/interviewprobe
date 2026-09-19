import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.domain.enums import (
    Difficulty,
    InterviewStatus,
    InterviewTopic,
    InterviewTopicStatus,
    MessageRole,
    QuestionType,
    Role,
)
from app.domain.roles import InvalidRoleTopicError, validate_role_topics
from app.models.interview_message import InterviewMessage
from app.models.interview_question import InterviewQuestion
from app.models.interview_session import InterviewSession
from app.models.interview_topic import InterviewTopicEntry
from app.repositories.interview_repository import InterviewRepository
from app.services.topic_progression_service import TopicProgressionService
from app.workflows.interview.models import NextAction
from app.workflows.interview.state import InterviewAgentState

if TYPE_CHECKING:
    # `app.workflows.interview.graph` (via its nodes module) imports
    # `InterviewNotFoundError` from this module — importing `InterviewWorkflow`
    # at runtime here would be circular. The type is only needed for
    # annotations, so a `TYPE_CHECKING`-only import breaks the cycle without
    # losing type-checking.
    from app.workflows.interview.graph import InterviewWorkflow

# Maps a validated `NextAction.action` to the persisted question's
# `QuestionType`. "END" is deliberately absent — that action never
# generates a question, so it never reaches this lookup.
_ACTION_TO_QUESTION_TYPE: dict[str, QuestionType] = {
    "FOLLOW_UP": QuestionType.FOLLOW_UP,
    "CLARIFY": QuestionType.CLARIFICATION,
    "NEW_TOPIC": QuestionType.TOPIC_TRANSITION,
}


class InterviewServiceError(Exception):
    """Base class for interview service domain errors."""


class InterviewNotFoundError(InterviewServiceError):
    pass


class InvalidInterviewStateError(InterviewServiceError):
    pass


class InvalidQuestionError(InterviewServiceError):
    pass


class InvalidRoleTopicSelectionError(InterviewServiceError):
    """Raised when the requested topics are not valid for the requested
    role. Wraps `app.domain.roles.InvalidRoleTopicError` so the API layer
    only ever maps `InterviewServiceError` subclasses, never a domain
    exception, to an HTTP response."""


class InterviewService:
    """Deterministic business rules for the interview lifecycle.

    Owns the transaction boundary: each public method commits on success
    and rolls back on failure. Repository methods only flush.
    """

    def __init__(self, repository: InterviewRepository, workflow: "InterviewWorkflow"):
        self.repository = repository
        # Shares this service's repository (and therefore its DB session),
        # so `start_interview` can call it mid-transaction and still commit
        # once at the end — see `apply_initial_progression`.
        self.topic_progression_service = TopicProgressionService(repository)
        # The LangGraph adaptive workflow: reasoning/orchestration only. It
        # reads through `repository` and returns structured results — it
        # never mutates PostgreSQL, Redis, or interview state itself. All
        # durable mutation below is this service's responsibility.
        self.workflow = workflow

    @property
    def _db(self) -> Session:
        return self.repository.session

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create_interview(
        self,
        role: Role,
        difficulty: Difficulty,
        question_limit: int,
        topics: list[InterviewTopic],
    ) -> InterviewSession:
        try:
            try:
                validate_role_topics(role, topics)
            except InvalidRoleTopicError as exc:
                raise InvalidRoleTopicSelectionError(str(exc)) from exc

            session = InterviewSession(
                role=role,
                difficulty=difficulty,
                status=InterviewStatus.CREATED,
                question_limit=question_limit,
                current_question_number=0,
                version=1,
            )
            self.repository.create_session(session)

            topic_entries = [
                InterviewTopicEntry(
                    session_id=session.id,
                    topic=topic,
                    sequence_number=sequence_number,
                    status=InterviewTopicStatus.PENDING,
                )
                for sequence_number, topic in enumerate(topics, start=1)
            ]
            self.repository.create_topics(topic_entries)

            self._db.commit()
        except Exception:
            self._db.rollback()
            raise
        return session

    # ------------------------------------------------------------------
    # Start
    # ------------------------------------------------------------------

    async def start_interview(self, session_id: uuid.UUID) -> tuple[InterviewSession, InterviewQuestion]:
        try:
            session = self._get_session_or_raise(session_id)
            if session.status != InterviewStatus.CREATED:
                raise InvalidInterviewStateError(
                    f"Interview session {session_id} must be CREATED to start "
                    f"(current status: {session.status})."
                )

            # The persisted `interview_topics` selection (this candidate's
            # actual choice, in their chosen order) is authoritative here —
            # never the role catalog, and never whatever topic the LLM's
            # `GeneratedQuestion` names below.
            topics = self.repository.get_topics(session_id)
            if not topics:
                raise InvalidInterviewStateError(
                    f"Interview session {session_id} has no selected topics to start."
                )
            first_topic_entry = topics[0]

            # Invoke the graph BEFORE any durable mutation: a failed LLM
            # call must leave the session untouched (still CREATED, topics
            # still PENDING) rather than a partially-mutated turn.
            state: InterviewAgentState = {"session_id": session_id}
            result = await self.workflow.run_initial_question(state)
            generated_question = result["generated_question"]

            # This marks topic 1 IN_PROGRESS, reusing Task 15's
            # TopicProgressionService instead of duplicating status-
            # transition logic.
            self.topic_progression_service.apply_initial_progression(session_id)

            self.repository.update_session(
                session,
                status=InterviewStatus.IN_PROGRESS,
                started_at=datetime.now(UTC),
                current_question_number=1,
                version=session.version + 1,
            )

            question = self._create_question(
                session=session,
                sequence_number=1,
                question_type=QuestionType.INITIAL,
                topic=first_topic_entry.topic,
                difficulty=session.difficulty,
                question_text=generated_question.question,
            )
            self._create_interviewer_message(session, question)

            self._db.commit()
        except Exception:
            self._db.rollback()
            raise
        return session, question

    # ------------------------------------------------------------------
    # Submit answer
    # ------------------------------------------------------------------

    async def submit_answer(
        self,
        session_id: uuid.UUID,
        question_id: uuid.UUID,
        answer: str,
        idempotency_key: str | None = None,
    ) -> tuple[InterviewSession, InterviewQuestion | None]:
        # idempotency_key is accepted so the API boundary can pass it through
        # to the service layer. Enforcement itself (dedup, replay) lives in
        # the Redis-backed layer the API route wraps this call in — by the
        # time this method runs, the caller has already guaranteed this is
        # a genuinely new mutation.
        try:
            session = self._get_session_or_raise(session_id)
            if session.status != InterviewStatus.IN_PROGRESS:
                raise InvalidInterviewStateError(
                    f"Interview session {session_id} is not IN_PROGRESS "
                    f"(current status: {session.status})."
                )

            question = self._get_current_question_or_raise(session, question_id)

            # Invoke the graph BEFORE any durable mutation — see
            # `start_interview` for the same rationale. Only the current
            # turn's context is handed to the workflow; the durable
            # transcript stays in PostgreSQL, never duplicated into graph
            # state.
            state: InterviewAgentState = {
                "session_id": session_id,
                "current_question_id": question.id,
                "candidate_answer": answer,
            }
            result = await self.workflow.run_answer_turn(state)
            next_action: NextAction = result["next_action"]

            next_question_number = session.current_question_number + 1
            next_version = session.version + 1

            self._create_message(
                session=session,
                question=question,
                role=MessageRole.CANDIDATE,
                content=answer,
            )

            # The question limit always wins, regardless of what the graph
            # decided — `validate_decision` already enforces this (see
            # decision_validator.py), but backend state remains the final
            # authority rather than trusting the graph's output alone.
            next_question: InterviewQuestion | None = None
            if next_action.action != "END" and next_question_number <= session.question_limit:
                topic_transition = result["topic_transition"]
                self.topic_progression_service.apply_transition_without_commit(
                    session_id, topic_transition
                )

                self.repository.update_session(
                    session,
                    current_question_number=next_question_number,
                    version=next_version,
                )

                generated_question = result["generated_question"]
                question_type = _ACTION_TO_QUESTION_TYPE.get(next_action.action, QuestionType.FOLLOW_UP)
                next_question = self._create_question(
                    session=session,
                    sequence_number=next_question_number,
                    question_type=question_type,
                    topic=next_action.topic or question.topic,
                    difficulty=next_action.difficulty,
                    question_text=generated_question.question,
                    agent_reason=next_action.rationale,
                )
                self._create_interviewer_message(session, next_question)
            else:
                self.repository.update_session(
                    session,
                    status=InterviewStatus.COMPLETED,
                    completed_at=datetime.now(UTC),
                    version=next_version,
                )

            self._db.commit()
        except Exception:
            self._db.rollback()
            raise
        return session, next_question

    # ------------------------------------------------------------------
    # Complete
    # ------------------------------------------------------------------

    def complete_interview(self, session_id: uuid.UUID) -> InterviewSession:
        try:
            session = self._get_session_or_raise(session_id)
            if session.status != InterviewStatus.IN_PROGRESS:
                raise InvalidInterviewStateError(
                    f"Interview session {session_id} must be IN_PROGRESS to complete "
                    f"(current status: {session.status})."
                )

            self.repository.update_session(
                session,
                status=InterviewStatus.COMPLETED,
                completed_at=datetime.now(UTC),
                version=session.version + 1,
            )

            self._db.commit()
        except Exception:
            self._db.rollback()
            raise
        return session

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get_interview_state(
        self, session_id: uuid.UUID
    ) -> tuple[
        InterviewSession,
        InterviewTopic | None,
        int,
        list[InterviewTopicEntry],
        InterviewQuestion | None,
    ]:
        """Return the session plus values derived/fetched at read time.

        `current_topic` is computed from the session's current question
        (there is no persisted, populated topic column to read from) and
        `questions_answered` is computed by counting CANDIDATE messages,
        rather than inferred from `current_question_number` bookkeeping.
        `topics` is the session's persisted topic selection, in sequence
        order.

        `current_unanswered_question` (Task 27) is the question a candidate
        should currently be answering, reconstructed from PostgreSQL alone
        (Redis is never consulted here) so a refreshed IN_PROGRESS interview
        can restore its in-flight question instead of generating a new one.
        Deliberately NOT `max(sequence_number)`, and deliberately not simply
        trusted from the session's `current_question_number` bookkeeping
        pointer either — both would return a stale, already-answered
        question once the interview is COMPLETED (`submit_answer` only
        advances that pointer when handing out a new question, never on the
        completing turn). Instead this is derived straight from the
        questions/messages history: the most recent question (by sequence
        number) that has no CANDIDATE message against it yet. Under normal
        operation there is at most one such question at a time — every
        earlier one was answered before the next was created — so this is
        equivalent to the bookkeeping pointer whenever the interview is
        genuinely IN_PROGRESS, but self-correcting rather than assumed:
        None for CREATED (no questions yet) and COMPLETED (all answered),
        the real in-flight question for IN_PROGRESS.
        """
        session = self._get_session_or_raise(session_id)

        current_question = self.repository.get_current_question(session_id)
        current_topic = current_question.topic if current_question is not None else None

        messages = self.repository.get_messages(session_id)
        questions_answered = sum(1 for m in messages if m.role == MessageRole.CANDIDATE)

        questions = self.repository.get_questions(session_id)
        answered_question_ids = {
            m.question_id for m in messages if m.role == MessageRole.CANDIDATE and m.question_id is not None
        }
        current_unanswered_question = next(
            (q for q in reversed(questions) if q.id not in answered_question_ids), None
        )

        topics = self.repository.get_topics(session_id)

        return session, current_topic, questions_answered, topics, current_unanswered_question

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_session_or_raise(self, session_id: uuid.UUID) -> InterviewSession:
        session = self.repository.get_session(session_id)
        if session is None:
            raise InterviewNotFoundError(f"Interview session {session_id} was not found.")
        return session

    def _get_current_question_or_raise(
        self, session: InterviewSession, question_id: uuid.UUID
    ) -> InterviewQuestion:
        question = self.repository.get_question(question_id)
        if question is None or question.session_id != session.id:
            raise InvalidQuestionError(
                f"Question {question_id} does not belong to session {session.id}."
            )
        if question.sequence_number != session.current_question_number:
            raise InvalidQuestionError(
                f"Question {question_id} is not the current question for session {session.id}."
            )
        return question

    def _next_message_sequence_number(self, session_id: uuid.UUID) -> int:
        messages = self.repository.get_messages(session_id)
        if not messages:
            return 1
        return messages[-1].sequence_number + 1

    def _create_question(
        self,
        session: InterviewSession,
        sequence_number: int,
        question_type: QuestionType,
        topic: InterviewTopic,
        difficulty: Difficulty,
        question_text: str,
        agent_reason: str | None = None,
    ) -> InterviewQuestion:
        # `agent_reason` (the graph's `NextAction.rationale`) is stored for
        # internal/debugging use only — `QuestionResponse` never exposes it
        # to the candidate.
        question = InterviewQuestion(
            session_id=session.id,
            sequence_number=sequence_number,
            question_text=question_text,
            topic=topic,
            difficulty=difficulty,
            question_type=question_type,
            agent_reason=agent_reason,
        )
        return self.repository.create_question(question)

    def _create_interviewer_message(
        self, session: InterviewSession, question: InterviewQuestion
    ) -> InterviewMessage:
        return self._create_message(
            session=session,
            question=question,
            role=MessageRole.INTERVIEWER,
            content=question.question_text,
        )

    def _create_message(
        self,
        session: InterviewSession,
        question: InterviewQuestion | None,
        role: MessageRole,
        content: str,
    ) -> InterviewMessage:
        message = InterviewMessage(
            session_id=session.id,
            question_id=question.id if question else None,
            role=role,
            content=content,
            sequence_number=self._next_message_sequence_number(session.id),
        )
        return self.repository.create_message(message)
