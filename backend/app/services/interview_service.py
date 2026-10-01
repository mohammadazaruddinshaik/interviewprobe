import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.domain.enums import (
    Difficulty,
    InterviewStatus,
    InterviewTopic,
    InterviewTopicStatus,
    MessageRole,
    QuestionType,
    ResumeExtractionStatus,
    Role,
)
from app.investigation.investigator import ClaimInvestigator
from app.investigation.models import ClaimInvestigation, InvestigationEvidence
from app.models.interview_message import InterviewMessage
from app.models.interview_question import InterviewQuestion
from app.models.interview_session import InterviewSession
from app.models.interview_topic import InterviewTopicEntry
from app.planning.models import InterviewPlanningConstraints, build_claim_id, build_planning_input
from app.planning.planner import InterviewPlanner
from app.repositories.interview_repository import InterviewRepository
from app.resume.models import ResumeProfile
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

logger = logging.getLogger(__name__)

DEFAULT_MAX_DURATION_MINUTES = 45

# Runtime-safe placeholders for the NOT NULL `difficulty` / `question_limit` columns of a CREATED session
# (the question limit sits inside the 3-10 range enforced by ck_interview_sessions_question_limit_min). They are
# not candidate choices and are not reported while CREATED. When a planner is configured, `start_interview` overwrites
# them with plan.starting_difficulty / plan.max_questions BEFORE the first question or any runtime state reads them;
# they survive only for planner-less (pre-Phase-3) sessions.
PLACEHOLDER_DIFFICULTY = Difficulty.MEDIUM
PLACEHOLDER_QUESTION_LIMIT = 5

