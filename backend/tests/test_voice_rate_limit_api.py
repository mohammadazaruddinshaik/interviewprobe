"""Task 46 — per-client (IP-based) rate limiting on `POST /api/v1/voice/tts`
(30/60/client) and `POST /api/v1/voice/stt/token` (10/60/client), the two
voice endpoints that trigger paid third-party usage (Azure TTS synthesis,
Deepgram token issuance) with no interview session to scope a limit by and
no authentication to identify a caller by.

Reuses the exact fake-service patterns from test_voice_api.py /
test_voice_stt_token_api.py (no real Azure/Deepgram call, no database) and
adds `get_redis_client` overrides + `TestClient(app, client=(...))` to
control caller identity, the same way test_interview_rate_limit_api.py
does for the interview-creation/start endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_stt_auth_service, get_tts_service
from app.main import app
from app.redis.client import get_redis_client
from app.voice.models import SttAuthToken, TTSResponse
from tests.fakes import FailingAsyncRedis, FakeAsyncRedis


class FakeTTSService:
    def __init__(self, *, audio=b"fake-mp3-bytes", content_type="audio/mpeg"):
        self._audio = audio
        self._content_type = content_type
        self.calls: list[str] = []

    async def synthesize(self, text: str) -> TTSResponse:
        self.calls.append(text)
        return TTSResponse(audio=self._audio, content_type=self._content_type)


class FakeSttAuthService:
    def __init__(self, *, access_token="temp-jwt", expires_in=30):
        self._access_token = access_token
        self._expires_in = expires_in
        self.call_count = 0

    async def grant_token(self) -> SttAuthToken:
        self.call_count += 1
        return SttAuthToken(access_token=self._access_token, expires_in=self._expires_in)


@pytest.fixture()
def fake_redis() -> FakeAsyncRedis:
    return FakeAsyncRedis()


@pytest.fixture()
def fake_tts() -> FakeTTSService:
    return FakeTTSService()


@pytest.fixture()
def fake_stt_auth() -> FakeSttAuthService:
    return FakeSttAuthService()


@pytest.fixture()
def overrides(fake_redis: FakeAsyncRedis, fake_tts: FakeTTSService, fake_stt_auth: FakeSttAuthService):
    async def override_get_redis_client():
        return fake_redis

    app.dependency_overrides[get_redis_client] = override_get_redis_client
    app.dependency_overrides[get_tts_service] = lambda: fake_tts
    app.dependency_overrides[get_stt_auth_service] = lambda: fake_stt_auth
    yield
    app.dependency_overrides.clear()


@pytest.fixture()
def client(overrides):
    return TestClient(app, client=("10.1.0.1", 1))


@pytest.fixture()
def other_client(overrides):
    """Same app/Redis/fakes, a different reported caller IP."""
    return TestClient(app, client=("10.1.0.2", 1))


# ---------------------------------------------------------------------------
# POST /api/v1/voice/tts — 30/60/client
# ---------------------------------------------------------------------------


def test_first_thirty_tts_requests_reach_the_tts_service(client: TestClient, fake_tts: FakeTTSService):
    for i in range(30):
        response = client.post("/api/v1/voice/tts", json={"text": f"Question {i}"})
        assert response.status_code == 200
    assert len(fake_tts.calls) == 30


def test_thirty_first_tts_request_is_rate_limited(client: TestClient):
    for i in range(30):
        client.post("/api/v1/voice/tts", json={"text": f"Question {i}"})

    response = client.post("/api/v1/voice/tts", json={"text": "one too many"})

    assert response.status_code == 429
    body = response.json()
    assert body["error"]["code"] == "RATE_LIMITED"
    assert "Retry-After" in response.headers
    assert int(response.headers["Retry-After"]) > 0


def test_rejected_tts_request_never_reaches_the_provider(client: TestClient, fake_tts: FakeTTSService):
    for i in range(30):
        client.post("/api/v1/voice/tts", json={"text": f"Question {i}"})
    calls_before_rejection = len(fake_tts.calls)

    response = client.post("/api/v1/voice/tts", json={"text": "one too many"})

    assert response.status_code == 429
    assert len(fake_tts.calls) == calls_before_rejection == 30


def test_tts_text_length_validation_still_applies(client: TestClient, fake_tts: FakeTTSService):
    # Existing Task 40 behavior (MAX_TTS_TEXT_LENGTH=2000) must be untouched
    # by the new rate limiter — still a 422, provider still never reached.
    response = client.post("/api/v1/voice/tts", json={"text": "x" * 2001})

    assert response.status_code == 422
    assert fake_tts.calls == []


def test_tts_buckets_are_isolated_per_client(client: TestClient, other_client: TestClient):
    for i in range(30):
        response = client.post("/api/v1/voice/tts", json={"text": f"Question {i}"})
        assert response.status_code == 200
    exhausted = client.post("/api/v1/voice/tts", json={"text": "one too many"})
    assert exhausted.status_code == 429

    response = other_client.post("/api/v1/voice/tts", json={"text": "hello"})
    assert response.status_code == 200


def test_tts_redis_outage_returns_503_and_never_reaches_the_provider(overrides, fake_tts: FakeTTSService):
    app.dependency_overrides[get_redis_client] = lambda: FailingAsyncRedis()
    test_client = TestClient(app, client=("10.1.0.3", 1))

    response = test_client.post("/api/v1/voice/tts", json={"text": "hello"})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "REDIS_UNAVAILABLE"
    assert fake_tts.calls == []


# ---------------------------------------------------------------------------
# POST /api/v1/voice/stt/token — 10/60/client
# ---------------------------------------------------------------------------


def test_first_ten_stt_token_requests_reach_the_token_service(client: TestClient, fake_stt_auth: FakeSttAuthService):
    for _ in range(10):
        response = client.post("/api/v1/voice/stt/token")
        assert response.status_code == 200
    assert fake_stt_auth.call_count == 10


def test_eleventh_stt_token_request_is_rate_limited(client: TestClient):
    for _ in range(10):
        client.post("/api/v1/voice/stt/token")

    response = client.post("/api/v1/voice/stt/token")

    assert response.status_code == 429
    body = response.json()
    assert body["error"]["code"] == "RATE_LIMITED"
    assert "Retry-After" in response.headers
    assert int(response.headers["Retry-After"]) > 0


def test_rejected_stt_token_request_never_requests_a_deepgram_token(client: TestClient, fake_stt_auth: FakeSttAuthService):
    for _ in range(10):
        client.post("/api/v1/voice/stt/token")
    calls_before_rejection = fake_stt_auth.call_count

    response = client.post("/api/v1/voice/stt/token")

    assert response.status_code == 429
    assert fake_stt_auth.call_count == calls_before_rejection == 10


def test_stt_token_buckets_are_isolated_per_client(client: TestClient, other_client: TestClient):
    for _ in range(10):
        response = client.post("/api/v1/voice/stt/token")
        assert response.status_code == 200
    exhausted = client.post("/api/v1/voice/stt/token")
    assert exhausted.status_code == 429

    response = other_client.post("/api/v1/voice/stt/token")
    assert response.status_code == 200


def test_stt_token_redis_outage_returns_503_and_never_requests_a_token(overrides, fake_stt_auth: FakeSttAuthService):
    app.dependency_overrides[get_redis_client] = lambda: FailingAsyncRedis()
    test_client = TestClient(app, client=("10.1.0.4", 1))

    response = test_client.post("/api/v1/voice/stt/token")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "REDIS_UNAVAILABLE"
    assert fake_stt_auth.call_count == 0


# ---------------------------------------------------------------------------
# Cross-endpoint isolation — TTS and STT-token never share a bucket
# ---------------------------------------------------------------------------


def test_exhausting_tts_does_not_exhaust_stt_token(client: TestClient):
    for i in range(30):
        client.post("/api/v1/voice/tts", json={"text": f"Question {i}"})
    assert client.post("/api/v1/voice/tts", json={"text": "one too many"}).status_code == 429

    response = client.post("/api/v1/voice/stt/token")
    assert response.status_code == 200


def test_exhausting_stt_token_does_not_exhaust_tts(client: TestClient):
    for _ in range(10):
        client.post("/api/v1/voice/stt/token")
    assert client.post("/api/v1/voice/stt/token").status_code == 429

    response = client.post("/api/v1/voice/tts", json={"text": "still allowed"})
    assert response.status_code == 200
