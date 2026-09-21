"""Task 41 — DeepgramSttAuthProvider: configuration validation and
HTTP-response translation into stable VoiceError subclasses. No real
network call is ever made — `httpx.AsyncClient` is monkeypatched with a
`MockTransport` that returns a canned response for every case."""

import httpx
import pytest

from app.voice.exceptions import (
    VoiceConfigurationError,
    VoiceProviderRejectedError,
    VoiceProviderUnavailableError,
    VoiceTimeoutError,
)
from app.voice.providers.deepgram_auth import DeepgramSttAuthProvider


def make_provider(**overrides) -> DeepgramSttAuthProvider:
    kwargs = dict(api_key="fake-deepgram-key", timeout_seconds=5)
    kwargs.update(overrides)
    return DeepgramSttAuthProvider(**kwargs)


def _install_transport(monkeypatch, handler):
    """Replaces httpx.AsyncClient's transport for the duration of one test
    so `grant_token()` exercises its real request/response-parsing code
    without ever reaching the network."""
    import app.voice.providers.deepgram_auth as deepgram_auth

    real_async_client = httpx.AsyncClient

    def fake_async_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(deepgram_auth.httpx, "AsyncClient", fake_async_client)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def test_missing_api_key_raises_configuration_error():
    with pytest.raises(VoiceConfigurationError):
        make_provider(api_key=None)


def test_empty_api_key_raises_configuration_error():
    with pytest.raises(VoiceConfigurationError):
        make_provider(api_key="")


# ---------------------------------------------------------------------------
# grant_token() success and error translation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_successful_grant_returns_normalized_token(monkeypatch):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers.get("authorization")
        return httpx.Response(200, json={"access_token": "temp-jwt", "expires_in": 30})

    _install_transport(monkeypatch, handler)
    provider = make_provider(api_key="fake-deepgram-key")

    token = await provider.grant_token()

    assert token.access_token == "temp-jwt"
    assert token.expires_in == 30
    assert captured["url"] == "https://api.deepgram.com/v1/auth/grant"
    assert captured["authorization"] == "Token fake-deepgram-key"


@pytest.mark.asyncio
async def test_unauthorized_response_is_translated_to_configuration_error(monkeypatch):
    _install_transport(monkeypatch, lambda request: httpx.Response(401, json={"err_msg": "invalid key"}))
    provider = make_provider()

    with pytest.raises(VoiceConfigurationError):
        await provider.grant_token()


@pytest.mark.asyncio
async def test_forbidden_response_is_translated_to_configuration_error(monkeypatch):
    _install_transport(monkeypatch, lambda request: httpx.Response(403, json={"err_msg": "forbidden"}))
    provider = make_provider()

    with pytest.raises(VoiceConfigurationError):
        await provider.grant_token()


@pytest.mark.asyncio
async def test_server_error_response_is_translated_to_provider_unavailable_error(monkeypatch):
    _install_transport(monkeypatch, lambda request: httpx.Response(503, text="service unavailable"))
    provider = make_provider()

    with pytest.raises(VoiceProviderUnavailableError):
        await provider.grant_token()


@pytest.mark.asyncio
async def test_bad_request_response_is_translated_to_provider_rejected_error(monkeypatch):
    _install_transport(monkeypatch, lambda request: httpx.Response(400, json={"err_msg": "bad request"}))
    provider = make_provider()

    with pytest.raises(VoiceProviderRejectedError):
        await provider.grant_token()


@pytest.mark.asyncio
async def test_malformed_success_body_is_translated_to_provider_unavailable_error(monkeypatch):
    _install_transport(monkeypatch, lambda request: httpx.Response(200, json={"unexpected": "shape"}))
    provider = make_provider()

    with pytest.raises(VoiceProviderUnavailableError):
        await provider.grant_token()


@pytest.mark.asyncio
async def test_connection_failure_is_translated_to_provider_unavailable_error(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    _install_transport(monkeypatch, handler)
    provider = make_provider()

    with pytest.raises(VoiceProviderUnavailableError):
        await provider.grant_token()


@pytest.mark.asyncio
async def test_timeout_is_translated_to_timeout_error(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out", request=request)

    _install_transport(monkeypatch, handler)
    provider = make_provider(timeout_seconds=1)

    with pytest.raises(VoiceTimeoutError):
        await provider.grant_token()


# ---------------------------------------------------------------------------
# Security: the response/exception never carries the permanent key
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_error_paths_never_include_the_permanent_key_in_the_exception_message(monkeypatch):
    _install_transport(monkeypatch, lambda request: httpx.Response(401, json={"err_msg": "invalid"}))
    provider = make_provider(api_key="super-secret-permanent-key")

    with pytest.raises(VoiceConfigurationError) as exc_info:
        await provider.grant_token()

    assert "super-secret-permanent-key" not in str(exc_info.value)
