from app.core.config import settings
from app.knowledge.embedding.base import EmbeddingProvider
from app.knowledge.embedding.providers.openai import OpenAIEmbeddingProvider
from app.knowledge.exceptions import EmbeddingConfigurationError

_PROVIDERS: dict[str, type[EmbeddingProvider]] = {
    "openai": OpenAIEmbeddingProvider,
}

_provider_instance: EmbeddingProvider | None = None


def _build_embedding_provider() -> EmbeddingProvider:
    provider_name = settings.embedding_provider.lower()
    provider_cls = _PROVIDERS.get(provider_name)
    if provider_cls is None:
        raise EmbeddingConfigurationError(f"Unsupported embedding provider: {settings.embedding_provider}")
    # EMBEDDING_API_KEY falls back to LLM_API_KEY: a single configured
    # OpenAI key can cover both text generation and embeddings, without
    # forcing every deployment to configure the same key twice.
    api_key = settings.embedding_api_key or settings.llm_api_key
    return provider_cls(
        model=settings.embedding_model,
        api_key=api_key,
        timeout_seconds=settings.embedding_timeout_seconds,
    )


def get_embedding_provider() -> EmbeddingProvider:
    """Return the configured embedding provider, constructing it at most
    once. Never called during application startup — only when a caller
    actually needs it — so the app starts fine without EMBEDDING_API_KEY
    configured, exactly like `app.llm.factory.get_llm_provider`."""
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = _build_embedding_provider()
    return _provider_instance


def reset_embedding_provider_cache() -> None:
    """Test-only: clear the cached singleton so tests can exercise
    provider selection/configuration-error behavior repeatedly without
    leaking state between cases."""
    global _provider_instance
    _provider_instance = None
