from uuid import UUID

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import settings
from app.domain.enums import InterviewStatus
from app.models.interview_session import InterviewSession
from app.redis.keys import InterviewRedisKeys
from app.redis.runtime_state import InterviewRuntimeNode, InterviewRuntimeState
from app.repositories.interview_repository import InterviewRepository
from app.services.interview_service import InterviewNotFoundError


class RuntimeStateUnavailableError(Exception):
    """A Redis runtime-state operation failed.

    Redis is a runtime optimization layer, not durable storage — callers
    catch this explicitly and decide to continue (PostgreSQL already holds
    the durable state) rather than silently swallowing the underlying
    Redis error.
    """


class RuntimeStateService:
    """Redis-backed runtime-state mirror for interview sessions.

    Reads/writes go through this class only; PostgreSQL access here is
    limited to what `get_or_rebuild_state` needs to reconstruct state after
    a Redis miss.
    """

    def __init__(self, redis_client: Redis, repository: InterviewRepository):
        self._redis = redis_client
        self._repository = repository

    async def set_state(self, state: InterviewRuntimeState) -> None:
        key = InterviewRedisKeys.state(state.session_id)
        payload = state.model_dump_json()
        try:
            await self._redis.set(key, payload, ex=settings.redis_interview_state_ttl_seconds)
        except RedisError as exc:
            raise RuntimeStateUnavailableError(
                f"Failed to write runtime state for session {state.session_id}"
            ) from exc

    async def get_state(self, session_id: UUID) -> InterviewRuntimeState | None:
        key = InterviewRedisKeys.state(session_id)
        try:
            raw = await self._redis.get(key)
        except RedisError as exc:
            raise RuntimeStateUnavailableError(
                f"Failed to read runtime state for session {session_id}"
            ) from exc
        if raw is None:
            return None
        return InterviewRuntimeState.model_validate_json(raw)

    async def delete_state(self, session_id: UUID) -> None:
        key = InterviewRedisKeys.state(session_id)
        try:
            await self._redis.delete(key)
        except RedisError as exc:
            raise RuntimeStateUnavailableError(
                f"Failed to delete runtime state for session {session_id}"
            ) from exc

    async def exists(self, session_id: UUID) -> bool:
        key = InterviewRedisKeys.state(session_id)
        try:
            return bool(await self._redis.exists(key))
        except RedisError as exc:
            raise RuntimeStateUnavailableError(
                f"Failed to check runtime state for session {session_id}"
            ) from exc

    def build_state(self, session: InterviewSession, last_action: str | None) -> InterviewRuntimeState:
        """Build the runtime state for `session`'s CURRENT position.

        `current_question`/`current_topic` are always derived from
        `InterviewRepository.get_current_question` (the same lookup
        `GET /interviews/{id}` uses) rather than accepted as a parameter —
        this keeps a live post-transaction write and a Redis-miss rebuild
        produce identical results for the same durable session state.
        """
        current_question = self._repository.get_current_question(session.id)
        node = (
            InterviewRuntimeNode.COMPLETED
            if session.status == InterviewStatus.COMPLETED
            else InterviewRuntimeNode.WAITING_FOR_ANSWER
        )
        return InterviewRuntimeState(
            session_id=session.id,
            status=session.status,
            current_node=node,
            question_number=session.current_question_number,
            question_limit=session.question_limit,
            current_topic=current_question.topic if current_question else None,
            current_question_id=current_question.id if current_question else None,
            difficulty=session.difficulty,
            last_action=last_action,
            version=session.version,
        )

    async def get_or_rebuild_state(self, session_id: UUID) -> InterviewRuntimeState:
        """Redis hit -> return it. Redis miss -> reconstruct from PostgreSQL,
        write it back, then return it."""
        state = await self.get_state(session_id)
        if state is not None:
            return state

        session = self._repository.get_session(session_id)
        if session is None:
            raise InterviewNotFoundError(f"Interview session {session_id} was not found.")

        # `last_action` is genuinely unknown once reconstructed purely from
        # durable state — it was never persisted, only ever held in Redis.
        rebuilt = self.build_state(session=session, last_action=None)
        await self.set_state(rebuilt)
        return rebuilt
