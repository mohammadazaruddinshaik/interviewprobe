class AuthError(Exception):
    """Base class for authentication failures."""


class AuthenticationRequiredError(AuthError):
    """No valid authenticated session (missing/unknown/expired/revoked cookie)."""


class InvalidGoogleCredentialError(AuthError):
    """The Google ID token failed verification."""


class AuthNotConfiguredError(AuthError):
    """Google Sign-In is not configured on the server (no GOOGLE_CLIENT_ID)."""
