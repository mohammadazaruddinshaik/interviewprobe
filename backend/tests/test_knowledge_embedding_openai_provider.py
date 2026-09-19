"""`OpenAIEmbeddingProvider` — configuration validation and response/error
translation, all against a mocked SDK client. No real network call, same
convention as tests/test_llm_openai_provider.py."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import openai
import pytest

from app.knowledge.exceptions import EmbeddingConfigurationError, EmbeddingProviderUnavailableError
from app.knowledge.embedding.providers.openai import OpenAIEmbeddingProvider


def make_provider(**overrides) -> OpenAIEmbeddingProvider:
    kwargs = dict(model="text-embedding-3-small", api_key="sk-fake")
    kwargs.update(overrides)
    return OpenAIEmbeddingProvider(**kwargs)


def _fake_request() -> httpx.Request:
    return httpx.Request("POST", "https://api.openai.com/v1/embeddings")


def _status_error(cls, status_code: int, message: str = "error"):
    response = httpx.Response(status_code, request=_fake_request())
    return cls(message, response=response, body=None)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def test_missing_api_key_raises_configuration_error():
    with pytest.raises(EmbeddingConfigurationError):
        OpenAIEmbeddingProvider(model="text-embedding-3-small", api_key=None)


def test_empty_api_key_raises_configuration_error():
    with pytest.raises(EmbeddingConfigurationError):
        OpenAIEmbeddingProvider(model="text-embedding-3-small", api_key="")


def test_unknown_model_raises_configuration_error():
    with pytest.raises(EmbeddingConfigurationError):
        OpenAIEmbeddingProvider(model="not-a-real-embedding-model", api_key="sk-fake")


def test_dimension_comes_from_the_selected_model_not_a_hardcoded_constant():
    small = make_provider(model="text-embedding-3-small")
    large = make_provider(model="text-embedding-3-large")

    assert small.dimension == 1536
    assert large.dimension == 3072
    assert small.dimension != large.dimension


# ---------------------------------------------------------------------------
# embed / embed_many normalization
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_embed_many_normalizes_response_into_plain_vectors():
    provider = make_provider()
    fake_response = SimpleNamespace(
        data=[SimpleNamespace(embedding=[0.1, 0.2]), SimpleNamespace(embedding=[0.3, 0.4])]
    )
    provider._client.embeddings.create = AsyncMock(return_value=fake_response)

    vectors = await provider.embed_many(["a", "b"])

    assert vectors == [[0.1, 0.2], [0.3, 0.4]]


@pytest.mark.asyncio
async def test_embed_many_empty_list_never_calls_the_sdk():
    provider = make_provider()
    provider._client.embeddings.create = AsyncMock()

    vectors = await provider.embed_many([])

    assert vectors == []
    provider._client.embeddings.create.assert_not_called()


@pytest.mark.asyncio
async def test_embed_delegates_to_embed_many():
    provider = make_provider()
    fake_response = SimpleNamespace(data=[SimpleNamespace(embedding=[0.5, 0.6])])
    provider._client.embeddings.create = AsyncMock(return_value=fake_response)

    vector = await provider.embed("hello")

    assert vector == [0.5, 0.6]


# ---------------------------------------------------------------------------
# Error translation (real OpenAI SDK exception classes, no network)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_authentication_error_is_translated_to_configuration_error():
    provider = make_provider()
    error = _status_error(openai.AuthenticationError, 401, "invalid api key")
    provider._client.embeddings.create = AsyncMock(side_effect=error)

    with pytest.raises(EmbeddingConfigurationError):
        await provider.embed_many(["a"])


@pytest.mark.asyncio
async def test_bad_request_error_is_translated_to_configuration_error():
    provider = make_provider()
    error = _status_error(openai.BadRequestError, 400, "bad request")
    provider._client.embeddings.create = AsyncMock(side_effect=error)

    with pytest.raises(EmbeddingConfigurationError):
        await provider.embed_many(["a"])


@pytest.mark.asyncio
async def test_connection_error_is_translated_to_provider_unavailable():
    provider = make_provider()
    error = openai.APIConnectionError(request=_fake_request())
    provider._client.embeddings.create = AsyncMock(side_effect=error)

    with pytest.raises(EmbeddingProviderUnavailableError):
        await provider.embed_many(["a"])


@pytest.mark.asyncio
async def test_internal_server_error_is_translated_to_provider_unavailable():
    provider = make_provider()
    error = _status_error(openai.InternalServerError, 500, "server error")
    provider._client.embeddings.create = AsyncMock(side_effect=error)

    with pytest.raises(EmbeddingProviderUnavailableError):
        await provider.embed_many(["a"])


@pytest.mark.asyncio
async def test_translated_errors_never_expose_the_raw_sdk_exception_type():
    provider = make_provider()
    error = _status_error(openai.InternalServerError, 500, "server error with sensitive detail")
    provider._client.embeddings.create = AsyncMock(side_effect=error)

    with pytest.raises(EmbeddingProviderUnavailableError) as exc_info:
        await provider.embed_many(["a"])

    assert "sensitive detail" not in str(exc_info.value)
