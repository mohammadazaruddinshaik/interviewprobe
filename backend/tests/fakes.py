"""Small test doubles shared across test modules."""

import asyncio
import hashlib
import io
import math
import time
from uuid import UUID

from docx import Document
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

    async def ping(self) -> bool:
        # Task 50 — GET /ready's Redis check. Not exercised by any
        # lock/rate-limit/idempotency code (none of it pings), only by
        # app.core.readiness.check_redis.
        await asyncio.sleep(0)
        return True

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
    ping = _fail  # Task 50 — GET /ready's Redis check

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
        questions: list | None = None,
    ):
        self.session = session
        self.topics = topics or []
        self.current_question = current_question
        self.questions_by_id = questions_by_id or {}
        # Defaults to `[current_question]` (or `[]`) rather than always
        # `[]` — callers that never pass `questions` explicitly still get a
        # `questions_on_current_topic` count of 1 (matching "the current
        # question already belongs to its own topic"), not a silently wrong
        # 0 that would make every existing FakeInterviewRepository(...) test
        # look like a brand-new topic.
        self.questions = questions if questions is not None else ([current_question] if current_question else [])

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

    def get_questions(self, session_id: UUID):
        return self.questions


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


# ---------------------------------------------------------------------------
# Phase 2 — resume upload test fixtures. Real, minimal, hand-built file
# bytes (not fixture files on disk) so resume extraction tests exercise
# the actual pypdf/python-docx parsing path end to end, without needing a
# binary test asset committed to the repo.
# ---------------------------------------------------------------------------


def make_test_pdf_bytes(text: str = "Test Resume Content For Extraction") -> bytes:
    """A minimal, real, single-page PDF with `text` as extractable content
    (real PDF syntax, not a fake magic-bytes-only stub) — pypdf reads it
    exactly like a real resume export."""
    content = f"BT /F1 24 Tf 72 712 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> "
        b"/MediaBox [0 0 612 792] /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(content)} >>\nstream\n".encode() + content + b"\nendstream",
    ]

    buf = io.BytesIO()
    buf.write(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(buf.tell())
        buf.write(f"{i} 0 obj\n".encode())
        buf.write(obj)
        buf.write(b"\nendobj\n")
    xref_offset = buf.tell()
    buf.write(f"xref\n0 {len(objects) + 1}\n".encode())
    buf.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        buf.write(f"{offset:010d} 00000 n \n".encode())
    buf.write(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode())
    return buf.getvalue()


def make_test_pdf_with_no_text_bytes() -> bytes:
    """A structurally valid single-page PDF with an empty content stream
    (no `Tj`/text-showing operator at all) — simulates a scanned PDF with
    no extractable text layer, without needing real image data."""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /Resources << >> /MediaBox [0 0 612 792] /Contents 4 0 R >>",
        b"<< /Length 0 >>\nstream\n\nendstream",
    ]

    buf = io.BytesIO()
    buf.write(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(buf.tell())
        buf.write(f"{i} 0 obj\n".encode())
        buf.write(obj)
        buf.write(b"\nendobj\n")
    xref_offset = buf.tell()
    buf.write(f"xref\n0 {len(objects) + 1}\n".encode())
    buf.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        buf.write(f"{offset:010d} 00000 n \n".encode())
    buf.write(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode())
    return buf.getvalue()


def make_test_docx_bytes(text: str = "Test Resume Content For Extraction") -> bytes:
    """A minimal, real .docx (via python-docx's own writer) with `text` as
    a paragraph — read back by the same python-docx parsing path
    `extract_resume_text` uses."""
    document = Document()
    document.add_paragraph(text)
    buf = io.BytesIO()
    document.save(buf)
    return buf.getvalue()
