from uuid import UUID

import httpx
from qdrant_client import AsyncQdrantClient
from qdrant_client import models as qm
from qdrant_client.http.exceptions import ApiException

from app.domain.enums import Difficulty, InterviewTopic, Role
from app.knowledge.exceptions import KnowledgeStoreUnavailableError
from app.knowledge.models import KnowledgeChunk, KnowledgeSearchResult
from app.knowledge.store.base import KnowledgeStore

# Every raw error a Qdrant operation can raise, translated uniformly to
# `KnowledgeStoreUnavailableError` — never exposed as `ApiException`/
# `httpx.HTTPError`/`OSError` outside this module.
_QDRANT_ERRORS = (ApiException, httpx.HTTPError, OSError)

# Metadata payload keys that aren't one of `KnowledgeSearchResult`'s named
# fields — everything else in the payload lands in `.metadata`.
_NAMED_PAYLOAD_KEYS = frozenset({"role", "topic", "concept", "content"})


class QdrantKnowledgeStore(KnowledgeStore):
    """KnowledgeStore backed by Qdrant.

    No Qdrant SDK type (`PointStruct`, `ScoredPoint`, `Filter`, ...) is
    exposed outside this module — callers only ever see `KnowledgeChunk`/
    `KnowledgeSearchResult`/`KnowledgeStoreUnavailableError`. The
    collection is created lazily on first real use (never at construction,
    never at application startup), with its vector size taken from the
    caller-supplied `vector_size` (the configured embedding model's actual
    dimension), not a hardcoded constant.
    """

    def __init__(self, *, url: str, collection_name: str, vector_size: int, api_key: str | None = None):
        self._collection_name = collection_name
        self._vector_size = vector_size
        self._client = AsyncQdrantClient(url=url, api_key=api_key)
        self._collection_ready = False

    async def _ensure_collection(self) -> None:
        if self._collection_ready:
            return
        try:
            exists = await self._client.collection_exists(self._collection_name)
            if not exists:
                await self._client.create_collection(
                    collection_name=self._collection_name,
                    vectors_config=qm.VectorParams(size=self._vector_size, distance=qm.Distance.COSINE),
                )
        except _QDRANT_ERRORS as exc:
            raise KnowledgeStoreUnavailableError(
                f"Failed to prepare Qdrant collection '{self._collection_name}': {exc.__class__.__name__}"
            ) from exc
        self._collection_ready = True

    async def upsert(self, chunks: list[KnowledgeChunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must be the same length")
        if not chunks:
            return
        await self._ensure_collection()
        points = [
            qm.PointStruct(id=str(chunk.id), vector=vector, payload=_chunk_to_payload(chunk))
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        try:
            await self._client.upsert(collection_name=self._collection_name, points=points)
        except _QDRANT_ERRORS as exc:
            raise KnowledgeStoreUnavailableError(f"Qdrant upsert failed: {exc.__class__.__name__}") from exc

    async def search(
        self,
        query_vector: list[float],
        role: Role,
        topic: InterviewTopic,
        concept: str | None = None,
        limit: int = 5,
    ) -> list[KnowledgeSearchResult]:
        await self._ensure_collection()
        must: list[qm.FieldCondition] = [
            qm.FieldCondition(key="role", match=qm.MatchValue(value=role.value)),
            qm.FieldCondition(key="topic", match=qm.MatchValue(value=topic.value)),
        ]
        if concept is not None:
            must.append(qm.FieldCondition(key="concept", match=qm.MatchValue(value=concept)))
        try:
            response = await self._client.query_points(
                collection_name=self._collection_name,
                query=query_vector,
                query_filter=qm.Filter(must=must),
                limit=limit,
                with_payload=True,
            )
        except _QDRANT_ERRORS as exc:
            raise KnowledgeStoreUnavailableError(f"Qdrant search failed: {exc.__class__.__name__}") from exc
        return [_point_to_result(point) for point in response.points]

    async def delete(self, chunk_ids: list[UUID]) -> None:
        if not chunk_ids:
            return
        await self._ensure_collection()
        try:
            await self._client.delete(
                collection_name=self._collection_name,
                points_selector=qm.PointIdsList(points=[str(chunk_id) for chunk_id in chunk_ids]),
            )
        except _QDRANT_ERRORS as exc:
            raise KnowledgeStoreUnavailableError(f"Qdrant delete failed: {exc.__class__.__name__}") from exc

    async def close(self) -> None:
        await self._client.close()


def _chunk_to_payload(chunk: KnowledgeChunk) -> dict:
    return {
        "role": chunk.role.value,
        "topic": chunk.topic.value,
        "concept": chunk.concept,
        "content": chunk.content,
        "source": chunk.source,
        "title": chunk.title,
        "section": chunk.section,
        "difficulty": chunk.difficulty.value if chunk.difficulty else None,
        "tags": chunk.tags,
    }


def _point_to_result(point: qm.ScoredPoint) -> KnowledgeSearchResult:
    payload = point.payload or {}
    metadata = {
        key: value for key, value in payload.items() if key not in _NAMED_PAYLOAD_KEYS and value not in (None, [])
    }
    if "difficulty" in metadata:
        metadata["difficulty"] = Difficulty(metadata["difficulty"])
    return KnowledgeSearchResult(
        content=payload.get("content", ""),
        score=point.score,
        role=Role(payload["role"]),
        topic=InterviewTopic(payload["topic"]),
        concept=payload["concept"],
        metadata=metadata,
    )
