"""Activity log repository — append-only."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.enums import ActivityAction
from app.domain.models import ActivityLog
from app.repositories.base import BaseRepository


class ActivityRepository(BaseRepository[ActivityLog]):
    model = ActivityLog

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create(
        self,
        task_id: UUID,
        workspace_id: UUID,
        project_id: UUID,
        actor_id: UUID,
        action: ActivityAction,
        old_value: str | None = None,
        new_value: str | None = None,
    ) -> ActivityLog:
        log = ActivityLog(
            task_id=task_id,
            workspace_id=workspace_id,
            project_id=project_id,
            actor_id=actor_id,
            action=action,
            old_value=old_value,
            new_value=new_value,
        )
        self.session.add(log)
        await self.session.flush()
        return log

    async def list_for_task(
        self, task_id: UUID, offset: int = 0, limit: int = 50
    ) -> tuple[list[ActivityLog], int]:
        count_result = await self.session.execute(
            select(func.count()).where(ActivityLog.task_id == task_id)
        )
        total = count_result.scalar_one()

        result = await self.session.execute(
            select(ActivityLog)
            .where(ActivityLog.task_id == task_id)
            .options(selectinload(ActivityLog.actor))
            .order_by(ActivityLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all()), total
