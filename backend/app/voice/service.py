from app.voice.base import SttAuthProvider, TTSProvider
from app.voice.models import SttAuthToken, TTSRequest, TTSResponse


class TTSService:
    """Thin application-facing wrapper around a `TTSProvider`. Routes depend
    on this, never on the provider or the factory directly, so the provider
    can be swapped/mocked without touching route code."""

    def __init__(self, provider: TTSProvider):
        self._provider = provider

    async def synthesize(self, text: str) -> TTSResponse:
        return await self._provider.synthesize(TTSRequest(text=text))


class SttAuthService:
    """Thin application-facing wrapper around an `SttAuthProvider`, mirroring
    `TTSService`."""

    def __init__(self, provider: SttAuthProvider):
        self._provider = provider

    async def grant_token(self) -> SttAuthToken:
        return await self._provider.grant_token()
