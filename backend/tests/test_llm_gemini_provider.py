from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from google.genai import errors as genai_errors
from pydantic import BaseModel

from app.llm.exceptions import (
    LLMConfigurationError,
    LLMInvalidResponseError,
    LLMProviderUnavailableError,
    LLMRateLimitError,
)
from app.llm.models import LLMMessage
from app.llm.providers.gemini import GeminiProvider, _split_messages


class ExampleOutput(BaseModel):
    answer: str
    score: float


def make_provider(**overrides) -> GeminiProvider:
    kwargs = dict(model="gemini-2.0-flash", api_key="fake-key", timeout_seconds=5, max_retries=1)
    kwargs.update(overrides)
    return GeminiProvider(**kwargs)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def test_missing_api_key_raises_configuration_error():
    with pytest.raises(LLMConfigurationError):
        GeminiProvider(model="gemini-2.0-flash", api_key=None, timeout_seconds=5, max_retries=1)


def test_empty_api_key_raises_configuration_error():
    with pytest.raises(LLMConfigurationError):
        GeminiProvider(model="gemini-2.0-flash", api_key="", timeout_seconds=5, max_retries=1)


# ---------------------------------------------------------------------------
# Message translation (no "system" role, "assistant" -> "model")
# ---------------------------------------------------------------------------


def test_split_messages_extracts_system_instruction():
    system, contents = _split_messages(
        [
            LLMMessage(role="system", content="You are helpful."),
            LLMMessage(role="user", content="Hi"),
        ]
    )

    assert system == "You are helpful."
    assert contents == [{"role": "user", "parts": [{"text": "Hi"}]}]


def test_split_messages_maps_assistant_to_model_role():
    _, contents = _split_messages(
        [
            LLMMessage(role="user", content="Hi"),
            LLMMessage(role="assistant", content="Hello"),
        ]
    )

    assert contents == [
        {"role": "user", "parts": [{"text": "Hi"}]},
        {"role": "model", "parts": [{"text": "Hello"}]},
    ]


def test_split_messages_with_no_system_message_returns_none():
    system, _ = _split_messages([LLMMessage(role="user", content="Hi")])

    assert system is None


# ---------------------------------------------------------------------------
# generate_text normalization
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_text_normalizes_response():
    provider = make_provider()
    fake_response = SimpleNamespace(
        text="Hello there",
        usage_metadata=SimpleNamespace(
            prompt_token_count=10, candidates_token_count=5, total_token_count=15
        ),
    )
    provider._client.aio.models.generate_content = AsyncMock(return_value=fake_response)

    response = await provider.generate_text([LLMMessage(role="user", content="Hi")])

    assert response.content == "Hello there"
    assert response.model == "gemini-2.0-flash"
    assert response.usage.total_tokens == 15


@pytest.mark.asyncio
async def test_generate_text_raises_invalid_response_when_text_is_empty():
    provider = make_provider()
    fake_response = SimpleNamespace(text="", usage_metadata=None)
    provider._client.aio.models.generate_content = AsyncMock(return_value=fake_response)

    with pytest.raises(LLMInvalidResponseError):
        await provider.generate_text([LLMMessage(role="user", content="Hi")])


# ---------------------------------------------------------------------------
# generate_structured normalization
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_structured_returns_validated_pydantic_instance():
    provider = make_provider()
    parsed = ExampleOutput(answer="42", score=0.9)
    fake_response = SimpleNamespace(
        parsed=parsed,
        usage_metadata=SimpleNamespace(
            prompt_token_count=1, candidates_token_count=1, total_token_count=2
        ),
    )
    provider._client.aio.models.generate_content = AsyncMock(return_value=fake_response)

    result = await provider.generate_structured([LLMMessage(role="user", content="Hi")], ExampleOutput)

    assert isinstance(result.data, ExampleOutput)
    assert result.data.answer == "42"
    assert result.usage.total_tokens == 2


@pytest.mark.asyncio
async def test_generate_structured_raises_invalid_response_when_parsed_is_none():
    provider = make_provider()
    fake_response = SimpleNamespace(parsed=None, usage_metadata=None)
    provider._client.aio.models.generate_content = AsyncMock(return_value=fake_response)

    with pytest.raises(LLMInvalidResponseError):
        await provider.generate_structured([LLMMessage(role="user", content="Hi")], ExampleOutput)


# ---------------------------------------------------------------------------
# Error translation (real google-genai SDK exception classes)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rate_limit_status_is_translated():
    provider = make_provider(max_retries=0)
    error = genai_errors.ClientError(429, {"error": {"message": "rate limited"}})
    provider._client.aio.models.generate_content = AsyncMock(side_effect=error)

    with pytest.raises(LLMRateLimitError):
        await provider.generate_text([LLMMessage(role="user", content="Hi")])


@pytest.mark.asyncio
async def test_auth_status_is_translated_to_configuration_error():
    provider = make_provider(max_retries=3)
    error = genai_errors.ClientError(401, {"error": {"message": "invalid api key"}})
    call_count = {"n": 0}

    async def generate_content(**kwargs):
        call_count["n"] += 1
        raise error

    provider._client.aio.models.generate_content = generate_content

    with pytest.raises(LLMConfigurationError):
        await provider.generate_text([LLMMessage(role="user", content="Hi")])
    assert call_count["n"] == 1


@pytest.mark.asyncio
async def test_other_client_error_is_translated_to_invalid_response_error():
    provider = make_provider(max_retries=3)
    error = genai_errors.ClientError(400, {"error": {"message": "malformed request"}})
    call_count = {"n": 0}

    async def generate_content(**kwargs):
        call_count["n"] += 1
        raise error

    provider._client.aio.models.generate_content = generate_content

    with pytest.raises(LLMInvalidResponseError):
        await provider.generate_text([LLMMessage(role="user", content="Hi")])
    assert call_count["n"] == 1


@pytest.mark.asyncio
async def test_server_error_is_translated_and_retried():
    provider = make_provider(max_retries=1)
    error = genai_errors.ServerError(500, {"error": {"message": "server error"}})
    call_count = {"n": 0}

    async def generate_content(**kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise error
        return SimpleNamespace(text="recovered", usage_metadata=None)

    provider._client.aio.models.generate_content = generate_content

    response = await provider.generate_text([LLMMessage(role="user", content="Hi")])

    assert response.content == "recovered"
    assert call_count["n"] == 2
