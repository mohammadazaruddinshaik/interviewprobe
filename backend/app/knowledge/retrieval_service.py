import logging
import time

from app.domain.enums import InterviewTopic, Role
from app.domain.roles import InvalidRoleTopicError, InvalidTopicConceptError, validate_role_topic_concept
from app.knowledge.embedding.base import EmbeddingProvider
from app.knowledge.exceptions import KnowledgeRetrievalError
from app.knowledge.models import KnowledgeSearchResult
from app.knowledge.store.base import KnowledgeStore

logger = logging.getLogger(__name__)


class KnowledgeRetrievalService:
    """Role/topic/concept-aware knowledge retrieval.

    Sits above `EmbeddingProvider` and `KnowledgeStore`: embeds the query
    text, then asks the store for vectors filtered to the requested role/
    topic (and optional concept) — never a generic, unfiltered semantic
    search. Enforces role/topic/concept compatibility against the existing
    role catalog (`validate_role_topic_concept`) before ever touching the
    embedding provider or the store, so an invalid filter fails fast and
    cheaply.

    No LLM calls happen here — this is a pure retrieval layer. It is not
    wired into `InterviewService` or the LangGraph workflow yet; that is
    the next task's integration point (Task 19 explicitly stops short of
    it).
    """

    def __init__(self, embedding_provider: EmbeddingProvider, store: KnowledgeStore):
        self._embedding_provider = embedding_provider
        self._store = store

    async def search(
        self,
        query: str,
        role: Role,
        topic: InterviewTopic,
        concept: str | None = None,
        limit: int = 5,
    ) -> list[KnowledgeSearchResult]:
        if not query or not query.strip():
            raise KnowledgeRetrievalError("query must not be empty")
        if limit < 1:
            raise KnowledgeRetrievalError("limit must be at least 1")
        try:
            validate_role_topic_concept(role, topic, concept)
        except (InvalidRoleTopicError, InvalidTopicConceptError) as exc:
            raise KnowledgeRetrievalError(str(exc)) from exc

        started = time.monotonic()
        try:
            query_vector = await self._embedding_provider.embed(query)
            results = await self._store.search(
                query_vector=query_vector, role=role, topic=topic, concept=concept, limit=limit
            )
        except Exception:
            self._log(role, topic, concept, started, result_count=None, status="failed")
            raise
        self._log(role, topic, concept, started, result_count=len(results), status="success")
        return results

    def _log(
        self,
        role: Role,
        topic: InterviewTopic,
        concept: str | None,
        started: float,
        result_count: int | None,
        status: str,
    ) -> None:
        # Deliberately: role, topic, concept, result_count, duration,
        # status only — never the query text or any chunk's content.
        duration_ms = int((time.monotonic() - started) * 1000)
        logger.info(
            "knowledge_retrieval role=%s topic=%s concept=%s result_count=%s duration_ms=%d status=%s",
            role.value,
            topic.value,
            concept,
            result_count,
            duration_ms,
            status,
        )
