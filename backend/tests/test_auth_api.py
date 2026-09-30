import hashlib

import pytest
from sqlalchemy import select

from app.api.deps import get_google_verifier
from app.core.config import settings
from app.main import app
from app.models.auth_session import AuthSession
from app.models.user import User
from tests.auth_helpers import (
    auth_app,
    bad_signature_token,
    make_google_token,
    sign_in,
)

COOKIE = settings.session_cookie_name


@pytest.fixture()
def env():
    with auth_app() as (make_client, session_factory, _redis):
        yield make_client, session_factory


def _count(session_factory, model):
    with session_factory() as db:
        return len(db.execute(select(model)).scalars().all())


# --------------------------------------------------------------------------
# Google credential verification
# --------------------------------------------------------------------------


def test_valid_google_credential_creates_user_and_session(env):
    make_client, session_factory = env
    client = make_client()

    response = sign_in(client)

    assert response.status_code == 200
    user = response.json()["data"]["user"]
    assert user["email"] == "azar@example.com"
    assert user["name"] == "Azar User"
    assert user["avatar_url"] == "https://example.com/a.png"
    assert set(user) == {"id", "name", "email", "avatar_url"}
    with session_factory() as db:
        row = db.execute(select(User)).scalar_one()
        assert row.google_subject == "google-sub-1"
        assert str(row.id) == user["id"]
    assert _count(session_factory, AuthSession) == 1


def test_valid_credential_for_existing_user_reuses_user_and_refreshes_profile(env):
    make_client, session_factory = env
    first = sign_in(make_client()).json()["data"]["user"]

    second = sign_in(make_client(), name="Renamed", email="new@example.com").json()["data"]["user"]

    assert second["id"] == first["id"]
    assert second["name"] == "Renamed"
    assert _count(session_factory, User) == 1
    assert _count(session_factory, AuthSession) == 2  # one server-side session per login


def test_identity_is_keyed_by_google_subject_not_email(env):
    make_client, session_factory = env
    a = sign_in(make_client(), sub="sub-a", email="same@example.com").json()["data"]["user"]
    b = sign_in(make_client(), sub="sub-b", email="same@example.com").json()["data"]["user"]

    assert a["id"] != b["id"]
    assert _count(session_factory, User) == 2


@pytest.mark.parametrize(
    "credential_factory",
    [
        pytest.param(lambda: "not-a-jwt", id="garbage"),
        pytest.param(lambda: bad_signature_token(), id="bad-signature"),
        pytest.param(lambda: make_google_token(aud="someone-elses-client-id"), id="wrong-audience"),
        pytest.param(lambda: make_google_token(exp_delta=-3600), id="expired"),
        pytest.param(lambda: make_google_token(iss="https://evil.example.com"), id="wrong-issuer"),
        pytest.param(lambda: make_google_token(email_verified=False), id="unverified-email"),
    ],
)
def test_invalid_google_credentials_are_rejected_and_create_nothing(env, credential_factory):
    make_client, session_factory = env
    client = make_client()

    response = client.post("/api/v1/auth/google", json={"credential": credential_factory()})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_GOOGLE_CREDENTIAL"
    assert COOKIE not in response.cookies
    assert _count(session_factory, User) == 0
    assert _count(session_factory, AuthSession) == 0


def test_missing_credential_is_a_validation_error(env):
    make_client, _ = env
    assert make_client().post("/api/v1/auth/google", json={}).status_code == 422


