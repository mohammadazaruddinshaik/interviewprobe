from typing import TypeVar

import openai
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.llm.base import LLMProvider
from app.llm.exceptions import (
    LLMConfigurationError,
    LLMInvalidResponseError,
    LLMProviderUnavailableError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from app.llm.models import LLMMessage, LLMResponse, LLMUsage, StructuredLLMResponse

T = TypeVar("T", bound=BaseModel)


class OpenAIProvider(LLMProvider):
    """LLMProvider backed by the official OpenAI Python SDK.

    No OpenAI SDK type is exposed outside this module — callers only ever
    see `LLMMessage`/`LLMResponse`/`StructuredLLMResponse`/`LLMError`.
    """

    def __init__(self, *, model: str, api_key: str | None, timeout_seconds: float, max_retries: int):
        if not api_key:
            raise LLMConfigurationError("The OpenAI provider requires LLM_API_KEY to be configured.")
        super().__init__(
            provider_name="openai", model=model, timeout_seconds=timeout_seconds, max_retries=max_retries
        )
        # max_retries=0: LLMProvider._execute owns retry policy uniformly
        # across providers, so the SDK's own retry layer is disabled to
        # avoid silently double-retrying the same transient failure.
        self._client = AsyncOpenAI(api_key=api_key, max_retries=0)

    async def generate_text(self, messages: list[LLMMessage]) -> LLMResponse:
        async def _call():
            try:
                return await self._client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": m.role, "content": m.content} for m in messages],
                )
            except Exception as exc:
                raise _translate_openai_error(exc) from exc

        completion = await self._execute(_call, operation_name="generate_text")
        content = completion.choices[0].message.content
        if content is None:
            raise LLMInvalidResponseError("OpenAI returned no text content.")
        return LLMResponse(
            content=content,
            model=completion.model,
            usage=_normalize_usage(completion.usage),
        )

    async def generate_structured(
        self, messages: list[LLMMessage], output_schema: type[T]
    ) -> StructuredLLMResponse[T]:
        async def _call():
            try:
                return await self._client.chat.completions.parse(
                    model=self.model,
                    messages=[{"role": m.role, "content": m.content} for m in messages],
                    response_format=output_schema,
                )
            except Exception as exc:
                raise _translate_openai_error(exc) from exc

        completion = await self._execute(_call, operation_name="generate_structured")
        message = completion.choices[0].message
        if message.parsed is None:
            reason = f": {message.refusal}" if message.refusal else "."
            raise LLMInvalidResponseError(f"OpenAI did not return a parsed structured response{reason}")
        return StructuredLLMResponse(
            data=message.parsed,
            model=completion.model,
            usage=_normalize_usage(completion.usage),
        )


def _normalize_usage(usage) -> LLMUsage | None:
    if usage is None:
        return None
    return LLMUsage(
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        total_tokens=usage.total_tokens,
    )


def _translate_openai_error(exc: Exception) -> Exception:
    if isinstance(exc, openai.APITimeoutError):
        # Our own asyncio.wait_for in LLMProvider._execute is the primary
        # timeout mechanism (no client-level timeout is configured on the
        # SDK), but translate this defensively in case the underlying
        # httpx transport times out on its own first.
        return LLMTimeoutError(f"OpenAI request timed out: {exc}")
    if isinstance(exc, openai.RateLimitError):
        return LLMRateLimitError(f"OpenAI rate limit exceeded: {exc}")
    if isinstance(exc, openai.AuthenticationError | openai.PermissionDeniedError):
        return LLMConfigurationError(f"OpenAI authentication/configuration error: {exc}")
    if isinstance(exc, openai.BadRequestError | openai.UnprocessableEntityError | openai.NotFoundError):
        return LLMInvalidResponseError(f"OpenAI rejected the request: {exc}")
    if isinstance(exc, openai.APIConnectionError | openai.InternalServerError | openai.APIStatusError):
        return LLMProviderUnavailableError(f"OpenAI provider unavailable: {exc}")
    return LLMProviderUnavailableError(f"Unexpected OpenAI error: {exc}")
