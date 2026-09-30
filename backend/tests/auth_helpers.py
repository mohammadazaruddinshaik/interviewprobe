"""Shared helpers for the authentication / ownership tests.

Unlike the other API tests these do NOT override `get_current_user`: they
exercise the real cookie -> server-session -> user dependency. Only the
Google verifier's *network* (cert fetch) is faked; signature/audience/
issuer/expiry checks run for real against a locally generated RSA key.
"""

import json
import time
from contextlib import contextmanager
from types import SimpleNamespace

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from google.auth import crypt
from google.auth import jwt as google_jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import (
    get_claim_investigator,
    get_google_verifier,
    get_interview_planner,
    get_knowledge_retrieval_service,
    get_llm_provider,
)
from app.auth.google import GoogleIdTokenVerifier
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.redis.client import get_redis_client
from tests.fakes import FakeAsyncRedis
from tests.test_interview_api import default_fake_llm_provider  # also registers sqlite UUID/JSONB compilers

CLIENT_ID = "test-client-id.apps.googleusercontent.com"
FRONTEND_ORIGIN = "http://localhost:5173"
EVIL_ORIGIN = "https://evil.example.com"
KEY_ID = "test-key-1"


def _generate_key_pair() -> tuple[str, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ).decode()
    public_pem = (
        private_key.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )
    return private_pem, public_pem


_PRIVATE_PEM, _PUBLIC_PEM = _generate_key_pair()
_OTHER_PRIVATE_PEM, _ = _generate_key_pair()


def fake_google_request(url, method="GET", body=None, headers=None, timeout=None, **kwargs):
    """Stands in for Google's cert endpoint: serves only the test public key."""
    return SimpleNamespace(status=200, data=json.dumps({KEY_ID: _PUBLIC_PEM}).encode(), headers={})


def make_google_token(
    *,
    sub="google-sub-1",
    email="azar@example.com",
    name="Azar User",
    picture="https://example.com/a.png",
    aud=CLIENT_ID,
    iss="https://accounts.google.com",
    exp_delta=3600,
    email_verified=True,
    signing_key=None,
) -> str:
    now = int(time.time())
    payload = {
        "iss": iss,
        "aud": aud,
        "sub": sub,
        "email": email,
        "email_verified": email_verified,
        "name": name,
        "picture": picture,
        "iat": now - 10,
        "exp": now + exp_delta,
    }
    signer = crypt.RSASigner.from_string(signing_key or _PRIVATE_PEM, key_id=KEY_ID)
    return google_jwt.encode(signer, payload, key_id=KEY_ID).decode()


def bad_signature_token(**kwargs) -> str:
    return make_google_token(signing_key=_OTHER_PRIVATE_PEM, **kwargs)


def real_verifier() -> GoogleIdTokenVerifier:
    return GoogleIdTokenVerifier(CLIENT_ID, http_request=fake_google_request)


@contextmanager
def auth_app(*, with_interview_overrides: bool = False):
    """Yields (make_client, session_factory, fake_redis). `make_client()`
    returns an independent TestClient (own cookie jar) against the shared app."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    fake_redis = FakeAsyncRedis()
    fake_llm = default_fake_llm_provider()

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    async def override_get_redis_client():
        return fake_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_google_verifier] = real_verifier
    app.dependency_overrides[get_redis_client] = override_get_redis_client
    app.dependency_overrides[get_llm_provider] = lambda: fake_llm
    app.dependency_overrides[get_knowledge_retrieval_service] = lambda: None
    app.dependency_overrides[get_interview_planner] = lambda: None
    app.dependency_overrides[get_claim_investigator] = lambda: None

    clients: list[TestClient] = []

    def make_client() -> TestClient:
        c = TestClient(app, headers={"Origin": FRONTEND_ORIGIN})
        c.__enter__()
        clients.append(c)
        return c

    try:
        yield make_client, session_factory, fake_redis
    finally:
        for c in clients:
            c.__exit__(None, None, None)
        app.dependency_overrides.clear()
        engine.dispose()


def sign_in(client: TestClient, **token_kwargs):
    return client.post("/api/v1/auth/google", json={"credential": make_google_token(**token_kwargs)})
