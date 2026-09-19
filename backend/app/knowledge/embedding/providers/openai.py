import openai
from openai import AsyncOpenAI

from app.knowledge.embedding.base import EmbeddingProvider
from app.knowledge.exceptions import EmbeddingConfigurationError, EmbeddingProviderUnavailableError

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

    def __init__(self, *, model: str, api_key: str | None):
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
        self._client = AsyncOpenAI(api_key=api_key, max_retries=0)

    async def embed(self, text: str) -> list[float]:
        return (await self.embed_many([text]))[0]

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            response = await self._client.embeddings.create(model=self.model, input=texts)
        except Exception as exc:
            raise _translate_openai_embedding_error(exc) from exc
        return [item.embedding for item in response.data]


def _translate_openai_embedding_error(exc: Exception) -> Exception:
    if isinstance(exc, openai.AuthenticationError | openai.PermissionDeniedError):
        return EmbeddingConfigurationError(f"OpenAI embedding authentication/configuration error: {exc.__class__.__name__}")
    if isinstance(exc, openai.BadRequestError | openai.UnprocessableEntityError | openai.NotFoundError):
        return EmbeddingConfigurationError(f"OpenAI embedding request rejected: {exc.__class__.__name__}")
    return EmbeddingProviderUnavailableError(f"OpenAI embedding provider unavailable: {exc.__class__.__name__}")
