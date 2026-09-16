"""FastAPI dependency providers.

All shared dependencies (DB session, current user, pagination params,
service factories) are defined here and injected via Depends().
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.domain.exceptions import AuthenticationError
from app.infrastructure.auth import JWTVerifier, get_jwt_verifier

if TYPE_CHECKING:
    from app.domain.models import User


# ─────────────────────────────────────────────────────────────
# Current user extraction
# ─────────────────────────────────────────────────────────────

async def get_current_user_id(
    authorization: Annotated[str | None, Header()] = None,
    jwt_verifier: JWTVerifier = Depends(get_jwt_verifier),
) -> UUID:
    """Extract and verify user ID from Bearer JWT.

    Returns the user's UUID.
    Raises HTTP 401 if the token is missing or invalid.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id_str = jwt_verifier.verify(token)
        return UUID(user_id_str)
    except (AuthenticationError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_current_user(
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """Retrieve the current authenticated User model."""
    from app.repositories.user_repository import UserRepository

    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


# Type aliases for use in route signatures
CurrentUserId = Annotated[UUID, Depends(get_current_user_id)]


# ─────────────────────────────────────────────────────────────
# Pagination
# ─────────────────────────────────────────────────────────────

class PaginationParams:
    """Standard pagination query parameters."""

    MAX_PAGE_SIZE = 100

    def __init__(
        self,
        page: Annotated[int, Query(ge=1, description="Page number (1-indexed)")] = 1,
        page_size: Annotated[
            int, Query(ge=1, le=100, description="Items per page (max 100)")
        ] = 20,
    ) -> None:
        self.page = page
        self.page_size = page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


Pagination = Annotated[PaginationParams, Depends(PaginationParams)]
DbSession = Annotated[AsyncSession, Depends(get_db_session)]
