import time

import httpx

from app.voice.base import SttAuthProvider
from app.voice.exceptions import (
    VoiceConfigurationError,
    VoiceProviderRejectedError,
    VoiceProviderUnavailableError,
    VoiceTimeoutError,
)
from app.voice.models import SttAuthToken

# Deepgram's token-based-auth grant endpoint: exchanges a permanent API key
# for a short-lived JWT the browser can use to open its own streaming
# connection directly. See
# https://developers.deepgram.com/reference/auth/tokens/grant — the
# permanent key is sent only in this server-to-server call, never to the
# browser.
_GRANT_URL = "https://api.deepgram.com/v1/auth/grant"


class DeepgramSttAuthProvider(SttAuthProvider):
    """Issues short-lived Deepgram access tokens for browser-side streaming
    STT. Holds no persistent connection or mutable per-request state — each
    `grant_token()` call is an independent HTTP request."""

    def __init__(self, *, api_key: str | None, timeout_seconds: float):
        if not api_key:
            raise VoiceConfigurationError("Deepgram STT is not configured: DEEPGRAM_API_KEY is required.")
        super().__init__(provider_name="deepgram", timeout_seconds=timeout_seconds)
        self._api_key = api_key

    async def grant_token(self) -> SttAuthToken:
        started = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(
                    _GRANT_URL,
                    headers={"Authorization": f"Token {self._api_key}"},
                )
        except httpx.TimeoutException as exc:
            self._log(started, "timeout")
            raise VoiceTimeoutError(f"Deepgram token request timed out after {self._timeout_seconds}s") from exc
        except httpx.HTTPError as exc:
            self._log(started, "failed")
            raise VoiceProviderUnavailableError("Deepgram authentication service is temporarily unavailable.") from exc

        if response.status_code in (401, 403):
            self._log(started, "failed")
            raise VoiceConfigurationError("Deepgram rejected the configured API key.")
        if response.status_code >= 500:
            self._log(started, "failed")
            raise VoiceProviderUnavailableError("Deepgram authentication service is temporarily unavailable.")
        if response.status_code >= 400:
            self._log(started, "failed")
            raise VoiceProviderRejectedError("Deepgram rejected the token request.")

        try:
            body = response.json()
            token = SttAuthToken(access_token=body["access_token"], expires_in=body["expires_in"])
        except (ValueError, KeyError) as exc:
            self._log(started, "failed")
            raise VoiceProviderUnavailableError("Deepgram returned an unexpected authentication response.") from exc

        self._log(started, "success")
        return token
