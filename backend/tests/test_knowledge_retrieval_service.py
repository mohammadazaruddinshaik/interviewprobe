"""Task 19 — `KnowledgeRetrievalService`: role/topic/concept-aware
retrieval on top of `EmbeddingProvider` + `KnowledgeStore`, exercised
entirely with fakes (no network)."""

import pytest

from app.domain.enums import InterviewTopic, Role
from app.knowledge.exceptions import EmbeddingProviderUnavailableError, KnowledgeRetrievalError, KnowledgeStoreUnavailableError
from app.knowledge.models import KnowledgeChunk
from app.knowledge.retrieval_service import KnowledgeRetrievalService
from tests.fakes import FakeEmbeddingProvider, FakeKnowledgeStore


def _chunk(role: Role, topic: InterviewTopic, concept: str, content: str) -> KnowledgeChunk:
    return KnowledgeChunk(role=role, topic=topic, concept=concept, content=content)


async def _seeded_service() -> tuple[KnowledgeRetrievalService, FakeEmbeddingProvider, FakeKnowledgeStore]:
    embedding_provider = FakeEmbeddingProvider(dimension=8)
    store = FakeKnowledgeStore()
    chunks = [
        _chunk(Role.FRONTEND_DEVELOPER, InterviewTopic.REACT, "hooks", "React hooks hold state in function components."),
        _chunk(Role.FRONTEND_DEVELOPER, InterviewTopic.REACT, "rendering", "React re-renders when state changes."),
        _chunk(Role.BACKEND_DEVELOPER, InterviewTopic.DATABASES, "indexing", "An index speeds up lookups."),
        _chunk(Role.AI_ENGINEER, InterviewTopic.RAG, "retrieval", "RAG fetches relevant context before generation."),
        _chunk(Role.JAVA_DEVELOPER, InterviewTopic.COLLECTIONS, "list_set_map", "List preserves insertion order."),
    ]
    vectors = await embedding_provider.embed_many([c.content for c in chunks])
    await store.upsert(chunks, vectors)
    service = KnowledgeRetrievalService(embedding_provider=embedding_provider, store=store)
    return service, embedding_provider, store


@pytest.mark.asyncio
async def test_frontend_react_query_does_not_return_other_roles_or_topics():
    service, _, _ = await _seeded_service()

    results = await service.search(
        query="How do hooks work?", role=Role.FRONTEND_DEVELOPER, topic=InterviewTopic.REACT
    )

    assert len(results) == 2  # only the two REACT chunks
    assert all(r.role is Role.FRONTEND_DEVELOPER and r.topic is InterviewTopic.REACT for r in results)
    contents = {r.content for r in results}
    assert "An index speeds up lookups." not in contents
    assert "RAG fetches relevant context before generation." not in contents
    assert "List preserves insertion order." not in contents


@pytest.mark.asyncio
async def test_backend_databases_query_returns_only_compatible_knowledge():
    service, _, _ = await _seeded_service()

    results = await service.search(
        query="How do database indexes affect query performance?",
        role=Role.BACKEND_DEVELOPER,
        topic=InterviewTopic.DATABASES,
    )

    assert len(results) == 1
    assert results[0].role is Role.BACKEND_DEVELOPER
    assert results[0].topic is InterviewTopic.DATABASES
    assert results[0].concept == "indexing"


@pytest.mark.asyncio
async def test_concept_specific_retrieval_narrows_further():
    service, _, _ = await _seeded_service()

    results = await service.search(
        query="What are hooks?", role=Role.FRONTEND_DEVELOPER, topic=InterviewTopic.REACT, concept="hooks"
    )

    assert len(results) == 1
    assert results[0].concept == "hooks"


@pytest.mark.asyncio
async def test_ai_engineer_rag_query_isolated_from_everything_else():
    service, _, _ = await _seeded_service()

    results = await service.search(query="What is RAG?", role=Role.AI_ENGINEER, topic=InterviewTopic.RAG)

    assert len(results) == 1
    assert results[0].role is Role.AI_ENGINEER
    assert results[0].topic is InterviewTopic.RAG


