import asyncio
import time

import azure.cognitiveservices.speech as speechsdk

from app.voice.base import TTSProvider
from app.voice.exceptions import (
    VoiceConfigurationError,
    VoiceError,
    VoiceProviderRejectedError,
    VoiceProviderUnavailableError,
    VoiceSynthesisError,
    VoiceTimeoutError,
)
from app.voice.models import TTSRequest, TTSResponse

_OUTPUT_FORMAT = speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
_CONTENT_TYPE = "audio/mpeg"


class AzureTTSProvider(TTSProvider):
    """Azure Cognitive Services Speech (TTS) provider.

    Every call to `synthesize` builds a brand-new `SpeechConfig` +
    `SpeechSynthesizer` — there is deliberately no shared/global
    synthesizer instance, so one request's state can never leak into
    another's.
    """

    def __init__(self, *, speech_key: str | None, speech_region: str | None, voice_name: str, timeout_seconds: float):
        if not speech_key or not speech_region:
            raise VoiceConfigurationError(
                "Azure Speech is not configured: AZURE_SPEECH_KEY and AZURE_SPEECH_REGION are required."
            )
        super().__init__(provider_name="azure", voice_name=voice_name, timeout_seconds=timeout_seconds)
        self._speech_key = speech_key
        self._speech_region = speech_region

    async def synthesize(self, request: TTSRequest) -> TTSResponse:
        started = time.monotonic()
        try:
            audio_bytes = await asyncio.wait_for(
                asyncio.to_thread(self._synthesize_sync, request.text), timeout=self._timeout_seconds
            )
        except TimeoutError as exc:
            self._log(started, "timeout")
            raise VoiceTimeoutError(f"Azure Speech request timed out after {self._timeout_seconds}s") from exc
        except VoiceError:
            self._log(started, "failed")
            raise
        except Exception as exc:
            self._log(started, "failed")
            raise VoiceProviderUnavailableError("Azure Speech provider is temporarily unavailable.") from exc
        else:
            self._log(started, "success")
            return TTSResponse(audio=audio_bytes, content_type=_CONTENT_TYPE)

    def _synthesize_sync(self, text: str) -> bytes:
        """Runs on a worker thread via `asyncio.to_thread` — the Azure SDK's
        `.get()` call is blocking and must never run on the event loop."""
        speech_config = speechsdk.SpeechConfig(subscription=self._speech_key, region=self._speech_region)
        speech_config.speech_synthesis_voice_name = self.voice_name
        speech_config.set_speech_synthesis_output_format(_OUTPUT_FORMAT)

        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
        result = synthesizer.speak_text_async(text).get()
        return _translate_result(result)


def _translate_result(result: "speechsdk.SpeechSynthesisResult") -> bytes:
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return result.audio_data

    if result.reason == speechsdk.ResultReason.Canceled:
        details = result.cancellation_details
        if details.reason == speechsdk.CancellationReason.Error:
            raise _translate_cancellation(details.error_code)
        raise VoiceSynthesisError("Azure Speech synthesis was cancelled.")

    raise VoiceSynthesisError(f"Azure Speech synthesis did not complete (reason={result.reason}).")


def _translate_cancellation(error_code: "speechsdk.CancellationErrorCode") -> Exception:
    if error_code in (speechsdk.CancellationErrorCode.AuthenticationFailure, speechsdk.CancellationErrorCode.Forbidden):
        return VoiceConfigurationError("Azure Speech rejected the configured credentials.")
    if error_code == speechsdk.CancellationErrorCode.ServiceTimeout:
        return VoiceTimeoutError("Azure Speech synthesis timed out.")
    if error_code in (
        speechsdk.CancellationErrorCode.ConnectionFailure,
        speechsdk.CancellationErrorCode.ServiceUnavailable,
        speechsdk.CancellationErrorCode.TooManyRequests,
        speechsdk.CancellationErrorCode.ServiceError,
    ):
        return VoiceProviderUnavailableError("Azure Speech provider is temporarily unavailable.")
    if error_code == speechsdk.CancellationErrorCode.BadRequest:
        return VoiceProviderRejectedError("Azure Speech rejected the request.")
    return VoiceSynthesisError("Azure Speech synthesis failed.")
