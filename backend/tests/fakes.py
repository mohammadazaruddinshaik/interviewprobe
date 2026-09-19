"""Small test doubles shared across test modules."""

import asyncio
import hashlib
import math
import time
from uuid import UUID

from pydantic import BaseModel

from app.domain.enums import InterviewTopic, Role
from app.knowledge.embedding.base import EmbeddingProvider
from app.knowledge.models import KnowledgeChunk, KnowledgeSearchResult
from app.knowledge.store.base import KnowledgeStore
from app.llm.base import LLMProvider
from app.llm.models import LLMMessage, StructuredLLMResponse


class FakeAsyncRedis:
    """In-memory stand-in for `redis.asyncio.Redis`, covering the subset of
    the API the Redis-backed components in this project actually use:
    runtime state (set/get/delete/exists), locking and rate limiting
    (set with nx=, ttl, eval of the two Lua scripts in app/redis/lock.py
    and app/redis/rate_limit.py), and idempotency (set/get).

    `eval` is matched against the *exact* script strings the production
    modules use (imported directly, not reimplemented from scratch), so a
    test failure here would mean the fake and the real script actually
    disagree — not that the fake drifted from its own copy of the logic.

    Every method awaits `asyncio.sleep(0)` first, yielding control back to
    the event loop so `asyncio.gather`/concurrent requests interleave
    realistically instead of one coroutine silently running start-to-finish
    before the other begins.
    """

    def __init__(self):
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int] = {}
        self._expire_at: dict[str, float] = {}

    def _purge_if_expired(self, key: str) -> None:
        expire_at = self._expire_at.get(key)
        if expire_at is not None and expire_at <= time.monotonic() and key in self.store:
            del self.store[key]
            self._expire_at.pop(key, None)
            self.ttls.pop(key, None)

    def force_expire(self, key: str) -> None:
        """Test helper: make `key` behave as already expired, without
        waiting in real wall-clock time."""
        self._expire_at[key] = 0.0
        self._purge_if_expired(key)

    async def set(
        self, key: str, value: str, ex: int | None = None, nx: bool = False
    ) -> bool | None:
        await asyncio.sleep(0)
        self._purge_if_expired(key)
        if nx and key in self.store:
            return None
        self.store[key] = value
        if ex is not None:
            self.ttls[key] = ex
            self._expire_at[key] = time.monotonic() + ex
        else:
            self._expire_at.pop(key, None)
            self.ttls.pop(key, None)
        return True

    async def get(self, key: str) -> str | None:
        await asyncio.sleep(0)
        self._purge_if_expired(key)
        return self.store.get(key)

    async def delete(self, key: str) -> int:
        await asyncio.sleep(0)
        self._purge_if_expired(key)
        existed = key in self.store
        self.store.pop(key, None)
        self.ttls.pop(key, None)
        self._expire_at.pop(key, None)
        return 1 if existed else 0

    async def exists(self, key: str) -> int:
        await asyncio.sleep(0)
        self._purge_if_expired(key)
        return 1 if key in self.store else 0

    async def ttl(self, key: str) -> int:
        await asyncio.sleep(0)
        self._purge_if_expired(key)
        if key not in self.store:
            return -2
        expire_at = self._expire_at.get(key)
        if expire_at is None:
            return -1
        return max(int(expire_at - time.monotonic()), 0)

    async def eval(self, script: str, numkeys: int, *keys_and_args):
        await asyncio.sleep(0)
        from app.redis.lock import _RELEASE_IF_OWNER_SCRIPT
        from app.redis.rate_limit import _INCR_AND_EXPIRE_SCRIPT

        keys = list(keys_and_args[:numkeys])
        args = list(keys_and_args[numkeys:])

        if script == _RELEASE_IF_OWNER_SCRIPT:
            key = keys[0]
            token = args[0]
            self._purge_if_expired(key)
            if self.store.get(key) == token:
                del self.store[key]
                self._expire_at.pop(key, None)
                self.ttls.pop(key, None)
                return 1
            return 0

        if script == _INCR_AND_EXPIRE_SCRIPT:
            key = keys[0]
            window_seconds = int(args[0])
            self._purge_if_expired(key)
            current = int(self.store.get(key, "0")) + 1
            self.store[key] = str(current)
            if current == 1:
                self.ttls[key] = window_seconds
                self._expire_at[key] = time.monotonic() + window_seconds
            return current

        raise NotImplementedError("FakeAsyncRedis.eval: unrecognized script")

    async def aclose(self) -> None:
        pass


class FailingAsyncRedis:
    """Raises `redis.exceptions.ConnectionError` on every operation, to
    exercise the "Redis is temporarily unavailable" path without needing a
    real server that is actually down.
    """

    async def _fail(self, *args, **kwargs):
        from redis.exceptions import ConnectionError as RedisConnectionError

        raise RedisConnectionError("simulated Redis outage")

    set = _fail
    get = _fail
    delete = _fail
    exists = _fail
    ttl = _fail
    eval = _fail

    async def aclose(self) -> None:
        pass


