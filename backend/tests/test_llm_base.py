import asyncio

import pytest

from app.llm.base import LLMProvider
from app.llm.exceptions import (
    LLMConfigurationError,
    LLMInvalidResponseError,
    LLMProviderUnavailableError,
    LLMRateLimitError,
    LLMTimeoutError,
)


class _MinimalProvider(LLMProvider):
    """Concrete LLMProvider used only to exercise `_execute` directly and
    to prove a subclass can satisfy the abstract interface."""

    async def generate_text(self, messages):
        raise NotImplementedError

    async def generate_structured(self, messages, output_schema):
        raise NotImplementedError


def make_provider(timeout_seconds: float = 1, max_retries: int = 2) -> _MinimalProvider:
    return _MinimalProvider(
        provider_name="fake", model="fake-model", timeout_seconds=timeout_seconds, max_retries=max_retries
    )


def test_concrete_subclass_satisfies_the_abstract_interface():
    provider = make_provider()

    assert isinstance(provider, LLMProvider)
    assert provider.provider_name == "fake"
    assert provider.model == "fake-model"


@pytest.mark.asyncio
async def test_execute_returns_result_on_success():
    provider = make_provider()

    async def op():
        return "ok"

    assert await provider._execute(op, operation_name="test") == "ok"


@pytest.mark.asyncio
async def test_execute_retries_provider_unavailable_error_then_succeeds():
    provider = make_provider(max_retries=2)
    attempts = {"count": 0}

    async def op():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise LLMProviderUnavailableError("transient")
        return "ok"

    result = await provider._execute(op, operation_name="test")

    assert result == "ok"
    assert attempts["count"] == 3


@pytest.mark.asyncio
async def test_execute_retries_rate_limit_error_then_succeeds():
    provider = make_provider(max_retries=1)
    attempts = {"count": 0}

    async def op():
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise LLMRateLimitError("rate limited")
        return "ok"

    result = await provider._execute(op, operation_name="test")

    assert result == "ok"
    assert attempts["count"] == 2


@pytest.mark.asyncio
async def test_execute_raises_after_exhausting_retries():
    provider = make_provider(max_retries=1)
    attempts = {"count": 0}

    async def op():
        attempts["count"] += 1
        raise LLMProviderUnavailableError("always fails")

    with pytest.raises(LLMProviderUnavailableError):
        await provider._execute(op, operation_name="test")

    assert attempts["count"] == 2  # 1 initial attempt + 1 retry


@pytest.mark.asyncio
async def test_execute_does_not_retry_configuration_error():
    provider = make_provider(max_retries=3)
    attempts = {"count": 0}

    async def op():
        attempts["count"] += 1
        raise LLMConfigurationError("bad config")

    with pytest.raises(LLMConfigurationError):
        await provider._execute(op, operation_name="test")

    assert attempts["count"] == 1


@pytest.mark.asyncio
async def test_execute_does_not_retry_invalid_response_error():
    provider = make_provider(max_retries=3)
    attempts = {"count": 0}

    async def op():
        attempts["count"] += 1
        raise LLMInvalidResponseError("malformed output")

    with pytest.raises(LLMInvalidResponseError):
        await provider._execute(op, operation_name="test")

    assert attempts["count"] == 1


@pytest.mark.asyncio
async def test_execute_translates_a_slow_operation_into_llm_timeout_error():
    provider = make_provider(timeout_seconds=0.05, max_retries=3)
    attempts = {"count": 0}

    async def op():
        attempts["count"] += 1
        await asyncio.sleep(1)
        return "too slow"

    with pytest.raises(LLMTimeoutError):
        await provider._execute(op, operation_name="test")

    assert attempts["count"] == 1  # timeouts are not retried
