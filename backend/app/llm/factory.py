from app.core.config import settings
from app.llm.base import LLMProvider
from app.llm.exceptions import LLMConfigurationError
from app.llm.providers.gemini import GeminiProvider
from app.llm.providers.openai import OpenAIProvider

_PROVIDERS: dict[str, type[LLMProvider]] = {
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
}

_provider_instance: LLMProvider | None = None


def _build_provider() -> LLMProvider:
    provider_name = settings.llm_provider.lower()
    provider_cls = _PROVIDERS.get(provider_name)
    if provider_cls is None:
        raise LLMConfigurationError(f"Unsupported LLM provider: {settings.llm_provider}")
    return provider_cls(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        timeout_seconds=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
    )


def get_llm_provider() -> LLMProvider:
    """Return the configured provider, constructing it at most once.

    Never called during application startup or by `/health` — it is only
    invoked when a caller (the future Interview Agent, or a FastAPI route
    via `Depends(get_llm_provider)`) actually needs the provider. This is
    what lets the app start without an LLM API key: configuration is only
    validated here, on first real use, exactly like `settings.redis_url`
    is only used when a Redis operation actually runs. Once built, the
    same instance (and its underlying SDK client) is reused rather than
    reconstructed on every call.
    """
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = _build_provider()
    return _provider_instance


def reset_llm_provider_cache() -> None:
    """Test-only: clear the cached singleton so tests can exercise
    provider selection/configuration-error behavior repeatedly without
    leaking state between cases."""
    global _provider_instance
    _provider_instance = None