class FakeLLMProvider(LLMProvider):
    """Configurable fake `LLMProvider` for workflow/graph tests — no
    network, no provider SDK.

    Configure `structured_responses` with `{SchemaClassName: instance}` to
    control what `generate_structured` returns per schema, or pass `error`
    to make every call raise it (to test error propagation). Every call is
    recorded in `.calls` as `(schema_name, messages)` so tests can assert
    on what the graph actually requested and in what order, without
    inspecting prompt content.
    """

    def __init__(
        self,
        structured_responses: dict[str, BaseModel] | None = None,
        error: Exception | None = None,
    ):
        super().__init__(provider_name="fake", model="fake-model", timeout_seconds=5, max_retries=0)
        self._structured_responses = structured_responses or {}
        self._error = error
        self.calls: list[tuple[str, list[LLMMessage]]] = []

    async def generate_text(self, messages: list[LLMMessage]):
        raise NotImplementedError("FakeLLMProvider.generate_text is not used by the interview workflow")

    async def generate_structured(self, messages: list[LLMMessage], output_schema: type[BaseModel]):
        self.calls.append((output_schema.__name__, messages))
        if self._error is not None:
            raise self._error
        data = self._structured_responses.get(output_schema.__name__)
        if data is None:
            raise AssertionError(
                f"FakeLLMProvider has no configured structured response for {output_schema.__name__}"
            )
        return StructuredLLMResponse(data=data, model=self.model)


class FakeInterviewRepository:
    """In-memory stand-in for `InterviewRepository`, covering only what
    `app.workflows.interview.nodes.load_interview_context` calls
    (`get_session`, `get_topics`, `get_current_question`, `get_question`).
    Lets workflow tests run without a database. Pass real (unpersisted)
    `InterviewSession`/`InterviewTopicEntry`/`InterviewQuestion` instances
    so the fake stays honest about the real model shapes.
    """

    def __init__(
        self,
        session=None,
        topics=None,
        current_question=None,
        questions_by_id: dict[UUID, object] | None = None,
    ):
        self.session = session
        self.topics = topics or []
        self.current_question = current_question
        self.questions_by_id = questions_by_id or {}

    def get_session(self, session_id: UUID):
        if self.session is not None and self.session.id == session_id:
            return self.session
        return None

    def get_topics(self, session_id: UUID):
        return self.topics

    def get_current_question(self, session_id: UUID):
        return self.current_question

    def get_question(self, question_id: UUID):
        return self.questions_by_id.get(question_id)


def _deterministic_vector(text: str, dimension: int) -> list[float]:
    """A stable, dependency-free stand-in for a real embedding: the same
    text always produces the same vector (via a SHA-256 digest), and
    different text produces a different vector — good enough to exercise
    ordering/filtering logic without needing numpy or a real model."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return [(digest[i % len(digest)] / 127.5) - 1.0 for i in range(dimension)]


class FakeEmbeddingProvider(EmbeddingProvider):
    """Deterministic in-memory stand-in for `EmbeddingProvider` — no
    network, no real model. Configure `error` to make every call raise it
    (to test error propagation). Every call is recorded in `.calls`."""

    def __init__(self, dimension: int = 8, error: Exception | None = None):
        super().__init__(provider_name="fake", model="fake-embedding-model", dimension=dimension)
        self._error = error
        self.calls: list[str] = []

    async def embed(self, text: str) -> list[float]:
        return (await self.embed_many([text]))[0]

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        await asyncio.sleep(0)
        if self._error is not None:
            raise self._error
        if not texts:
            return []
        self.calls.extend(texts)
        return [_deterministic_vector(text, self.dimension) for text in texts]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class FakeKnowledgeStore(KnowledgeStore):
    """In-memory stand-in for `KnowledgeStore` — no network, no real
    Qdrant. Applies exact role/topic/(concept) filtering like the real
    store, then ranks matches by cosine similarity against the query
    vector using plain Python (the fixed, tiny test dimension makes numpy
    unnecessary here). Configure `error` to make every call raise it.
    """

    def __init__(self, error: Exception | None = None):
        self._entries: dict[UUID, tuple[KnowledgeChunk, list[float]]] = {}
        self._error = error

    async def upsert(self, chunks: list[KnowledgeChunk], vectors: list[list[float]]) -> None:
        await asyncio.sleep(0)
        if self._error is not None:
            raise self._error
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must be the same length")
        for chunk, vector in zip(chunks, vectors, strict=True):
            self._entries[chunk.id] = (chunk, vector)

    async def search(
        self,
        query_vector: list[float],
        role: Role,
        topic: InterviewTopic,
        concept: str | None = None,
        limit: int = 5,
    ) -> list[KnowledgeSearchResult]:
        await asyncio.sleep(0)
        if self._error is not None:
            raise self._error
        matches = [
            (chunk, vector)
            for chunk, vector in self._entries.values()
            if chunk.role == role and chunk.topic == topic and (concept is None or chunk.concept == concept)
        ]
        scored = [(chunk, _cosine_similarity(query_vector, vector)) for chunk, vector in matches]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return [
            KnowledgeSearchResult(
                content=chunk.content,
                score=score,
                role=chunk.role,
                topic=chunk.topic,
                concept=chunk.concept,
                metadata={
                    k: v
                    for k, v in {
                        "source": chunk.source,
                        "title": chunk.title,
                        "section": chunk.section,
                        "difficulty": chunk.difficulty,
                        "tags": chunk.tags,
                    }.items()
                    if v not in (None, [])
                },
            )
            for chunk, score in scored[:limit]
        ]

    async def delete(self, chunk_ids: list[UUID]) -> None:
        await asyncio.sleep(0)
        if self._error is not None:
            raise self._error
        for chunk_id in chunk_ids:
            self._entries.pop(chunk_id, None)
