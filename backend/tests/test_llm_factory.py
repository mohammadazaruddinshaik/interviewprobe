import pytest

from app.llm.exceptions import LLMConfigurationError
from app.llm.factory import get_llm_provider, reset_llm_provider_cache
from app.llm.providers.gemini import GeminiProvider
from app.llm.providers.openai import OpenAIProvider


@pytest.fixture(autouse=True)
def _reset_cache():
    reset_llm_provider_cache()
    yield
    reset_llm_provider_cache()


def _patch_settings(monkeypatch, **overrides):
    from app.llm import factory

    defaults = dict(
        llm_provider="openai",
        llm_model="gpt-4o-mini",
        llm_api_key="fake-key",
        llm_timeout_seconds=30,
        llm_max_retries=2,
    )
    defaults.update(overrides)
    for name, value in defaults.items():
        monkeypatch.setattr(factory.settings, name, value)


def test_openai_provider_name_selects_openai_provider(monkeypatch):
    _patch_settings(monkeypatch, llm_provider="openai")

    provider = get_llm_provider()

    assert isinstance(provider, OpenAIProvider)
    assert provider.model == "gpt-4o-mini"


def test_gemini_provider_name_selects_gemini_provider(monkeypatch):
    _patch_settings(monkeypatch, llm_provider="gemini", llm_model="gemini-2.0-flash")

    provider = get_llm_provider()

    assert isinstance(provider, GeminiProvider)
    assert provider.model == "gemini-2.0-flash"


def test_provider_name_is_case_insensitive(monkeypatch):
    _patch_settings(monkeypatch, llm_provider="OpenAI")

    provider = get_llm_provider()

    assert isinstance(provider, OpenAIProvider)


def test_unsupported_provider_raises_configuration_error(monkeypatch):
    _patch_settings(monkeypatch, llm_provider="xyz")

    with pytest.raises(LLMConfigurationError, match="Unsupported LLM provider: xyz"):
        get_llm_provider()


def test_missing_api_key_raises_configuration_error(monkeypatch):
    _patch_settings(monkeypatch, llm_provider="openai", llm_api_key=None)

    with pytest.raises(LLMConfigurationError):
        get_llm_provider()


def test_provider_instance_is_cached_and_reused(monkeypatch):
    _patch_settings(monkeypatch, llm_provider="openai")

    first = get_llm_provider()
    second = get_llm_provider()

    assert first is second
