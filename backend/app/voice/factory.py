from app.core.config import settings
from app.voice.base import SttAuthProvider, TTSProvider
from app.voice.exceptions import VoiceConfigurationError
from app.voice.providers.azure_tts import AzureTTSProvider
from app.voice.providers.deepgram_auth import DeepgramSttAuthProvider

_PROVIDERS: dict[str, type[TTSProvider]] = {
    "azure": AzureTTSProvider,
}

_STT_AUTH_PROVIDERS: dict[str, type[SttAuthProvider]] = {
    "deepgram": DeepgramSttAuthProvider,
}

_provider_instance: TTSProvider | None = None
_stt_auth_provider_instance: SttAuthProvider | None = None


def _build_provider() -> TTSProvider:
    provider_name = settings.tts_provider.lower()
    provider_cls = _PROVIDERS.get(provider_name)
    if provider_cls is None:
        raise VoiceConfigurationError(f"Unsupported TTS provider: {settings.tts_provider}")
    return provider_cls(
        speech_key=settings.azure_speech_key,
        speech_region=settings.azure_speech_region,
        voice_name=settings.azure_speech_voice,
        timeout_seconds=settings.tts_timeout_seconds,
    )


def get_tts_provider() -> TTSProvider:
    """Return the configured provider, constructing it at most once.

    Never called during application startup or by `/health` — it is only
    invoked when a caller actually needs the provider (a FastAPI route via
    `Depends(get_tts_provider)`). This is what lets the app start without
    Azure Speech credentials: configuration is only validated here, on
    first real use. Once built, the same instance is reused rather than
    reconstructed on every call.
    """
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = _build_provider()
    return _provider_instance


def reset_tts_provider_cache() -> None:
    """Test-only: clear the cached singleton so tests can exercise
    provider selection/configuration-error behavior repeatedly without
    leaking state between cases."""
    global _provider_instance
    _provider_instance = None


def _build_stt_auth_provider() -> SttAuthProvider:
    provider_name = settings.stt_auth_provider.lower()
    provider_cls = _STT_AUTH_PROVIDERS.get(provider_name)
    if provider_cls is None:
        raise VoiceConfigurationError(f"Unsupported STT auth provider: {settings.stt_auth_provider}")
    return provider_cls(api_key=settings.deepgram_api_key, timeout_seconds=settings.stt_auth_timeout_seconds)


def get_stt_auth_provider() -> SttAuthProvider:
    """Return the configured STT auth provider, constructing it at most
    once. Mirrors `get_tts_provider` exactly — never called at startup or
    by `/health`, only on first real use, so the app starts fine without
    DEEPGRAM_API_KEY set."""
    global _stt_auth_provider_instance
    if _stt_auth_provider_instance is None:
        _stt_auth_provider_instance = _build_stt_auth_provider()
    return _stt_auth_provider_instance


def reset_stt_auth_provider_cache() -> None:
    """Test-only: mirrors `reset_tts_provider_cache`."""
    global _stt_auth_provider_instance
    _stt_auth_provider_instance = None
