import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.exceptions import AuthenticationRequiredError
from app.auth.google import GoogleIdentity
from app.models.auth_session import AuthSession
from app.models.user import User


def hash_session_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _as_utc(value: datetime) -> datetime:
    # SQLite (used in tests) returns naive datetimes; PostgreSQL returns aware ones.
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


@dataclass(frozen=True)
class IssuedSession:
    raw_token: str
    expires_at: datetime


class AuthService:
    """Owns the auth transaction boundary (commits), mirroring InterviewService."""

    def __init__(self, db: Session, session_lifetime_seconds: int):
        self._db = db
        self._lifetime = timedelta(seconds=session_lifetime_seconds)

    # -- login ---------------------------------------------------------

    def sign_in(self, identity: GoogleIdentity) -> tuple[User, IssuedSession]:
        user = self._upsert_user(identity)
        raw_token = secrets.token_urlsafe(32)  # 256 bits from the OS CSPRNG
        expires_at = datetime.now(UTC) + self._lifetime
        self._db.add(AuthSession(user_id=user.id, token_hash=hash_session_token(raw_token), expires_at=expires_at))
        self._db.commit()
        self._db.refresh(user)
        return user, IssuedSession(raw_token=raw_token, expires_at=expires_at)

    def _upsert_user(self, identity: GoogleIdentity) -> User:
        user = self._find_by_subject(identity.subject)
        if user is None:
            user = User(
                google_subject=identity.subject,
                email=identity.email,
                name=identity.name,
                avatar_url=identity.avatar_url,
            )
            self._db.add(user)
            try:
                self._db.flush()
            except IntegrityError:
                # A concurrent first login created the same subject.
                self._db.rollback()
                user = self._find_by_subject(identity.subject)
                if user is None:
                    raise
        else:
            # Only safe profile fields are refreshed; identity (sub) never changes.
            user.email = identity.email
            user.name = identity.name
            user.avatar_url = identity.avatar_url
        return user

    def _find_by_subject(self, subject: str) -> User | None:
        return self._db.execute(select(User).where(User.google_subject == subject)).scalar_one_or_none()

    # -- current user / logout -----------------------------------------

    def get_user_for_token(self, raw_token: str | None) -> User:
        if not raw_token:
            raise AuthenticationRequiredError("Authentication is required.")
        auth_session = self._db.execute(
            select(AuthSession).where(AuthSession.token_hash == hash_session_token(raw_token))
        ).scalar_one_or_none()
        if auth_session is None or auth_session.revoked_at is not None:
            raise AuthenticationRequiredError("Authentication is required.")
        if _as_utc(auth_session.expires_at) <= datetime.now(UTC):
            raise AuthenticationRequiredError("Authentication is required.")
        user = self._db.get(User, auth_session.user_id)
        if user is None:
            raise AuthenticationRequiredError("Authentication is required.")
        return user

    def logout(self, raw_token: str | None) -> None:
        """Revoke the session for this token. Safe when already logged out."""
        if not raw_token:
            return
        auth_session = self._db.execute(
            select(AuthSession).where(AuthSession.token_hash == hash_session_token(raw_token))
        ).scalar_one_or_none()
        if auth_session is not None and auth_session.revoked_at is None:
            auth_session.revoked_at = datetime.now(UTC)
            self._db.commit()

