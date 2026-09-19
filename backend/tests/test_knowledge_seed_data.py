"""Task 19 — the small deterministic seed dataset used for development/
testing. Not a real knowledge base; just enough to prove role/topic-aware
retrieval works end to end."""

import pytest

from app.domain.enums import InterviewTopic, Role
from app.knowledge.seed_data import SEED_KNOWLEDGE, seed_knowledge_store
from tests.fakes import FakeEmbeddingProvider, FakeKnowledgeStore

REQUIRED_COVERAGE = {
    (Role.FRONTEND_DEVELOPER, InterviewTopic.REACT),
    (Role.FRONTEND_DEVELOPER, InterviewTopic.JAVASCRIPT),
    (Role.BACKEND_DEVELOPER, InterviewTopic.REST_APIS),
    (Role.BACKEND_DEVELOPER, InterviewTopic.DATABASES),
    (Role.AI_ENGINEER, InterviewTopic.RAG),
    (Role.AI_ENGINEER, InterviewTopic.EMBEDDINGS_VECTOR_DB),
    (Role.JAVA_DEVELOPER, InterviewTopic.COLLECTIONS),
    (Role.JAVA_DEVELOPER, InterviewTopic.CONCURRENCY),
}


def test_seed_dataset_is_small_and_deterministic():
    # "Small" — proving filtering works, not a real knowledge base.
    assert 1 < len(SEED_KNOWLEDGE) < 50


def test_seed_dataset_covers_every_required_role_topic_pair():
    covered = {(chunk.role, chunk.topic) for chunk in SEED_KNOWLEDGE}

    assert REQUIRED_COVERAGE <= covered


def test_seed_dataset_has_no_duplicate_ids():
    ids = [chunk.id for chunk in SEED_KNOWLEDGE]

    assert len(ids) == len(set(ids))


def test_every_seed_chunk_has_non_empty_content():
    assert all(chunk.content.strip() for chunk in SEED_KNOWLEDGE)


@pytest.mark.asyncio
async def test_seed_knowledge_store_upserts_all_chunks_and_they_become_searchable():
    embedding_provider = FakeEmbeddingProvider(dimension=8)
    store = FakeKnowledgeStore()

    count = await seed_knowledge_store(store, embedding_provider)

    assert count == len(SEED_KNOWLEDGE)
    results = await store.search(
        query_vector=await embedding_provider.embed("hooks"),
        role=Role.FRONTEND_DEVELOPER,
        topic=InterviewTopic.REACT,
    )
    assert len(results) >= 1


@pytest.mark.asyncio
async def test_seed_knowledge_store_with_empty_chunk_list_is_a_noop():
    embedding_provider = FakeEmbeddingProvider()
    store = FakeKnowledgeStore()

    count = await seed_knowledge_store(store, embedding_provider, chunks=[])

    assert count == 0
    assert embedding_provider.calls == []
