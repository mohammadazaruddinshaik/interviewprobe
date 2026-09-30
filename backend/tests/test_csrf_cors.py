import pytest
from pydantic import ValidationError

from app.core.config import Settings, settings
from tests.auth_helpers import EVIL_ORIGIN, FRONTEND_ORIGIN, auth_app, make_google_token, sign_in

COOKIE = settings.session_cookie_name


@pytest.fixture()
def env():
    with auth_app() as (make_client, _sf, _r):
        yield make_client


def test_configured_frontend_origin_works_with_credentials(env):
    client = env()
    response = client.get("/api/v1/auth/me", headers={"Origin": FRONTEND_ORIGIN})
    assert response.headers["access-control-allow-origin"] == FRONTEND_ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"


def test_preflight_for_configured_origin_allows_credentials(env):
    client = env()
    response = client.options(
        "/api/v1/auth/google",
        headers={
            "Origin": FRONTEND_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == FRONTEND_ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"


def test_unauthorized_origin_is_not_granted_cors(env):
    client = env()
    preflight = client.options(
        "/api/v1/auth/google",
        headers={"Origin": EVIL_ORIGIN, "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in preflight.headers
    simple = client.get("/api/v1/auth/me", headers={"Origin": EVIL_ORIGIN})
    assert "access-control-allow-origin" not in simple.headers


def test_state_changing_request_from_unauthorized_origin_is_rejected(env):
    client = env()
    response = client.post(
        "/api/v1/auth/google",
        json={"credential": make_google_token()},
        headers={"Origin": EVIL_ORIGIN},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ORIGIN_NOT_ALLOWED"
    assert COOKIE not in response.cookies  # no session was created


def test_cross_site_logout_with_cookie_is_rejected_and_session_survives(env):
    client = env()
    sign_in(client)

    forged = client.post("/api/v1/auth/logout", headers={"Origin": EVIL_ORIGIN})

    assert forged.status_code == 403
    assert client.get("/api/v1/auth/me").status_code == 200  # still authenticated


def test_cookie_bearing_state_change_without_origin_is_rejected(env):
    from fastapi.testclient import TestClient

    from app.main import app

    client = env()
    sign_in(client)
    # A client with the session cookie but no Origin header at all (no default headers).
    bare = TestClient(app)
    bare.cookies.set(COOKIE, client.cookies.get(COOKIE))

    response = bare.post("/api/v1/auth/logout")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ORIGIN_NOT_ALLOWED"
    assert client.get("/api/v1/auth/me").status_code == 200  # session untouched


def test_request_without_cookie_or_origin_is_not_blocked_by_csrf_check(env):
    from fastapi.testclient import TestClient

    from app.main import app

    # Non-browser callers (no cookie) are unaffected; they fail on auth, not CSRF.
    assert TestClient(app).post("/api/v1/auth/logout").status_code == 204


def test_safe_methods_are_not_origin_restricted(env):
    client = env()
    assert client.get("/health", headers={"Origin": EVIL_ORIGIN}).status_code == 200


def test_wildcard_cors_origin_is_rejected_by_settings():
    with pytest.raises(ValidationError):
        Settings(cors_allowed_origins=["*"])


def test_samesite_none_forces_secure_cookie():
    assert Settings(session_cookie_samesite="none").effective_session_cookie_secure is True
    assert Settings(environment="production").effective_session_cookie_secure is True
    assert Settings(environment="development").effective_session_cookie_secure is False
