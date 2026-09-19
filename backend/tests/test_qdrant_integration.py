"""Genuine integration test against a real Qdrant server.

Unlike tests/test_knowledge_store.py (which uses an in-memory fake so unit
tests don't require Qdrant), this test opens a real connection and creates
a real collection. Gated behind `RUN_QDRANT_INTEGRATION_TESTS=true` so the
default test suite never makes network calls to Qdrant — and if Qdrant
isn't reachable even with the flag set, it skips cleanly with the actual
connection error rather than faking a pass, the same honesty standard
already established for PostgreSQL (test_db.py), Redis
(test_redis_integration.py), and the real LLM providers
(test_llm_integration.py).
"""

import os
import uuid

import httpx
import pytest
import pytest_asyncio
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import ApiException

from app.core.config import settings
from app.domain.enums import InterviewTopic, Role
from app.knowledge.models import KnowledgeChunk
from app.knowledge.seed_data import seed_knowledge_store
from app.knowledge.store.qdrant import QdrantKnowledgeStore
from tests.fakes import FakeEmbeddingProvider

RUN_INTEGRATION = os.environ.get("RUN_QDRANT_INTEGRATION_TESTS", "").lower() == "true"

pytestmark = pytest.mark.skipif(
    not RUN_INTEGRATION,
    reason="RUN_QDRANT_INTEGRATION_TESTS is not set to 'true' — skipping real Qdrant calls.",
)


@pytest.fixture()
def collection_name() -> str:
    # A unique, throwaway collection per test run so this never collides
    # with a real deployment's `interview_knowledge` collection.
    return f"test_interview_knowledge_{uuid.uuid4().hex[:8]}"


@pytest_asyncio.fixture()
async def real_store(collection_name: str):
    embedding_provider = FakeEmbeddingProvider(dimension=8)
    store = QdrantKnowledgeStore(
        url=settings.qdrant_url,
        collection_name=collection_name,
        vector_size=embedding_provider.dimension,
        api_key=settings.qdrant_api_key,
    )
    probe = AsyncQdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
    try:
        await probe.get_collections()
    except (ApiException, httpx.HTTPError, OSError) as exc:
        await probe.close()
        pytest.skip(f"Qdrant is not reachable at {settings.qdrant_url}: {exc}")
    await probe.close()

    yield store, embedding_provider

    await store._client.delete_collection(collection_name)  # noqa: SLF001 — test-only cleanup
    await store.close()


@pytest.mark.asyncio
async def test_real_qdrant_upsert_and_filtered_search_roundtrip(real_store):
    store, embedding_provider = real_store
    chunk = KnowledgeChunk(
        role=Role.BACKEND_DEVELOPER,
        topic=InterviewTopic.DATABASES,
        concept="indexing",
        content="An index speeds up lookups at the cost of writes.",
    )
    vector = await embedding_provider.embed(chunk.content)

    await store.upsert([chunk], [vector])
    results = await store.search(
        query_vector=vector, role=Role.BACKEND_DEVELOPER, topic=InterviewTopic.DATABASES, concept="indexing"
    )

    assert len(results) == 1
    assert results[0].content == chunk.content
    assert results[0].concept == "indexing"


@pytest.mark.asyncio
async def test_real_qdrant_filters_out_non_matching_role_topic(real_store):
    store, embedding_provider = real_store
    react_chunk = KnowledgeChunk(
        role=Role.FRONTEND_DEVELOPER, topic=InterviewTopic.REACT, concept="hooks", content="React hooks hold state."
    )
    vector = await embedding_provider.embed(react_chunk.content)
    await store.upsert([react_chunk], [vector])

    results = await store.search(
        query_vector=vector, role=Role.BACKEND_DEVELOPER, topic=InterviewTopic.DATABASES
    )

    assert results == []


@pytest.mark.asyncio
async def test_real_qdrant_seed_dataset_upserts_successfully(real_store):
    store, embedding_provider = real_store

    count = await seed_knowledge_store(store, embedding_provider)

    assert count > 0
    results = await store.search(
        query_vector=await embedding_provider.embed("hooks"),
        role=Role.FRONTEND_DEVELOPER,
        topic=InterviewTopic.REACT,
    )
    assert len(results) >= 1
