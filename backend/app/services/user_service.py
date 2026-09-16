"""User service."""

from __future__ import annotations

from uuid import UUID

from app.domain.exceptions import NotFoundError
from app.domain.models import User
from app.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, user_repo: UserRepository) -> None:
        self._user_repo = user_repo

    async def get_by_id(self, user_id: UUID) -> User:
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User", str(user_id))
        return user

    async def get_by_email(self, email: str) -> User:
        user = await self._user_repo.get_by_email(email)
        if user is None:
            raise NotFoundError("User", email)
        return user
