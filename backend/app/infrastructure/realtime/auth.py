"""WebSocket authentication for the real-time layer.

Validates JWT tokens passed as query parameters during the WebSocket
handshake.  Reuses the existing ``JWTVerifier`` infrastructure — no
separate auth logic.
"""

from __future__ import annotations

from uuid import UUID

import structlog

from app.domain.exceptions import AuthenticationError
from app.infrastructure.auth import JWTVerifier

logger = structlog.get_logger(__name__)


def authenticate_ws_token(token: str | None, verifier: JWTVerifier) -> UUID:
    """Validate a WS token and return the authenticated user's UUID.

    Args:
        token: The JWT access token (from the ``token`` query parameter).
        verifier: The shared JWT verifier instance.

    Returns:
        The user's UUID.

    Raises:
        AuthenticationError: If the token is missing, invalid, or expired.
    """
    if not token:
        raise AuthenticationError("Missing authentication token")

    user_id_str = verifier.verify(token)
    try:
        return UUID(user_id_str)
    except ValueError as exc:
        raise AuthenticationError("Invalid user identifier in token") from exc
