from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx2
import openai
import pytest
from pydantic import BaseModel

from app.llm.exceptions import (
    LLMConfigurationError,
    LLMInvalidResponseError,
    LLMProviderUnavailableError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from app.llm.models import LLMMessage
from app.llm.providers.openai import OpenAIProvider


class ExampleOutput(BaseModel):
    answer: str
    score: float


def make_provider(**overrides) -> OpenAIProvider:
    kwargs = dict(model="gpt-4o-mini", api_key="sk-fake", timeout_seconds=5, max_retries=1)
    kwargs.update(overrides)
    return OpenAIProvider(**kwargs)


def _fake_request() -> httpx2.Request:
    return httpx2.Request("POST", "https://api.openai.com/v1/chat/completions")


def _status_error(cls, status_code: int, message: str = "error"):
    response = httpx2.Response(status_code, request=_fake_request())
    return cls(message, response=response, body=None)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def test_missing_api_key_raises_configuration_error():
    with pytest.raises(LLMConfigurationError):
        OpenAIProvider(model="gpt-4o-mini", api_key=None, timeout_seconds=5, max_retries=1)


def test_empty_api_key_raises_configuration_error():
    with pytest.raises(LLMConfigurationError):
        OpenAIProvider(model="gpt-4o-mini", api_key="", timeout_seconds=5, max_retries=1)


# ---------------------------------------------------------------------------
# generate_text normalization
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_text_normalizes_response():
    provider = make_provider()
    fake_completion = SimpleNamespace(
        model="gpt-4o-mini-2024-07-18",
        choices=[SimpleNamespace(message=SimpleNamespace(content="Hello there"))],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15),
    )
    provider._client.chat.completions.create = AsyncMock(return_value=fake_completion)

    response = await provider.generate_text([LLMMessage(role="user", content="Hi")])

    assert response.content == "Hello there"
    assert response.model == "gpt-4o-mini-2024-07-18"
    assert response.usage.total_tokens == 15


@pytest.mark.asyncio
async def test_generate_text_raises_invalid_response_when_content_is_none():
    provider = make_provider()
    fake_completion = SimpleNamespace(
        model="gpt-4o-mini",
        choices=[SimpleNamespace(message=SimpleNamespace(content=None))],
        usage=None,
    )
    provider._client.chat.completions.create = AsyncMock(return_value=fake_completion)

    with pytest.raises(LLMInvalidResponseError):
        await provider.generate_text([LLMMessage(role="user", content="Hi")])


# ---------------------------------------------------------------------------
# generate_structured normalization
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_structured_returns_validated_pydantic_instance():
    provider = make_provider()
    parsed = ExampleOutput(answer="42", score=0.9)
    fake_completion = SimpleNamespace(
        model="gpt-4o-mini",
        choices=[SimpleNamespace(message=SimpleNamespace(parsed=parsed, refusal=None))],
        usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2),
    )
    provider._client.chat.completions.parse = AsyncMock(return_value=fake_completion)

    result = await provider.generate_structured([LLMMessage(role="user", content="Hi")], ExampleOutput)

    assert isinstance(result.data, ExampleOutput)
    assert result.data.answer == "42"
    assert result.data.score == 0.9
    assert result.usage.total_tokens == 2


@pytest.mark.asyncio
async def test_generate_structured_raises_invalid_response_when_parsed_is_none():
    provider = make_provider()
    fake_completion = SimpleNamespace(
        model="gpt-4o-mini",
        choices=[SimpleNamespace(message=SimpleNamespace(parsed=None, refusal="policy violation"))],
        usage=None,
    )
    provider._client.chat.completions.parse = AsyncMock(return_value=fake_completion)

    with pytest.raises(LLMInvalidResponseError, match="policy violation"):
        await provider.generate_structured([LLMMessage(role="user", content="Hi")], ExampleOutput)


# ---------------------------------------------------------------------------
# Error translation (real OpenAI SDK exception classes, no network)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rate_limit_error_is_translated():
    provider = make_provider(max_retries=0)
    error = _status_error(openai.RateLimitError, 429, "slow down")
    provider._client.chat.completions.create = AsyncMock(side_effect=error)

    with pytest.raises(LLMRateLimitError):
        await provider.generate_text([LLMMessage(role="user", content="Hi")])


@pytest.mark.asyncio
async def test_authentication_error_is_translated_to_configuration_error():
    provider = make_provider(max_retries=3)
    error = _status_error(openai.AuthenticationError, 401, "invalid api key")
    call_count = {"n": 0}

    async def create(**kwargs):
        call_count["n"] += 1
        raise error

    provider._client.chat.completions.create = create

    with pytest.raises(LLMConfigurationError):
        await provider.generate_text([LLMMessage(role="user", content="Hi")])
    assert call_count["n"] == 1  # not retried


@pytest.mark.asyncio
async def test_bad_request_error_is_translated_to_invalid_response_error():
    provider = make_provider(max_retries=3)
    error = _status_error(openai.BadRequestError, 400, "malformed request")
    call_count = {"n": 0}

    async def create(**kwargs):
        call_count["n"] += 1
        raise error

    provider._client.chat.completions.create = create

    with pytest.raises(LLMInvalidResponseError):
        await provider.generate_text([LLMMessage(role="user", content="Hi")])
    assert call_count["n"] == 1  # not retried


@pytest.mark.asyncio
async def test_internal_server_error_is_translated_and_retried():
    provider = make_provider(max_retries=1)
    error = _status_error(openai.InternalServerError, 500, "server error")
    call_count = {"n": 0}

    async def create(**kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise error
        return SimpleNamespace(
            model="gpt-4o-mini",
            choices=[SimpleNamespace(message=SimpleNamespace(content="recovered"))],
            usage=None,
        )

    provider._client.chat.completions.create = create

    response = await provider.generate_text([LLMMessage(role="user", content="Hi")])

    assert response.content == "recovered"
    assert call_count["n"] == 2


@pytest.mark.asyncio
async def test_connection_error_is_translated_to_provider_unavailable():
    provider = make_provider(max_retries=0)
    error = openai.APIConnectionError(message="connection failed", request=_fake_request())
    provider._client.chat.completions.create = AsyncMock(side_effect=error)

    with pytest.raises(LLMProviderUnavailableError):
        await provider.generate_text([LLMMessage(role="user", content="Hi")])


@pytest.mark.asyncio
async def test_api_timeout_error_is_translated_to_llm_timeout_error():
    provider = make_provider(max_retries=3)
    error = openai.APITimeoutError(request=_fake_request())
    call_count = {"n": 0}

    async def create(**kwargs):
        call_count["n"] += 1
        raise error

    provider._client.chat.completions.create = create

    with pytest.raises(LLMTimeoutError):
        await provider.generate_text([LLMMessage(role="user", content="Hi")])
    assert call_count["n"] == 1  # timeouts are not retried
