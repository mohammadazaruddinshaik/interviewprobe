from uuid import UUID

from app.domain.enums import InterviewTopicStatus
from app.repositories.interview_repository import InterviewRepository
from app.workflows.interview.models import TopicTransition


class TopicProgressionService:
    """Applies durable `interview_topics` status transitions.

    The interview workflow (LangGraph) only ever *proposes* a
    `TopicTransition` — it has no repository-write access at all. This is
    where a transition actually gets persisted, following the same
    transaction pattern as `InterviewService` (Task 8): each method owns
    its own commit/rollback boundary.
    """

    def __init__(self, repository: InterviewRepository):
        self.repository = repository

    @property
    def _db(self):
        return self.repository.session

    def initialize_topic_progression(self, session_id: UUID) -> None:
        """Call once, when an interview starts: the first selected topic
        (lowest sequence_number) becomes IN_PROGRESS; the rest stay
        PENDING (their persisted default — nothing to change there).

        Owns its own commit — for callers that are not already inside an
        open transaction. A caller that IS already inside one (e.g.
        `InterviewService.start_interview`, which also needs to update the
        session row and create the first question in the same commit)
        should use `apply_initial_progression` instead.
        """
        try:
            self.apply_initial_progression(session_id)
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise

    def apply_initial_progression(self, session_id: UUID) -> None:
        """Same mutation as `initialize_topic_progression`, without
        committing — the caller owns the transaction boundary."""
        topics = self.repository.get_topics(session_id)
        if topics:
            first = min(topics, key=lambda t: t.sequence_number)
            self.repository.update_topic_status(first, InterviewTopicStatus.IN_PROGRESS)

    def apply_transition(self, session_id: UUID, transition: TopicTransition) -> None:
        """Same mutation as `apply_transition_without_commit`, owning its own
        commit — for callers that are not already inside an open
        transaction."""
        try:
            self.apply_transition_without_commit(session_id, transition)
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise

    def apply_transition_without_commit(self, session_id: UUID, transition: TopicTransition) -> None:
        """Applies a validated `TopicTransition`: `from_topic` -> COMPLETED,
        `to_topic` -> IN_PROGRESS. A no-op (no write) when both fields are
        None — the common case for FOLLOW_UP/CLARIFY/END, where no topic
        transition applies. Does not commit — the caller (e.g.
        `InterviewService.submit_answer`, which also needs to persist the
        candidate answer and generated question in the same commit) owns
        the transaction boundary."""
        if transition.from_topic is None and transition.to_topic is None:
            return
        topics_by_enum = {t.topic: t for t in self.repository.get_topics(session_id)}

        if transition.from_topic is not None and transition.from_topic in topics_by_enum:
            self.repository.update_topic_status(
                topics_by_enum[transition.from_topic], InterviewTopicStatus.COMPLETED
            )
        if transition.to_topic is not None and transition.to_topic in topics_by_enum:
            self.repository.update_topic_status(
                topics_by_enum[transition.to_topic], InterviewTopicStatus.IN_PROGRESS
            )
