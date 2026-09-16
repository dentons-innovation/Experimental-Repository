"""Authentication infrastructure — password hashing and JWT token handling.

Security model:
- Passwords are salted and hashed using bcrypt.
- JWTs are signed with HMAC-SHA256 (HS256) using a secret key.
- Tokens contain subject (user UUID), email, username, issued-at, and expiration claims.
- The backend verifies signature, expiry, and presence of subject claim on every request.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any
from uuid import UUID

import bcrypt
import jwt
import structlog

from app.core.config import Settings, get_settings
from app.domain.exceptions import AuthenticationError

logger = structlog.get_logger(__name__)


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception as exc:
        logger.warning("password_verification_failed", error=str(exc))
        return False


def create_access_token(
    user_id: UUID,
    email: str,
    username: str,
    expires_delta: timedelta | None = None,
    settings: Settings | None = None,
) -> str:
    """Create a signed JWT access token."""
    s = settings or get_settings()
    now = datetime.now(UTC)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=s.jwt_access_token_expire_minutes)

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "username": username,
        "iat": now,
        "exp": expire,
    }

    token = jwt.encode(payload, s.jwt_secret_key, algorithm=s.jwt_algorithm)
    return token


class JWTVerifier:
    """Verifies backend-issued JWT tokens."""

    def __init__(self, settings: Settings) -> None:
        self._secret = settings.jwt_secret_key
        self._algorithm = settings.jwt_algorithm

    def verify_token(self, token: str) -> dict[str, Any]:
        """Decode and verify JWT token, returning payload claims dictionary.

        Raises:
            AuthenticationError: If the token is invalid or expired.
        """
        try:
            payload: dict[str, Any] = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                options={
                    "verify_exp": True,
                    "verify_iat": True,
                },
            )
            return payload
        except jwt.ExpiredSignatureError as exc:
            raise AuthenticationError("Token has expired") from exc
        except jwt.PyJWTError as exc:
            logger.warning("jwt_decode_failed", error=str(exc))
            raise AuthenticationError(f"Invalid token: {exc}") from exc

    def verify(self, token: str) -> str:
        """Verify token and return subject (user ID as string)."""
        payload = self.verify_token(token)
        sub = payload.get("sub")
        if not sub:
            raise AuthenticationError("Token missing subject claim")
        return str(sub)


@lru_cache
def get_jwt_verifier() -> JWTVerifier:
    """Cached JWT verifier singleton."""
    return JWTVerifier(get_settings())
