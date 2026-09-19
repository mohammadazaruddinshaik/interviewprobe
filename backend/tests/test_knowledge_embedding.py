"""Task 19 — the `EmbeddingProvider` abstraction, exercised via the
deterministic `FakeEmbeddingProvider` (no network, no real model)."""

import pytest

from app.knowledge.exceptions import EmbeddingProviderUnavailableError
from tests.fakes import FakeEmbeddingProvider


@pytest.mark.asyncio
async def test_embed_is_deterministic_for_the_same_text():
    provider = FakeEmbeddingProvider(dimension=8)

    first = await provider.embed("What is an index?")
    second = await provider.embed("What is an index?")

    assert first == second
    assert len(first) == 8


@pytest.mark.asyncio
async def test_embed_differs_for_different_text():
    provider = FakeEmbeddingProvider(dimension=8)

    a = await provider.embed("React hooks")
    b = await provider.embed("Database indexing")

    assert a != b


@pytest.mark.asyncio
async def test_embed_many_returns_one_vector_per_text_in_order():
    provider = FakeEmbeddingProvider(dimension=4)
    texts = ["closures", "event loop", "promises"]

    vectors = await provider.embed_many(texts)

    assert len(vectors) == 3
    assert all(len(v) == 4 for v in vectors)
    # Batch embedding agrees with individual embedding for the same text.
    assert vectors[0] == await provider.embed("closures")


@pytest.mark.asyncio
async def test_embed_many_empty_list_returns_empty_list():
    provider = FakeEmbeddingProvider()

    vectors = await provider.embed_many([])

    assert vectors == []


@pytest.mark.asyncio
async def test_embed_empty_text_is_handled_deterministically_not_a_crash():
    provider = FakeEmbeddingProvider(dimension=8)

    vector = await provider.embed("")

    assert len(vector) == 8
    # Still deterministic for the same (empty) input.
    assert vector == await provider.embed("")


@pytest.mark.asyncio
async def test_embed_records_calls():
    provider = FakeEmbeddingProvider()

    await provider.embed("first")
    await provider.embed_many(["second", "third"])

    assert provider.calls == ["first", "second", "third"]


@pytest.mark.asyncio
async def test_embedding_failure_propagates_as_embedding_error():
    provider = FakeEmbeddingProvider(error=EmbeddingProviderUnavailableError("simulated outage"))

    with pytest.raises(EmbeddingProviderUnavailableError):
        await provider.embed("anything")


def test_provider_exposes_its_vector_dimension():
    provider = FakeEmbeddingProvider(dimension=1536)

    assert provider.dimension == 1536
    assert provider.provider_name == "fake"
