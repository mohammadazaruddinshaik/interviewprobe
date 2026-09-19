from typing import TypeVar

from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types
from pydantic import BaseModel

from app.llm.base import LLMProvider
from app.llm.exceptions import (
    LLMConfigurationError,
    LLMInvalidResponseError,
    LLMProviderUnavailableError,
    LLMRateLimitError,
)
from app.llm.models import LLMMessage, LLMResponse, LLMUsage, StructuredLLMResponse

T = TypeVar("T", bound=BaseModel)

_ROLE_MAP = {"user": "user", "assistant": "model"}  # Gemini has no "assistant" role


class GeminiProvider(LLMProvider):
    """LLMProvider backed by the official Google `google-genai` SDK.

    No Gemini SDK type is exposed outside this module — callers only ever
    see `LLMMessage`/`LLMResponse`/`StructuredLLMResponse`/`LLMError`.
    """

    def __init__(self, *, model: str, api_key: str | None, timeout_seconds: float, max_retries: int):
        if not api_key:
            raise LLMConfigurationError("The Gemini provider requires LLM_API_KEY to be configured.")
        super().__init__(
            provider_name="gemini", model=model, timeout_seconds=timeout_seconds, max_retries=max_retries
        )
        self._client = genai.Client(api_key=api_key)

    async def generate_text(self, messages: list[LLMMessage]) -> LLMResponse:
        system_instruction, contents = _split_messages(messages)

        async def _call():
            try:
                return await self._client.aio.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=genai_types.GenerateContentConfig(system_instruction=system_instruction),
                )
            except Exception as exc:
                raise _translate_gemini_error(exc) from exc

        response = await self._execute(_call, operation_name="generate_text")
        text = response.text
        if not text:
            raise LLMInvalidResponseError("Gemini returned no text content.")
        return LLMResponse(content=text, model=self.model, usage=_normalize_usage(response.usage_metadata))

    async def generate_structured(
        self, messages: list[LLMMessage], output_schema: type[T]
    ) -> StructuredLLMResponse[T]:
        system_instruction, contents = _split_messages(messages)

        async def _call():
            try:
                return await self._client.aio.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=genai_types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        response_schema=output_schema,
                    ),
                )
            except Exception as exc:
                raise _translate_gemini_error(exc) from exc

        response = await self._execute(_call, operation_name="generate_structured")
        parsed = response.parsed
        if parsed is None:
            raise LLMInvalidResponseError("Gemini did not return a parsed structured response.")
        # The SDK returns an instance of `output_schema` when given a
        # Pydantic model class directly; validate defensively in case a
        # dict slips through on some SDK versions.
        if not isinstance(parsed, output_schema):
            parsed = output_schema.model_validate(parsed)
        return StructuredLLMResponse(
            data=parsed, model=self.model, usage=_normalize_usage(response.usage_metadata)
        )


def _split_messages(messages: list[LLMMessage]) -> tuple[str | None, list[dict]]:
    """Gemini has no "system" role message — system prompts are instead
    passed as a separate `system_instruction` config value, and there is
    no "assistant" role (it's "model")."""
    system_parts = [m.content for m in messages if m.role == "system"]
    system_instruction = "\n\n".join(system_parts) if system_parts else None
    contents = [
        {"role": _ROLE_MAP[m.role], "parts": [{"text": m.content}]}
        for m in messages
        if m.role != "system"
    ]
    return system_instruction, contents


def _normalize_usage(usage_metadata) -> LLMUsage | None:
    if usage_metadata is None:
        return None
    return LLMUsage(
        prompt_tokens=usage_metadata.prompt_token_count,
        completion_tokens=usage_metadata.candidates_token_count,
        total_tokens=usage_metadata.total_token_count,
    )


def _translate_gemini_error(exc: Exception) -> Exception:
    if isinstance(exc, genai_errors.ClientError):
        code = getattr(exc, "code", None)
        if code == 429:
            return LLMRateLimitError(f"Gemini rate limit exceeded: {exc}")
        if code in (401, 403):
            return LLMConfigurationError(f"Gemini authentication/configuration error: {exc}")
        return LLMInvalidResponseError(f"Gemini rejected the request: {exc}")
    if isinstance(exc, genai_errors.ServerError):
        return LLMProviderUnavailableError(f"Gemini provider unavailable: {exc}")
    if isinstance(exc, genai_errors.APIError):
        return LLMProviderUnavailableError(f"Gemini API error: {exc}")
    return LLMProviderUnavailableError(f"Unexpected Gemini error: {exc}")