# Maps a validated `NextAction.action` to the persisted question's
# `QuestionType`. "END" is deliberately absent — that action never
# generates a question, so it never reaches this lookup.
_ACTION_TO_QUESTION_TYPE: dict[str, QuestionType] = {
    "FOLLOW_UP": QuestionType.FOLLOW_UP,
    "CLARIFY": QuestionType.CLARIFICATION,
    "DEEP_DIVE": QuestionType.DEEP_DIVE,
    "CHALLENGE": QuestionType.CHALLENGE,
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


class InterviewExpiredError(InterviewServiceError):
    """Raised when the authoritative interview deadline has passed."""


def get_interview_deadline(
    session: InterviewSession,
    max_duration_minutes: int = DEFAULT_MAX_DURATION_MINUTES,
) -> datetime | None:
    """Return the authoritative interview deadline derived from the
    server-side ``started_at`` timestamp.  Returns ``None`` for sessions
    that have not started yet (no deadline to enforce)."""
    if session.started_at is None:
        return None
    return session.started_at + timedelta(minutes=max_duration_minutes)


def is_interview_expired(
    session: InterviewSession,
    now: datetime | None = None,
    max_duration_minutes: int = DEFAULT_MAX_DURATION_MINUTES,
) -> bool:
    """``True`` when the authoritative deadline has passed.  Sessions that
    have not started yet are never expired."""
    deadline = get_interview_deadline(session, max_duration_minutes)
    if deadline is None:
        return False
    if now is None:
        now = datetime.now(UTC)
    # Normalise to UTC-aware: SQLite strips tzinfo on round-trip, but the
    # value is always UTC (set via ``datetime.now(UTC)``).
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    return now >= deadline


class InterviewService:
    """Deterministic business rules for the interview lifecycle.

    Owns the transaction boundary: each public method commits on success
    and rolls back on failure. Repository methods only flush.
    """

    def __init__(
        self,
        repository: InterviewRepository,
        workflow: "InterviewWorkflow",
        planner: InterviewPlanner | None = None,
        investigator: ClaimInvestigator | None = None,
    ):
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
        self.planner = planner
        self.investigator = investigator

    @property
    def _db(self) -> Session:
        return self.repository.session

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create_interview(self, role: Role) -> InterviewSession:
        """Create a CREATED session for `role`. The candidate picks nothing else: topics are chosen by the
        planner at start (`interview_topics` stays empty until `_materialize_plan_topics`), and
        difficulty / question_limit are planner-owned too.

        `difficulty` and `question_limit` are NOT NULL columns, so a CREATED session carries the
        conservative placeholders `PLACEHOLDER_*` below. They are internal, never reported by the API
        while CREATED, and are overwritten from the validated InterviewPlan at start."""
        try:
            session = InterviewSession(
                role=role,
                difficulty=PLACEHOLDER_DIFFICULTY,
                status=InterviewStatus.CREATED,
                question_limit=PLACEHOLDER_QUESTION_LIMIT,
                current_question_number=0,
                version=1,
            )
            self.repository.create_session(session)
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise
        return session

    # ------------------------------------------------------------------
    # Start
    # ------------------------------------------------------------------

    async def start_interview(
        self, session_id: uuid.UUID
    ) -> tuple[InterviewSession, InterviewQuestion, str | None]:
        try:
            session = self._get_session_or_raise(session_id)
            if session.status != InterviewStatus.CREATED:
                raise InvalidInterviewStateError(
                    f"Interview session {session_id} must be CREATED to start "
                    f"(current status: {session.status})."
                )

            # --- Phase 3: interview planning ---
            # The planner runs ONCE per interview at start time. An
            # existing plan (from a prior attempt that rolled back after
            # planning but before commit) is reused — never regenerated.
            await self._ensure_interview_plan(session)

            # The persisted `interview_topics` selection — either the
            # candidate's original choice (pre-Phase-3 / no planner) or
            # the plan-materialized topics — is authoritative here.
            topics = self.repository.get_topics(session_id)
            if not topics:
                raise InvalidInterviewStateError(
                    f"Interview session {session_id} has no planned topics to start."
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
        return session, question, generated_question.lead_in

    # ------------------------------------------------------------------
    # Submit answer
    # ------------------------------------------------------------------

    async def submit_answer(
        self,
        session_id: uuid.UUID,
        question_id: uuid.UUID,
        answer: str,
        idempotency_key: str | None = None,
    ) -> tuple[InterviewSession, InterviewQuestion | None, str | None]:
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

            # ── Deadline pre-check ──────────────────────────────────
            # If the authoritative deadline has already passed, persist the
            # candidate's answer and finalize the session immediately —
            # skip the expensive LLM workflow entirely.
            if is_interview_expired(session):
                return self._finalize_expired_answer(session, question, answer)

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

            # ── Deadline post-check ─────────────────────────────────
            # The LLM workflow may have taken long enough for the deadline
            # to pass while processing.  The candidate's answer is already
            # persisted above; we simply finalize instead of continuing.
            interview_should_end = (
                next_action.action == "END"
                or next_question_number > session.question_limit
                or is_interview_expired(session)
            )

            next_question: InterviewQuestion | None = None
            lead_in: str | None = None
            if not interview_should_end:
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
                lead_in = generated_question.lead_in
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

            await self._investigate_relevant_claims(session_id, question)

            self._db.commit()
        except Exception:
            self._db.rollback()
            raise
        return session, next_question, lead_in

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
        `topics` is the session's persisted (planner-materialized) topics, in sequence
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
    # Planning
    # ------------------------------------------------------------------

    async def _ensure_interview_plan(self, session: InterviewSession) -> None:
        """Generate and persist an interview plan if a planner is
        configured and no plan exists yet. Materializes the plan's topics
        into `interview_topics`, replacing the candidate's original
        selection. A no-op when no planner is configured (backward
        compatibility with pre-Phase-3 sessions)."""
        if self.planner is None:
            return

        existing_plan = self.repository.load_plan(session.id)
        if existing_plan is not None:
            if existing_plan.starting_difficulty is not None and existing_plan.max_questions is not None:
                self._apply_plan_runtime_values(session, existing_plan)
                return
            # Legacy plan (pre-B1, no planner decisions). A CREATED session only carries creation-time
            # placeholders, which are not a prior runtime state, so they must not stand in for planner
            # decisions. Replace the plan with a freshly generated, validated one. Only flushes; a
            # planner failure rolls the deletion back with the rest of the start transaction.
            self.repository.delete_plan(session.id)

        resume_profile = self._load_resume_profile(session.id)
        constraints = InterviewPlanningConstraints(max_duration_minutes=DEFAULT_MAX_DURATION_MINUTES)
        planning_input = build_planning_input(
            role=session.role,
            constraints=constraints,
            resume_profile=resume_profile,
        )
        plan = await self.planner.plan(planning_input)
        self.repository.create_plan(session.id, plan)
        self._apply_plan_runtime_values(session, plan)
        self._materialize_plan_topics(session, plan)

    def _apply_plan_runtime_values(self, session: InterviewSession, plan) -> None:
        """Copy the planner's validated decisions into the session's runtime columns. The workflow, the
        decision validator, `submit_answer` and Redis all keep reading the session, never the plan."""
        self.repository.update_session(
            session,
            difficulty=plan.starting_difficulty,
            question_limit=plan.max_questions,
        )

    def _load_resume_profile(self, session_id: uuid.UUID) -> ResumeProfile | None:
        """Load a successfully extracted resume profile for planning.
        Returns None when no resume was uploaded or extraction failed."""
        resume = self.repository.get_resume(session_id)
        if resume is None:
            return None
        if resume.extraction_status != ResumeExtractionStatus.READY:
            return None
        if resume.structured_profile is None:
            return None
        return ResumeProfile.model_validate(resume.structured_profile)

    def _materialize_plan_topics(self, session: InterviewSession, plan) -> None:
        """Replace the session's existing `interview_topics` with the
        plan's `planned_topics`, preserving plan order as sequence
        numbers. Only flushes — the caller owns the transaction."""
        self.repository.delete_topics(session.id)
        topic_entries = [
            InterviewTopicEntry(
                session_id=session.id,
                topic=planned.topic,
                sequence_number=seq,
                status=InterviewTopicStatus.PENDING,
            )
            for seq, planned in enumerate(plan.planned_topics, start=1)
        ]
        self.repository.create_topics(topic_entries)

    # ------------------------------------------------------------------
    # Claim investigation
    # ------------------------------------------------------------------

    async def _investigate_relevant_claims(
        self, session_id: uuid.UUID, question: InterviewQuestion
    ) -> None:
        """Investigate resume claims associated with the answered question's topic.

        Runs only when an investigator is configured and the question's
        topic has related claims in the plan. Errors are caught and logged
        — investigation must never block the main answer flow."""
        if self.investigator is None:
            return

        try:
            plan = self.repository.load_plan(session_id)
            if plan is None:
                return

            planned_topic = next(
                (pt for pt in plan.planned_topics if pt.topic == question.topic),
                None,
            )
            if planned_topic is None or not planned_topic.related_claim_ids:
                return

            resume_profile = self._load_resume_profile(session_id)
            if resume_profile is None or not resume_profile.claims:
                return

            claim_by_id: dict[str, "ResumeClaim"] = {}
            for claim in resume_profile.claims:
                claim_by_id[build_claim_id(claim)] = claim

            target_claim_ids = [
                cid for cid in planned_topic.related_claim_ids if cid in claim_by_id
            ]
            if not target_claim_ids:
                return

            all_questions = self.repository.get_questions(session_id)
            all_messages = self.repository.get_messages(session_id)
            candidate_answers = {
                m.question_id: m for m in all_messages if m.role == MessageRole.CANDIDATE
            }

            topic_to_claim_ids: dict[InterviewTopic, set[str]] = {}
            for pt in plan.planned_topics:
                if pt.related_claim_ids:
                    topic_to_claim_ids[pt.topic] = set(pt.related_claim_ids)

            existing = self.repository.load_claim_investigations(session_id)
            inv_by_claim: dict[str, ClaimInvestigation] = {
                inv.claim_id: inv for inv in existing
            }

            for claim_id in target_claim_ids:
                evidence: list[InvestigationEvidence] = []
                for q in all_questions:
                    topic_claims = topic_to_claim_ids.get(q.topic, set())
                    if claim_id not in topic_claims:
                        continue
                    answer_msg = candidate_answers.get(q.id)
                    if answer_msg is None:
                        continue
                    evidence.append(
                        InvestigationEvidence(
                            question_sequence=q.sequence_number,
                            question_text=q.question_text,
                            answer_text=answer_msg.content,
                        )
                    )

                if not evidence:
                    continue

                claim = claim_by_id[claim_id]
                result = await self.investigator.investigate(claim, claim_id, evidence)

                inv_by_claim[claim_id] = ClaimInvestigation(
                    claim_id=claim_id,
                    status=result.status,
                    evidence_summary=result.evidence_summary,
                    rationale=result.rationale,
                )

            updated = list(inv_by_claim.values())
            self.repository.save_claim_investigations(session_id, updated)

        except Exception:
            logger.warning(
                "Claim investigation failed for session %s; continuing without investigation.",
                session_id,
                exc_info=True,
            )

    # ------------------------------------------------------------------
    # Deadline enforcement
    # ------------------------------------------------------------------

    def _finalize_expired_answer(
        self,
        session: InterviewSession,
        question: InterviewQuestion,
        answer: str,
    ) -> tuple[InterviewSession, InterviewQuestion | None, str | None]:
        """Persist the candidate's answer and complete the session when the
        deadline has already passed before LLM processing begins.  The
        candidate's answer is never lost — it was submitted in time to be
        recorded, even though the interview cannot continue."""
        self._create_message(
            session=session,
            question=question,
            role=MessageRole.CANDIDATE,
            content=answer,
        )
        self.repository.update_session(
            session,
            status=InterviewStatus.COMPLETED,
            completed_at=datetime.now(UTC),
            version=session.version + 1,
        )
        self._db.commit()
        return session, None, None

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
