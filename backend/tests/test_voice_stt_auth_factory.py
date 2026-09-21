import pytest

from app.voice.exceptions import VoiceConfigurationError
from app.voice.factory import get_stt_auth_provider, reset_stt_auth_provider_cache
from app.voice.providers.deepgram_auth import DeepgramSttAuthProvider


@pytest.fixture(autouse=True)
def _reset_cache():
    reset_stt_auth_provider_cache()
    yield
    reset_stt_auth_provider_cache()


def _patch_settings(monkeypatch, **overrides):
    from app.voice import factory

    defaults = dict(
        stt_auth_provider="deepgram",
        deepgram_api_key="fake-key",
        stt_auth_timeout_seconds=10,
    )
    defaults.update(overrides)
    for name, value in defaults.items():
        monkeypatch.setattr(factory.settings, name, value)


def test_deepgram_provider_name_selects_deepgram_provider(monkeypatch):
    _patch_settings(monkeypatch, stt_auth_provider="deepgram")

    provider = get_stt_auth_provider()

    assert isinstance(provider, DeepgramSttAuthProvider)


def test_provider_name_is_case_insensitive(monkeypatch):
    _patch_settings(monkeypatch, stt_auth_provider="Deepgram")

    provider = get_stt_auth_provider()

    assert isinstance(provider, DeepgramSttAuthProvider)


def test_unsupported_provider_raises_configuration_error(monkeypatch):
    _patch_settings(monkeypatch, stt_auth_provider="xyz")

    with pytest.raises(VoiceConfigurationError, match="Unsupported STT auth provider: xyz"):
        get_stt_auth_provider()


def test_missing_api_key_raises_configuration_error(monkeypatch):
    _patch_settings(monkeypatch, deepgram_api_key=None)

    with pytest.raises(VoiceConfigurationError):
        get_stt_auth_provider()


def test_provider_instance_is_cached_and_reused(monkeypatch):
    _patch_settings(monkeypatch)

    first = get_stt_auth_provider()
    second = get_stt_auth_provider()

    assert first is second