def test_unconfigured_google_client_id_fails_clearly(monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", None)
    with auth_app() as (make_client, _sf, _r):
        del app.dependency_overrides[get_google_verifier]  # use the real, settings-driven dependency
        response = make_client().post("/api/v1/auth/google", json={"credential": "x"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AUTH_NOT_CONFIGURED"


# --------------------------------------------------------------------------
# Sessions and cookie
# --------------------------------------------------------------------------


def test_login_sets_httponly_session_cookie_and_never_returns_the_token(env):
    make_client, _ = env
    client = make_client()

    response = sign_in(client)

    set_cookie = response.headers["set-cookie"]
    assert set_cookie.startswith(f"{COOKIE}=")
    lowered = set_cookie.lower()
    assert "httponly" in lowered
    assert "path=/" in lowered
    assert f"max-age={settings.session_lifetime_seconds}" in lowered
    assert "samesite=" in lowered
    raw_token = response.cookies[COOKIE]
    assert raw_token not in response.text  # never in the JSON body


def test_authenticated_session_works(env):
    make_client, _ = env
    client = make_client()
    user = sign_in(client).json()["data"]["user"]

    me = client.get("/api/v1/auth/me")

    assert me.status_code == 200
    assert me.json()["data"]["user"] == user


def test_missing_cookie_returns_401(env):
    make_client, _ = env
    response = make_client().get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_unknown_token_returns_401(env):
    make_client, _ = env
    client = make_client()
    client.cookies.set(COOKIE, "definitely-not-a-real-token")
    assert client.get("/api/v1/auth/me").status_code == 401


def test_expired_session_returns_401(env):
    from datetime import UTC, datetime, timedelta

    make_client, session_factory = env
    client = make_client()
    sign_in(client)
    with session_factory() as db:
        row = db.execute(select(AuthSession)).scalar_one()
        row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()

    assert client.get("/api/v1/auth/me").status_code == 401


def test_revoked_session_returns_401(env):
    from datetime import UTC, datetime

    make_client, session_factory = env
    client = make_client()
    sign_in(client)
    with session_factory() as db:
        row = db.execute(select(AuthSession)).scalar_one()
        row.revoked_at = datetime.now(UTC)
        db.commit()

    assert client.get("/api/v1/auth/me").status_code == 401


def test_logout_revokes_session_and_clears_cookie(env):
    make_client, session_factory = env
    client = make_client()
    sign_in(client)
    raw_token = client.cookies.get(COOKIE)

    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 204
    cleared = response.headers["set-cookie"].lower()
    assert f"{COOKIE}=" in cleared and ("max-age=0" in cleared or "expires=" in cleared)
    with session_factory() as db:
        assert db.execute(select(AuthSession)).scalar_one().revoked_at is not None
    # The old token no longer authenticates, even if a client kept it.
    replay = make_client()
    replay.cookies.set(COOKIE, raw_token)
    assert replay.get("/api/v1/auth/me").status_code == 401


def test_logout_when_already_logged_out_is_safe(env):
    make_client, _ = env
    client = make_client()
    assert client.post("/api/v1/auth/logout").status_code == 204
    sign_in(client)
    assert client.post("/api/v1/auth/logout").status_code == 204
    assert client.post("/api/v1/auth/logout").status_code == 204


def test_raw_session_token_is_never_stored(env):
    make_client, session_factory = env
    client = make_client()
    sign_in(client)
    raw_token = client.cookies.get(COOKIE)

    with session_factory() as db:
        row = db.execute(select(AuthSession)).scalar_one()
        stored = row.token_hash
    assert stored != raw_token
    assert stored == hashlib.sha256(raw_token.encode()).hexdigest()
    assert len(stored) == 64
    # And nothing in the table (any column) equals the raw token.
    with session_factory() as db:
        for r in db.execute(select(AuthSession)).scalars():
            assert raw_token not in {str(getattr(r, c.name)) for c in AuthSession.__table__.columns}


def test_each_login_gets_a_distinct_random_token(env):
    make_client, _ = env
    a, b = make_client(), make_client()
    sign_in(a)
    sign_in(b)
    assert a.cookies.get(COOKIE) != b.cookies.get(COOKIE)
    assert len(a.cookies.get(COOKIE)) >= 40


def test_openapi_documents_auth_endpoints_and_401():
    schema = app.openapi()
    assert "/api/v1/auth/google" in schema["paths"]
    assert "401" in schema["paths"]["/api/v1/auth/me"]["get"]["responses"]
    assert "/api/v1/auth/logout" in schema["paths"]
    # No token field anywhere in the auth response schemas.
    assert "token" not in str(schema["components"]["schemas"].get("AuthUserResponse", "")).lower()