@pytest.mark.asyncio
async def test_limit_is_respected():
    service, _, _ = await _seeded_service()

    results = await service.search(
        query="React", role=Role.FRONTEND_DEVELOPER, topic=InterviewTopic.REACT, limit=1
    )

    assert len(results) == 1


@pytest.mark.asyncio
async def test_no_matching_knowledge_returns_empty_list_not_an_error():
    service, _, _ = await _seeded_service()

    results = await service.search(
        query="Concurrency primitives", role=Role.JAVA_DEVELOPER, topic=InterviewTopic.CONCURRENCY
    )

    assert results == []


# ---------------------------------------------------------------------------
# Failure cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalid_role_topic_filter_raises_retrieval_error_without_calling_embedding_or_store():
    embedding_provider = FakeEmbeddingProvider()
    store = FakeKnowledgeStore()
    service = KnowledgeRetrievalService(embedding_provider=embedding_provider, store=store)

    with pytest.raises(KnowledgeRetrievalError):
        # REACT is not a Backend Developer topic.
        await service.search(query="anything", role=Role.BACKEND_DEVELOPER, topic=InterviewTopic.REACT)

    assert embedding_provider.calls == []  # failed fast, before embedding


@pytest.mark.asyncio
async def test_invalid_concept_filter_raises_retrieval_error():
    embedding_provider = FakeEmbeddingProvider()
    store = FakeKnowledgeStore()
    service = KnowledgeRetrievalService(embedding_provider=embedding_provider, store=store)

    with pytest.raises(KnowledgeRetrievalError):
        # "hooks" is not a Databases concept.
        await service.search(
            query="anything", role=Role.BACKEND_DEVELOPER, topic=InterviewTopic.DATABASES, concept="hooks"
        )


@pytest.mark.asyncio
async def test_empty_query_raises_retrieval_error():
    service = KnowledgeRetrievalService(embedding_provider=FakeEmbeddingProvider(), store=FakeKnowledgeStore())

    with pytest.raises(KnowledgeRetrievalError):
        await service.search(query="   ", role=Role.AI_ENGINEER, topic=InterviewTopic.RAG)


@pytest.mark.asyncio
async def test_invalid_limit_raises_retrieval_error():
    service = KnowledgeRetrievalService(embedding_provider=FakeEmbeddingProvider(), store=FakeKnowledgeStore())

    with pytest.raises(KnowledgeRetrievalError):
        await service.search(query="anything", role=Role.AI_ENGINEER, topic=InterviewTopic.RAG, limit=0)


@pytest.mark.asyncio
async def test_embedding_failure_propagates_not_swallowed():
    embedding_provider = FakeEmbeddingProvider(error=EmbeddingProviderUnavailableError("simulated outage"))
    service = KnowledgeRetrievalService(embedding_provider=embedding_provider, store=FakeKnowledgeStore())

    with pytest.raises(EmbeddingProviderUnavailableError):
        await service.search(query="anything", role=Role.AI_ENGINEER, topic=InterviewTopic.RAG)


@pytest.mark.asyncio
async def test_store_unavailable_propagates_not_swallowed():
    store = FakeKnowledgeStore(error=KnowledgeStoreUnavailableError("simulated Qdrant outage"))
    service = KnowledgeRetrievalService(embedding_provider=FakeEmbeddingProvider(), store=store)

    with pytest.raises(KnowledgeStoreUnavailableError):
        await service.search(query="anything", role=Role.AI_ENGINEER, topic=InterviewTopic.RAG)


@pytest.mark.asyncio
async def test_retrieval_log_never_contains_query_text_or_chunk_content(caplog):
    import logging

    service, _, _ = await _seeded_service()
    secret_query = "SuperSecretCandidateQueryText"

    with caplog.at_level(logging.INFO):
        await service.search(query=secret_query, role=Role.FRONTEND_DEVELOPER, topic=InterviewTopic.REACT)

    full_log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert secret_query not in full_log_text
    assert "React hooks hold state in function components." not in full_log_text
