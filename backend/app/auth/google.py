import time
from dataclasses import dataclass
from typing import Callable, Protocol

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app.auth.exceptions import AuthNotConfiguredError, InvalidGoogleCredentialError
from app.core.config import settings

GOOGLE_ISSUERS = frozenset({"accounts.google.com", "https://accounts.google.com"})


@dataclass(frozen=True)
class GoogleIdentity:
    subject: str
    email: str
    name: str
    avatar_url: str | None


class GoogleIdentityVerifier(Protocol):
    def verify(self, credential: str) -> GoogleIdentity: ...


class GoogleIdTokenVerifier:
    """Verifies a Google Sign-In ID token with Google's official library
    (signature against Google's published certs, audience, expiry, issuer)
    and then re-checks the claims this app depends on. The payload is never
    trusted without that verification.

    `http_request` is injectable so tests can serve a test key's certs
    without network access; production uses google-auth's `requests` transport.
    """

    def __init__(self, client_id: str, http_request: Callable | None = None):
        self._client_id = client_id
        self._request = http_request or google_requests.Request()

    def verify(self, credential: str) -> GoogleIdentity:
        try:
            claims = id_token.verify_oauth2_token(credential, self._request, self._client_id)
        except Exception as exc:  # google-auth raises ValueError / GoogleAuthError / transport errors
            raise InvalidGoogleCredentialError("The Google credential could not be verified.") from exc

        # Defense in depth: explicit re-checks of everything we rely on.
        if claims.get("iss") not in GOOGLE_ISSUERS:
            raise InvalidGoogleCredentialError("The Google credential has an invalid issuer.")
        audience = claims.get("aud")
        if audience != self._client_id:
            raise InvalidGoogleCredentialError("The Google credential was issued for a different client.")
        exp = claims.get("exp")
        if not isinstance(exp, int | float) or exp <= time.time():
            raise InvalidGoogleCredentialError("The Google credential has expired.")
        subject = claims.get("sub")
        email = claims.get("email")
        if not subject or not isinstance(subject, str) or not email or not isinstance(email, str):
            raise InvalidGoogleCredentialError("The Google credential is missing required identity claims.")
        if claims.get("email_verified") is not True:
            raise InvalidGoogleCredentialError("The Google account email is not verified.")

        name = claims.get("name") or email.split("@", 1)[0]
        picture = claims.get("picture")
        return GoogleIdentity(
            subject=subject,
            email=email,
            name=str(name),
            avatar_url=picture if isinstance(picture, str) and picture else None,
        )


def get_configured_google_verifier() -> GoogleIdentityVerifier:
    if not settings.google_client_id:
        raise AuthNotConfiguredError("Google Sign-In is not configured on the server.")
    return GoogleIdTokenVerifier(settings.google_client_id)
