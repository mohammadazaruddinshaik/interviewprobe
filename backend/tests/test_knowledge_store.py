"""Task 19 — the `KnowledgeStore` abstraction, exercised via the in-memory
`FakeKnowledgeStore` (no network, no real Qdrant)."""

import uuid

import pytest

from app.domain.enums import InterviewTopic, Role
from app.knowledge.exceptions import KnowledgeStoreUnavailableError
from app.knowledge.models import KnowledgeChunk
from tests.fakes import FakeKnowledgeStore


def _chunk(role: Role, topic: InterviewTopic, concept: str, content: str) -> KnowledgeChunk:
    return KnowledgeChunk(role=role, topic=topic, concept=concept, content=content)


REACT_HOOKS = _chunk(Role.FRONTEND_DEVELOPER, InterviewTopic.REACT, "hooks", "React hooks let function components hold state.")
REACT_RENDERING = _chunk(Role.FRONTEND_DEVELOPER, InterviewTopic.REACT, "rendering", "React re-renders when state or props change.")
DB_INDEXING = _chunk(Role.BACKEND_DEVELOPER, InterviewTopic.DATABASES, "indexing", "An index speeds up lookups.")
DB_TRANSACTIONS = _chunk(Role.BACKEND_DEVELOPER, InterviewTopic.DATABASES, "transactions", "A transaction groups operations atomically.")


@pytest.mark.asyncio
async def test_upsert_then_search_returns_the_upserted_chunk():
    store = FakeKnowledgeStore()
    await store.upsert([REACT_HOOKS], [[1.0, 0.0, 0.0]])

    results = await store.search(
        query_vector=[1.0, 0.0, 0.0], role=Role.FRONTEND_DEVELOPER, topic=InterviewTopic.REACT
    )

    assert len(results) == 1
    assert results[0].content == REACT_HOOKS.content
    assert results[0].concept == "hooks"


@pytest.mark.asyncio
async def test_search_filters_by_role_and_topic():
    store = FakeKnowledgeStore()
    await store.upsert(
        [REACT_HOOKS, DB_INDEXING],
        [[1.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
    )

    results = await store.search(
        query_vector=[1.0, 0.0, 0.0], role=Role.BACKEND_DEVELOPER, topic=InterviewTopic.DATABASES
    )

    assert len(results) == 1
    assert results[0].concept == "indexing"


@pytest.mark.asyncio
async def test_search_filters_by_concept_when_given():
    store = FakeKnowledgeStore()
    await store.upsert(
        [DB_INDEXING, DB_TRANSACTIONS],
        [[1.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
    )

    results = await store.search(
        query_vector=[1.0, 0.0, 0.0],
        role=Role.BACKEND_DEVELOPER,
        topic=InterviewTopic.DATABASES,
        concept="transactions",
    )

    assert len(results) == 1
    assert results[0].concept == "transactions"


@pytest.mark.asyncio
async def test_search_without_concept_returns_all_matching_topic_concepts():
    store = FakeKnowledgeStore()
    await store.upsert(
        [DB_INDEXING, DB_TRANSACTIONS],
        [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
    )

    results = await store.search(
        query_vector=[1.0, 0.0, 0.0], role=Role.BACKEND_DEVELOPER, topic=InterviewTopic.DATABASES
    )

    assert {r.concept for r in results} == {"indexing", "transactions"}


@pytest.mark.asyncio
async def test_search_orders_by_similarity_to_the_query_vector():
    store = FakeKnowledgeStore()
    # DB_INDEXING's vector exactly matches the query; DB_TRANSACTIONS' is
    # orthogonal (similarity 0) — indexing must rank first.
    await store.upsert(
        [DB_TRANSACTIONS, DB_INDEXING],
        [[0.0, 1.0, 0.0], [1.0, 0.0, 0.0]],
    )

    results = await store.search(
        query_vector=[1.0, 0.0, 0.0], role=Role.BACKEND_DEVELOPER, topic=InterviewTopic.DATABASES
    )

    assert [r.concept for r in results] == ["indexing", "transactions"]
    assert results[0].score > results[1].score


@pytest.mark.asyncio
async def test_search_respects_limit():
    store = FakeKnowledgeStore()
    await store.upsert(
        [REACT_HOOKS, REACT_RENDERING],
        [[1.0, 0.0, 0.0], [0.9, 0.1, 0.0]],
    )

    results = await store.search(
        query_vector=[1.0, 0.0, 0.0], role=Role.FRONTEND_DEVELOPER, topic=InterviewTopic.REACT, limit=1
    )

    assert len(results) == 1


@pytest.mark.asyncio
async def test_search_with_no_matches_returns_empty_list():
    store = FakeKnowledgeStore()
    await store.upsert([REACT_HOOKS], [[1.0, 0.0, 0.0]])

    results = await store.search(
        query_vector=[1.0, 0.0, 0.0], role=Role.JAVA_DEVELOPER, topic=InterviewTopic.CONCURRENCY
    )

    assert results == []


@pytest.mark.asyncio
async def test_delete_removes_the_chunk_from_search_results():
    store = FakeKnowledgeStore()
    await store.upsert([REACT_HOOKS], [[1.0, 0.0, 0.0]])

    await store.delete([REACT_HOOKS.id])

    results = await store.search(
        query_vector=[1.0, 0.0, 0.0], role=Role.FRONTEND_DEVELOPER, topic=InterviewTopic.REACT
    )
    assert results == []


@pytest.mark.asyncio
async def test_delete_of_unknown_id_is_a_clean_noop():
    store = FakeKnowledgeStore()

    await store.delete([uuid.uuid4()])  # does not raise


@pytest.mark.asyncio
async def test_upsert_mismatched_lengths_raises():
    store = FakeKnowledgeStore()

    with pytest.raises(ValueError):
        await store.upsert([REACT_HOOKS, REACT_RENDERING], [[1.0, 0.0, 0.0]])


@pytest.mark.asyncio
async def test_store_unavailable_propagates_as_domain_error():
    store = FakeKnowledgeStore(error=KnowledgeStoreUnavailableError("simulated Qdrant outage"))

    with pytest.raises(KnowledgeStoreUnavailableError):
        await store.search(query_vector=[1.0, 0.0, 0.0], role=Role.FRONTEND_DEVELOPER, topic=InterviewTopic.REACT)
