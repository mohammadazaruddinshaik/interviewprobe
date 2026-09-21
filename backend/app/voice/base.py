import logging
import time
from abc import ABC, abstractmethod

from app.voice.models import SttAuthToken, TTSRequest, TTSResponse

logger = logging.getLogger(__name__)


class TTSProvider(ABC):
    """Provider-neutral interface for text-to-speech synthesis.

    Application code must depend only on this interface, never on a
    provider SDK directly. Subclasses implement `synthesize` by calling
    their SDK, translating every raw SDK exception into a `VoiceError`
    subclass, and reporting non-sensitive timing via `_log`.
    """

    def __init__(self, *, provider_name: str, voice_name: str, timeout_seconds: float):
        self.provider_name = provider_name
        self.voice_name = voice_name
        self._timeout_seconds = timeout_seconds

    @abstractmethod
    async def synthesize(self, request: TTSRequest) -> TTSResponse: ...

    def _log(self, started: float, status: str) -> None:
        # Deliberately: provider, voice, duration, status only — never the
        # synthesized text itself.
        duration_ms = int((time.monotonic() - started) * 1000)
        logger.info(
            "tts_request provider=%s voice=%s duration_ms=%d status=%s",
            self.provider_name,
            self.voice_name,
            duration_ms,
            status,
        )


class SttAuthProvider(ABC):
    """Provider-neutral interface for issuing a short-lived, browser-safe
    STT credential. The browser streams audio directly to the STT vendor
    using this credential — the permanent provider key never leaves this
    process, and this class's only job is exchanging it for something
    temporary that's safe to hand to the client."""

    def __init__(self, *, provider_name: str, timeout_seconds: float):
        self.provider_name = provider_name
        self._timeout_seconds = timeout_seconds

    @abstractmethod
    async def grant_token(self) -> SttAuthToken: ...

    def _log(self, started: float, status: str) -> None:
        # Deliberately: provider, duration, status only — never the token.
        duration_ms = int((time.monotonic() - started) * 1000)
        logger.info(
            "stt_auth_request provider=%s duration_ms=%d status=%s",
            self.provider_name,
            duration_ms,
            status,
        )
