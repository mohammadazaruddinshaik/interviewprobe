import asyncio

import openai
from openai import AsyncOpenAI

from app.knowledge.embedding.base import EmbeddingProvider
from app.knowledge.exceptions import (
    EmbeddingConfigurationError,
    EmbeddingProviderUnavailableError,
    EmbeddingTimeoutError,
)

# The vector dimension is a fixed property of each OpenAI embedding model,
# not something to guess or hardcode elsewhere — `KnowledgeStore` reads it
# via `EmbeddingProvider.dimension`, never a literal.
_MODEL_DIMENSIONS: dict[str, int] = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """EmbeddingProvider backed by the official OpenAI Python SDK.

    No OpenAI SDK type is exposed outside this module — callers only ever
    see `list[float]` vectors and `EmbeddingError` subclasses.
    """

    def __init__(self, *, model: str, api_key: str | None, timeout_seconds: float):
        if not api_key:
            raise EmbeddingConfigurationError(
                "The OpenAI embedding provider requires EMBEDDING_API_KEY (or LLM_API_KEY) to be configured."
            )
        dimension = _MODEL_DIMENSIONS.get(model)
        if dimension is None:
            raise EmbeddingConfigurationError(
                f"Unknown OpenAI embedding model '{model}'; supported models: {sorted(_MODEL_DIMENSIONS)}."
            )
        super().__init__(provider_name="openai", model=model, dimension=dimension)
        self._timeout_seconds = timeout_seconds
        # max_retries=0, no client-level timeout: mirrors
        # app.llm.providers.OpenAIProvider exactly — our own asyncio.wait_for
        # below is the primary, bounded timeout mechanism (not the SDK's own
        # ~600s default), and the async client is genuinely cancellable, so
        # wait_for's cancellation actually aborts the in-flight httpx
        # request rather than leaving an orphaned thread/connection behind.
        self._client = AsyncOpenAI(api_key=api_key, max_retries=0)

    async def embed(self, text: str) -> list[float]:
        return (await self.embed_many([text]))[0]

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            response = await asyncio.wait_for(
                self._client.embeddings.create(model=self.model, input=texts),
                timeout=self._timeout_seconds,
            )
        except TimeoutError as exc:
            raise EmbeddingTimeoutError(
                f"OpenAI embedding request timed out after {self._timeout_seconds}s"
            ) from exc
        except Exception as exc:
            raise _translate_openai_embedding_error(exc) from exc
        return [item.embedding for item in response.data]


def _translate_openai_embedding_error(exc: Exception) -> Exception:
    if isinstance(exc, openai.APITimeoutError):
        # Defensive: our own asyncio.wait_for above is the primary timeout
        # mechanism, but this covers the case where the underlying httpx
        # transport times out on its own first (mirrors
        # app.llm.providers.openai._translate_openai_error).
        return EmbeddingTimeoutError(f"OpenAI embedding request timed out: {exc.__class__.__name__}")
    if isinstance(exc, openai.AuthenticationError | openai.PermissionDeniedError):
        return EmbeddingConfigurationError(f"OpenAI embedding authentication/configuration error: {exc.__class__.__name__}")
    if isinstance(exc, openai.BadRequestError | openai.UnprocessableEntityError | openai.NotFoundError):
        return EmbeddingConfigurationError(f"OpenAI embedding request rejected: {exc.__class__.__name__}")
    return EmbeddingProviderUnavailableError(f"OpenAI embedding provider unavailable: {exc.__class__.__name__}")
