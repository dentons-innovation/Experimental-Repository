"""User repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
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

    async def search(
        self,
        query: str,
        exclude_user_id: UUID | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[User], int]:
        """Search users by username, email, or full_name.

        Case-insensitive ILIKE search.  Query is capped at 100 characters.
        Results exclude the searching user.
        """
        q = query.strip()[:100]
        if not q:
            return [], 0

        pattern = f"%{q}%"
        search_filter = or_(
            User.username.ilike(pattern),
            User.email.ilike(pattern),
            User.full_name.ilike(pattern),
        )

        filters = [search_filter]
        if exclude_user_id is not None:
            filters.append(User.id != exclude_user_id)

        count_result = await self.session.execute(
            select(func.count()).select_from(select(User).where(*filters).subquery())
        )
        total = count_result.scalar_one()

        result = await self.session.execute(
            select(User)
            .where(*filters)
            .order_by(User.username)
            .offset(offset)
            .limit(min(limit, 50))  # Hard cap at 50 results per page
        )
        return list(result.scalars().all()), total
