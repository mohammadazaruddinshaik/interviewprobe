import pytest

from app.voice.exceptions import VoiceConfigurationError
from app.voice.factory import get_tts_provider, reset_tts_provider_cache
from app.voice.providers.azure_tts import AzureTTSProvider


@pytest.fixture(autouse=True)
def _reset_cache():
    reset_tts_provider_cache()
    yield
    reset_tts_provider_cache()


def _patch_settings(monkeypatch, **overrides):
    from app.voice import factory

    defaults = dict(
        tts_provider="azure",
        azure_speech_key="fake-key",
        azure_speech_region="eastus",
        azure_speech_voice="en-IN-PrabhatNeural",
        tts_timeout_seconds=15,
    )
    defaults.update(overrides)
    for name, value in defaults.items():
        monkeypatch.setattr(factory.settings, name, value)


def test_azure_provider_name_selects_azure_provider(monkeypatch):
    _patch_settings(monkeypatch, tts_provider="azure")

    provider = get_tts_provider()

    assert isinstance(provider, AzureTTSProvider)
    assert provider.voice_name == "en-IN-PrabhatNeural"


def test_provider_name_is_case_insensitive(monkeypatch):
    _patch_settings(monkeypatch, tts_provider="Azure")

    provider = get_tts_provider()

    assert isinstance(provider, AzureTTSProvider)


def test_unsupported_provider_raises_configuration_error(monkeypatch):
    _patch_settings(monkeypatch, tts_provider="xyz")

    with pytest.raises(VoiceConfigurationError, match="Unsupported TTS provider: xyz"):
        get_tts_provider()


def test_missing_speech_key_raises_configuration_error(monkeypatch):
    _patch_settings(monkeypatch, azure_speech_key=None)

    with pytest.raises(VoiceConfigurationError):
        get_tts_provider()


def test_missing_speech_region_raises_configuration_error(monkeypatch):
    _patch_settings(monkeypatch, azure_speech_region=None)

    with pytest.raises(VoiceConfigurationError):
        get_tts_provider()


def test_provider_instance_is_cached_and_reused(monkeypatch):
    _patch_settings(monkeypatch)

    first = get_tts_provider()
    second = get_tts_provider()

    assert first is second
