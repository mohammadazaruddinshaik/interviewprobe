import asyncio
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import TypeVar

from pydantic import BaseModel

from app.llm.exceptions import LLMError, LLMProviderUnavailableError, LLMRateLimitError, LLMTimeoutError
from app.llm.models import LLMMessage, LLMResponse, StructuredLLMResponse

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)
R = TypeVar("R")

# Only these are worth retrying: both are transient by nature (a temporary
# network/provider hiccup or a rate limit that a short wait resolves).
# LLMTimeoutError, LLMConfigurationError, and LLMInvalidResponseError are
# deterministic failures — retrying them immediately would just reproduce
# the same outcome.
_RETRYABLE_ERRORS = (LLMProviderUnavailableError, LLMRateLimitError)


class LLMProvider(ABC):
    """Provider-neutral interface for text and structured LLM generation.

    Application code (and the future Interview Agent) must depend only on
    this interface, never on a provider SDK directly. Subclasses implement
    `generate_text`/`generate_structured` by calling their SDK, translating
    every raw SDK exception into an `LLMError` subclass, and routing the
    call through `_execute` for uniform timeout/retry/logging behavior.
    """

    def __init__(self, *, provider_name: str, model: str, timeout_seconds: float, max_retries: int):
        self.provider_name = provider_name
        self.model = model
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries

    @abstractmethod
    async def generate_text(self, messages: list[LLMMessage]) -> LLMResponse: ...

    @abstractmethod
    async def generate_structured(
        self, messages: list[LLMMessage], output_schema: type[T]
    ) -> StructuredLLMResponse[T]: ...

    async def _execute(self, operation: Callable[[], Awaitable[R]], *, operation_name: str) -> R:
        """Shared timeout + bounded-retry + non-sensitive logging wrapper.

        `operation` must already translate any raw SDK exception into an
        `LLMError` subclass before it can reach this method — this method
        only ever inspects our own normalized exception types, never SDK
        types, so it works identically for every provider.
        """
        attempt = 0
        while True:
            attempt += 1
            started = time.monotonic()
            try:
                result = await asyncio.wait_for(operation(), timeout=self._timeout_seconds)
            except TimeoutError as exc:
                self._log(operation_name, attempt, started, "timeout")
                raise LLMTimeoutError(
                    f"{self.provider_name} request timed out after {self._timeout_seconds}s"
                ) from exc
            except _RETRYABLE_ERRORS as exc:
                will_retry = attempt <= self._max_retries
                self._log(operation_name, attempt, started, "retrying" if will_retry else "failed")
                if not will_retry:
                    raise
                continue
            except LLMError:
                self._log(operation_name, attempt, started, "failed")
                raise
            else:
                self._log(operation_name, attempt, started, "success")
                return result

    def _log(self, operation_name: str, attempt: int, started: float, status: str) -> None:
        # Deliberately: provider, model, operation, attempt, duration,
        # status only — never prompts, answers, or full responses.
        duration_ms = int((time.monotonic() - started) * 1000)
        logger.info(
            "llm_request provider=%s model=%s operation=%s attempt=%d duration_ms=%d status=%s",
            self.provider_name,
            self.model,
            operation_name,
            attempt,
            duration_ms,
            status,
        )
