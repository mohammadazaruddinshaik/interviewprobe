"""Task 40 — AzureTTSProvider: configuration validation, SDK-result
translation into stable VoiceError subclasses, and the async timeout
wrapper. No real Azure call is ever made — the SDK's `SpeechSynthesizer`
is either monkeypatched with a fake, or bypassed entirely by overriding
`provider._synthesize_sync` on the instance (mirrors how
test_llm_openai_provider.py overwrites `provider._client...` directly).
"""

import time
from types import SimpleNamespace

import azure.cognitiveservices.speech as speechsdk
import pytest

from app.voice.exceptions import (
    VoiceConfigurationError,
    VoiceProviderRejectedError,
    VoiceProviderUnavailableError,
    VoiceSynthesisError,
    VoiceTimeoutError,
)
from app.voice.models import TTSRequest
from app.voice.providers.azure_tts import AzureTTSProvider, _translate_result


def make_provider(**overrides) -> AzureTTSProvider:
    kwargs = dict(speech_key="fake-key", speech_region="eastus", voice_name="en-IN-PrabhatNeural", timeout_seconds=5)
    kwargs.update(overrides)
    return AzureTTSProvider(**kwargs)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def test_missing_speech_key_raises_configuration_error():
    with pytest.raises(VoiceConfigurationError):
        make_provider(speech_key=None)


def test_empty_speech_key_raises_configuration_error():
    with pytest.raises(VoiceConfigurationError):
        make_provider(speech_key="")


def test_missing_speech_region_raises_configuration_error():
    with pytest.raises(VoiceConfigurationError):
        make_provider(speech_region=None)


# ---------------------------------------------------------------------------
# _translate_result — pure translation logic, fake SDK-shaped result objects
# ---------------------------------------------------------------------------


def _fake_result(reason, *, audio_data=None, cancellation_reason=None, error_code=None):
    cancellation_details = None
    if cancellation_reason is not None:
        cancellation_details = SimpleNamespace(reason=cancellation_reason, error_code=error_code)
    return SimpleNamespace(reason=reason, audio_data=audio_data, cancellation_details=cancellation_details)


def test_completed_result_returns_audio_bytes():
    result = _fake_result(speechsdk.ResultReason.SynthesizingAudioCompleted, audio_data=b"mp3-bytes")
    assert _translate_result(result) == b"mp3-bytes"


@pytest.mark.parametrize(
    "error_code",
    [speechsdk.CancellationErrorCode.AuthenticationFailure, speechsdk.CancellationErrorCode.Forbidden],
)
def test_auth_cancellation_is_translated_to_configuration_error(error_code):
    result = _fake_result(
        speechsdk.ResultReason.Canceled, cancellation_reason=speechsdk.CancellationReason.Error, error_code=error_code
    )
    with pytest.raises(VoiceConfigurationError):
        _translate_result(result)


def test_service_timeout_cancellation_is_translated_to_timeout_error():
    result = _fake_result(
        speechsdk.ResultReason.Canceled,
        cancellation_reason=speechsdk.CancellationReason.Error,
        error_code=speechsdk.CancellationErrorCode.ServiceTimeout,
    )
    with pytest.raises(VoiceTimeoutError):
        _translate_result(result)


@pytest.mark.parametrize(
    "error_code",
    [
        speechsdk.CancellationErrorCode.ConnectionFailure,
        speechsdk.CancellationErrorCode.ServiceUnavailable,
        speechsdk.CancellationErrorCode.TooManyRequests,
        speechsdk.CancellationErrorCode.ServiceError,
    ],
)
def test_service_unavailable_cancellations_are_translated_to_provider_unavailable_error(error_code):
    result = _fake_result(
        speechsdk.ResultReason.Canceled, cancellation_reason=speechsdk.CancellationReason.Error, error_code=error_code
    )
    with pytest.raises(VoiceProviderUnavailableError):
        _translate_result(result)


