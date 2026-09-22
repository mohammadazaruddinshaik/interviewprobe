"""Task 40 — `POST /api/v1/voice/tts` through the full HTTP stack: request
validation, binary audio response, and VoiceError -> stable API error
mapping. `get_tts_service` is overridden with a fake — no real Azure call,
no database. `get_redis_client` is overridden with `FakeAsyncRedis` (Task
46 added a per-client rate-limit check ahead of every request here); see
test_voice_rate_limit_api.py for the rate limiter's own behavior."""

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_tts_service
from app.main import app
from app.redis.client import get_redis_client
from app.voice.exceptions import (
    VoiceConfigurationError,
    VoiceProviderRejectedError,
    VoiceProviderUnavailableError,
    VoiceSynthesisError,
    VoiceTimeoutError,
)
from app.voice.models import TTSResponse
from tests.fakes import FakeAsyncRedis

client = TestClient(app)


class FakeTTSService:
    def __init__(self, *, audio=b"fake-mp3-bytes", content_type="audio/mpeg", error=None):
        self._audio = audio
        self._content_type = content_type
        self._error = error
        self.calls: list[str] = []

    async def synthesize(self, text: str) -> TTSResponse:
        self.calls.append(text)
        if self._error is not None:
            raise self._error
        return TTSResponse(audio=self._audio, content_type=self._content_type)


@pytest.fixture(autouse=True)
def _clear_overrides():
    async def override_get_redis_client():
        return FakeAsyncRedis()

    app.dependency_overrides[get_redis_client] = override_get_redis_client
    yield
    app.dependency_overrides.clear()


def _override(service: FakeTTSService) -> None:
    app.dependency_overrides[get_tts_service] = lambda: service


def test_successful_synthesis_returns_binary_audio():
    fake = FakeTTSService(audio=b"\xff\xfb\x90audio", content_type="audio/mpeg")
    _override(fake)

    response = client.post("/api/v1/voice/tts", json={"text": "Tell me about your experience with Redis."})

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert response.content == b"\xff\xfb\x90audio"
    assert fake.calls == ["Tell me about your experience with Redis."]


def test_default_voice_value_is_accepted():
    fake = FakeTTSService()
    _override(fake)

    response = client.post("/api/v1/voice/tts", json={"text": "Hello", "voice": "default"})

    assert response.status_code == 200


def test_non_default_voice_value_is_rejected():
    fake = FakeTTSService()
    _override(fake)

    response = client.post("/api/v1/voice/tts", json={"text": "Hello", "voice": "en-US-JennyNeural"})

    assert response.status_code == 422
    assert fake.calls == []  # validation failure never reaches the provider


def test_empty_text_is_rejected_before_reaching_the_provider():
    fake = FakeTTSService()
    _override(fake)

    response = client.post("/api/v1/voice/tts", json={"text": ""})

    assert response.status_code == 422
    assert fake.calls == []


def test_overly_long_text_is_rejected_before_reaching_the_provider():
    fake = FakeTTSService()
    _override(fake)

    response = client.post("/api/v1/voice/tts", json={"text": "x" * 2001})

    assert response.status_code == 422
    assert fake.calls == []


@pytest.mark.parametrize(
    "exc,status_code,code",
    [
        (VoiceTimeoutError("slow"), 504, "VOICE_SERVICE_TIMEOUT"),
        (VoiceProviderUnavailableError("down"), 503, "VOICE_SERVICE_UNAVAILABLE"),
        (VoiceConfigurationError("bad config, key=SECRET123"), 500, "VOICE_SERVICE_MISCONFIGURED"),
        (VoiceProviderRejectedError("rejected"), 502, "VOICE_SYNTHESIS_FAILED"),
        (VoiceSynthesisError("failed"), 502, "VOICE_SYNTHESIS_FAILED"),
    ],
)
def test_provider_errors_map_to_stable_api_error_codes(exc, status_code, code):
    fake = FakeTTSService(error=exc)
    _override(fake)

    response = client.post("/api/v1/voice/tts", json={"text": "Hello"})

    assert response.status_code == status_code
    body = response.json()
    assert body["error"]["code"] == code
    # The fixed, generic message is returned — never the raw exception
    # string, which could contain configuration/credential details.
    assert "SECRET123" not in response.text
    assert body["error"]["message"] != str(exc)
