"""User repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_id(self, id: UUID) -> User | None:
        result = await self.session.execute(select(User).where(User.id == id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.username == username.lower())
        )
        return result.scalar_one_or_none()

    async def create_user(
        self,
        email: str,
        username: str,
        full_name: str,
        password_hash: str,
        avatar_url: str | None = None,
    ) -> User:
        """Create a new user with hashed password."""
        user = User(
            email=email.lower(),
            username=username.lower(),
            full_name=full_name,
            password_hash=password_hash,
            avatar_url=avatar_url,
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user
