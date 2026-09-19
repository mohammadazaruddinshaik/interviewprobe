from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.enums import InterviewTopic, Role
from app.knowledge.models import KnowledgeChunk, KnowledgeSearchResult


class KnowledgeStore(ABC):
    """Provider-neutral interface over a searchable vector representation
    of knowledge chunks.

    Deliberately does not embed anything itself — every method here takes
    or returns already-embedded vectors / already-validated chunks. Text
    -> vector is `EmbeddingProvider`'s job; the rest of the application
    depends on this abstraction, never on a vector-store SDK directly, so
    the backing store stays swappable and easy to fake in tests.
    """

    @abstractmethod
    async def upsert(self, chunks: list[KnowledgeChunk], vectors: list[list[float]]) -> None: ...

    @abstractmethod
    async def search(
        self,
        query_vector: list[float],
        role: Role,
        topic: InterviewTopic,
        concept: str | None = None,
        limit: int = 5,
    ) -> list[KnowledgeSearchResult]: ...

    @abstractmethod
    async def delete(self, chunk_ids: list[UUID]) -> None: ...