def test_bad_request_cancellation_is_translated_to_provider_rejected_error():
    result = _fake_result(
        speechsdk.ResultReason.Canceled,
        cancellation_reason=speechsdk.CancellationReason.Error,
        error_code=speechsdk.CancellationErrorCode.BadRequest,
    )
    with pytest.raises(VoiceProviderRejectedError):
        _translate_result(result)


def test_cancelled_by_user_without_error_reason_is_translated_to_synthesis_error():
    result = _fake_result(speechsdk.ResultReason.Canceled, cancellation_reason=speechsdk.CancellationReason.CancelledByUser)
    with pytest.raises(VoiceSynthesisError):
        _translate_result(result)


def test_unmapped_result_reason_is_translated_to_synthesis_error():
    result = _fake_result(speechsdk.ResultReason.NoMatch)
    with pytest.raises(VoiceSynthesisError):
        _translate_result(result)


# ---------------------------------------------------------------------------
# synthesize() — async timeout wrapper, without touching the real SDK
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_synthesize_returns_normalized_response_on_success():
    provider = make_provider()
    provider._synthesize_sync = lambda text: b"audio-bytes"

    response = await provider.synthesize(TTSRequest(text="Hello"))

    assert response.audio == b"audio-bytes"
    assert response.content_type == "audio/mpeg"


@pytest.mark.asyncio
async def test_synthesize_wraps_slow_call_in_timeout_error():
    provider = make_provider(timeout_seconds=0.05)

    def slow_synth(text):
        time.sleep(0.2)
        return b"too-late"

    provider._synthesize_sync = slow_synth

    with pytest.raises(VoiceTimeoutError):
        await provider.synthesize(TTSRequest(text="Hello"))


@pytest.mark.asyncio
async def test_synthesize_wraps_unexpected_exception_in_provider_unavailable_error():
    provider = make_provider()

    def failing_synth(text):
        raise RuntimeError("boom")

    provider._synthesize_sync = failing_synth

    with pytest.raises(VoiceProviderUnavailableError):
        await provider.synthesize(TTSRequest(text="Hello"))


@pytest.mark.asyncio
async def test_synthesize_propagates_translated_voice_error_without_rewrapping():
    provider = make_provider()

    def rejecting_synth(text):
        raise VoiceProviderRejectedError("rejected")

    provider._synthesize_sync = rejecting_synth

    with pytest.raises(VoiceProviderRejectedError):
        await provider.synthesize(TTSRequest(text="Hello"))


# ---------------------------------------------------------------------------
# End-to-end through a fake SpeechSynthesizer — proves the real code path
# (SpeechConfig + SpeechSynthesizer + speak_text_async) reaches the SDK
# correctly, with no network call.
# ---------------------------------------------------------------------------


class _FakeFuture:
    def __init__(self, result):
        self._result = result

    def get(self):
        return self._result


class _FakeSynthesizer:
    captured_text = None
    captured_voice = None

    def __init__(self, speech_config, audio_config):
        _FakeSynthesizer.captured_voice = speech_config.speech_synthesis_voice_name

    def speak_text_async(self, text):
        _FakeSynthesizer.captured_text = text
        return _FakeFuture(_fake_result(speechsdk.ResultReason.SynthesizingAudioCompleted, audio_data=b"fake-audio"))


@pytest.mark.asyncio
async def test_synthesize_reaches_the_sdk_with_configured_voice_and_text(monkeypatch):
    from app.voice.providers import azure_tts

    monkeypatch.setattr(azure_tts.speechsdk, "SpeechSynthesizer", _FakeSynthesizer)
    provider = make_provider(voice_name="en-IN-PrabhatNeural")

    response = await provider.synthesize(TTSRequest(text="What is a hash map?"))

    assert response.audio == b"fake-audio"
    assert _FakeSynthesizer.captured_text == "What is a hash map?"
    assert _FakeSynthesizer.captured_voice == "en-IN-PrabhatNeural"
