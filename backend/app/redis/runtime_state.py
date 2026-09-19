from uuid import UUID

from pydantic import BaseModel

from app.domain.enums import Difficulty, InterviewStatus, InterviewTopic


class InterviewRuntimeNode:
    """Explicit runtime-position constants for `InterviewRuntimeState.current_node`.

    Only two nodes exist because this project has no AI agent decision
    graph yet (a later task). Kept as named constants rather than scattering
    string literals through the service/router layers.
    """

    WAITING_FOR_ANSWER = "WAITING_FOR_ANSWER"
    COMPLETED = "COMPLETED"


class InterviewRuntimeState(BaseModel):
    """Small, reconstructable runtime-position snapshot mirrored into Redis.

    This is NOT the source of truth — PostgreSQL is. It holds only what is
    needed to resume/inspect the current interview position quickly; the
    full transcript (questions, messages, evaluation) always lives in
    PostgreSQL and is never duplicated here.
    """

    session_id: UUID
    status: InterviewStatus
    current_node: str
    question_number: int
    question_limit: int
    current_topic: InterviewTopic | None
    current_question_id: UUID | None
    difficulty: Difficulty
    last_action: str | None
    version: int
