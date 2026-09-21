"""Task 41 — `POST /api/v1/voice/stt/token` through the full HTTP stack:
binary-free JSON response shape, stable error mapping, and the guarantee
that the permanent Deepgram key never appears in a response or is logged.
`get_stt_auth_service` is overridden with a fake — no real Deepgram call."""

import logging

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_stt_auth_service
from app.main import app
from app.voice.exceptions import (
    VoiceConfigurationError,
    VoiceProviderRejectedError,
    VoiceProviderUnavailableError,
    VoiceTimeoutError,
)
from app.voice.models import SttAuthToken

client = TestClient(app)


class FakeSttAuthService:
    def __init__(self, *, access_token="temp-jwt", expires_in=30, error=None):
        self._access_token = access_token
        self._expires_in = expires_in
        self._error = error
        self.call_count = 0

    async def grant_token(self) -> SttAuthToken:
        self.call_count += 1
        if self._error is not None:
            raise self._error
        return SttAuthToken(access_token=self._access_token, expires_in=self._expires_in)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _override(service: FakeSttAuthService) -> None:
    app.dependency_overrides[get_stt_auth_service] = lambda: service


def test_successful_grant_returns_stable_response_shape():
    fake = FakeSttAuthService(access_token="temp-jwt-value", expires_in=30)
    _override(fake)

    response = client.post("/api/v1/voice/stt/token")

    assert response.status_code == 200
    body = response.json()
    assert body == {"data": {"access_token": "temp-jwt-value", "expires_in": 30}}
    assert fake.call_count == 1


def test_response_contains_only_the_expected_fields_no_provider_configuration():
    fake = FakeSttAuthService()
    _override(fake)

    response = client.post("/api/v1/voice/stt/token")

    assert set(response.json()["data"].keys()) == {"access_token", "expires_in"}


@pytest.mark.parametrize(
    "exc,status_code,code",
    [
        (VoiceTimeoutError("slow"), 504, "VOICE_SERVICE_TIMEOUT"),
        (VoiceProviderUnavailableError("down"), 503, "VOICE_SERVICE_UNAVAILABLE"),
        (VoiceConfigurationError("bad config, key=SECRET_PERMANENT_KEY"), 500, "VOICE_SERVICE_MISCONFIGURED"),
        (VoiceProviderRejectedError("rejected"), 502, "VOICE_SYNTHESIS_FAILED"),
    ],
)
def test_provider_errors_map_to_the_existing_stable_api_error_codes(exc, status_code, code):
    fake = FakeSttAuthService(error=exc)
    _override(fake)

    response = client.post("/api/v1/voice/stt/token")

    assert response.status_code == status_code
    body = response.json()
    assert body["error"]["code"] == code
    assert "SECRET_PERMANENT_KEY" not in response.text
    assert body["error"]["message"] != str(exc)


def test_permanent_key_never_appears_in_logs(caplog):
    fake = FakeSttAuthService(access_token="temp-jwt-value", expires_in=30)
    _override(fake)

    with caplog.at_level(logging.DEBUG):
        client.post("/api/v1/voice/stt/token")

    assert "temp-jwt-value" not in caplog.text


def test_token_endpoint_rejects_an_origin_not_in_the_existing_cors_allowlist():
    response = client.options(
        "/api/v1/voice/stt/token",
        headers={
            "Origin": "https://not-an-allowed-origin.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )

    # The existing CORSMiddleware config is unbroadened: a disallowed origin
    # gets no access-control-allow-origin header at all on this new route,
    # exactly as it would on the pre-existing /tts route.
    assert "access-control-allow-origin" not in response.headers


def test_token_endpoint_allows_the_existing_configured_origin():
    from app.core.config import settings

    allowed_origin = settings.cors_allowed_origins[0]
    response = client.options(
        "/api/v1/voice/stt/token",
        headers={"Origin": allowed_origin, "Access-Control-Request-Method": "POST"},
    )

    assert response.headers.get("access-control-allow-origin") == allowed_origin
