"""Label repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Label
from app.repositories.base import BaseRepository


class LabelRepository(BaseRepository[Label]):
    model = Label

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_workspace_and_name(
        self, workspace_id: UUID, name: str
    ) -> Label | None:
        result = await self.session.execute(
            select(Label).where(
                Label.workspace_id == workspace_id,
                Label.name == name,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_workspace(self, workspace_id: UUID) -> list[Label]:
        result = await self.session.execute(
            select(Label)
            .where(Label.workspace_id == workspace_id)
            .order_by(Label.name)
        )
        return list(result.scalars().all())

    async def get_by_ids(self, label_ids: list[UUID]) -> list[Label]:
        if not label_ids:
            return []
        result = await self.session.execute(
            select(Label).where(Label.id.in_(label_ids))
        )
        return list(result.scalars().all())
