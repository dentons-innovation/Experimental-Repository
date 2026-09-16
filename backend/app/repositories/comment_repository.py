"""Comment repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.models import Comment
from app.repositories.base import BaseRepository


class CommentRepository(BaseRepository[Comment]):
    model = Comment

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_id_with_author(self, comment_id: UUID) -> Comment | None:
        result = await self.session.execute(
            select(Comment)
            .where(Comment.id == comment_id)
            .options(selectinload(Comment.author))
        )
        return result.scalar_one_or_none()

    async def list_for_task(
        self, task_id: UUID, offset: int = 0, limit: int = 50
    ) -> tuple[list[Comment], int]:
        count_result = await self.session.execute(
            select(func.count()).where(Comment.task_id == task_id)
        )
        total = count_result.scalar_one()

        result = await self.session.execute(
            select(Comment)
            .where(Comment.task_id == task_id)
            .options(selectinload(Comment.author))
            .order_by(Comment.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all()), total
