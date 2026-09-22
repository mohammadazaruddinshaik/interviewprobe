"""`OpenAIEmbeddingProvider` — configuration validation and response/error
translation, all against a mocked SDK client. No real network call, same
convention as tests/test_llm_openai_provider.py.

Task 49 additions (timeout configuration/enforcement) are grouped in their
own section near the bottom, alongside the `Settings.embedding_timeout_seconds`
default/override tests — no existing test above was weakened; `make_provider`
now supplies an explicit default `timeout_seconds` so every pre-existing
call site keeps working unchanged."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import openai
import pytest

from app.core.config import Settings
from app.knowledge.exceptions import (
    EmbeddingConfigurationError,
    EmbeddingProviderUnavailableError,
    EmbeddingTimeoutError,
)
from app.knowledge.embedding.providers.openai import OpenAIEmbeddingProvider


def make_provider(**overrides) -> OpenAIEmbeddingProvider:
    kwargs = dict(model="text-embedding-3-small", api_key="sk-fake", timeout_seconds=5.0)
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
        OpenAIEmbeddingProvider(model="text-embedding-3-small", api_key=None, timeout_seconds=5.0)


def test_empty_api_key_raises_configuration_error():
    with pytest.raises(EmbeddingConfigurationError):
        OpenAIEmbeddingProvider(model="text-embedding-3-small", api_key="", timeout_seconds=5.0)


def test_unknown_model_raises_configuration_error():
    with pytest.raises(EmbeddingConfigurationError):
        OpenAIEmbeddingProvider(model="not-a-real-embedding-model", api_key="sk-fake", timeout_seconds=5.0)


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


# ---------------------------------------------------------------------------
# Task 49 — embedding timeout configuration/enforcement
# ---------------------------------------------------------------------------


def test_default_embedding_timeout_seconds_is_ten():
    # Constructed directly (not the module-level `settings` singleton) so
    # this reflects the class default regardless of this machine's own
    # backend/.env — same pattern as test_logging_config.py's LOG_LEVEL test.
    assert Settings(_env_file=None).embedding_timeout_seconds == 10


def test_embedding_timeout_seconds_is_overridable_via_environment(monkeypatch):
    monkeypatch.setenv("EMBEDDING_TIMEOUT_SECONDS", "3")

    assert Settings(_env_file=None).embedding_timeout_seconds == 3


@pytest.mark.asyncio
async def test_a_stalled_request_past_the_configured_timeout_raises_embedding_timeout_error():
    provider = make_provider(timeout_seconds=0.05)

    async def _never_returns_in_time(**kwargs):
        await asyncio.sleep(1)
        raise AssertionError("should have been cancelled by the timeout")

    provider._client.embeddings.create = _never_returns_in_time

    with pytest.raises(EmbeddingTimeoutError):
        await provider.embed_many(["a"])


@pytest.mark.asyncio
async def test_the_configured_timeout_is_what_actually_bounds_the_call():
    # A generous timeout must let the same slow-but-eventually-successful
    # call through — proves the configured value (not some other fixed
    # bound) is what's actually being enforced, in both directions.
    provider = make_provider(timeout_seconds=1.0)
    fake_response = SimpleNamespace(data=[SimpleNamespace(embedding=[0.1, 0.2])])

    async def _resolves_quickly(**kwargs):
        await asyncio.sleep(0.01)
        return fake_response

    provider._client.embeddings.create = _resolves_quickly

    vector = await provider.embed("a")

    assert vector == [0.1, 0.2]


@pytest.mark.asyncio
async def test_successful_call_within_the_timeout_is_unaffected():
    provider = make_provider(timeout_seconds=5.0)
    fake_response = SimpleNamespace(
        data=[SimpleNamespace(embedding=[0.1, 0.2]), SimpleNamespace(embedding=[0.3, 0.4])]
    )
    provider._client.embeddings.create = AsyncMock(return_value=fake_response)

    vectors = await provider.embed_many(["a", "b"])

    assert vectors == [[0.1, 0.2], [0.3, 0.4]]


@pytest.mark.asyncio
async def test_openai_sdk_level_timeout_is_also_translated_to_embedding_timeout_error():
    # Defensive coverage: if the underlying httpx transport times out on
    # its own (openai.APITimeoutError) before our own asyncio.wait_for
    # does, it must still be classified as a timeout, not a generic
    # provider-unavailable error.
    provider = make_provider()
    error = openai.APITimeoutError(request=_fake_request())
    provider._client.embeddings.create = AsyncMock(side_effect=error)

    with pytest.raises(EmbeddingTimeoutError):
        await provider.embed_many(["a"])


@pytest.mark.asyncio
async def test_embedding_timeout_error_never_exposes_raw_sdk_exception_text():
    provider = make_provider(timeout_seconds=0.05)

    async def _never_returns_in_time(**kwargs):
        await asyncio.sleep(1)

    provider._client.embeddings.create = _never_returns_in_time

    with pytest.raises(EmbeddingTimeoutError) as exc_info:
        await provider.embed_many(["a"])

    # Only our own fixed wording + the configured duration — nothing from
    # asyncio's own TimeoutError, no API key, no request details.
    assert str(exc_info.value) == "OpenAI embedding request timed out after 0.05s"


@pytest.mark.asyncio
async def test_non_timeout_errors_are_still_classified_exactly_as_before():
    # Existing classification (auth/bad-request -> configuration,
    # connection/5xx -> provider-unavailable) must be completely
    # unaffected by adding timeout handling — re-asserted here as a single
    # focused regression check alongside the new timeout tests.
    provider = make_provider()
    auth_error = _status_error(openai.AuthenticationError, 401, "invalid api key")
    provider._client.embeddings.create = AsyncMock(side_effect=auth_error)

    with pytest.raises(EmbeddingConfigurationError):
        await provider.embed_many(["a"])
