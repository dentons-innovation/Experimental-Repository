"""Task repository with filtering, sorting, pagination, and OCC support."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.enums import TaskPriority, TaskStatus
from app.domain.models import Task, TaskLabel
from app.repositories.base import BaseRepository


@dataclass
class TaskFilters:
    """Query filters for task listing."""

    status: list[TaskStatus] = field(default_factory=list)
    priority: list[TaskPriority] = field(default_factory=list)
    assignee_id: UUID | None = None
    label_ids: list[UUID] = field(default_factory=list)
    search: str | None = None
    sort_by: str = "created_at"
    sort_order: str = "desc"


ALLOWED_SORT_FIELDS = {
    "created_at",
    "updated_at",
    "due_date",
    "priority",
    "status",
    "title",
}
PRIORITY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


class TaskRepository(BaseRepository[Task]):
    model = Task

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_id_with_details(self, task_id: UUID) -> Task | None:
        result = await self.session.execute(
            select(Task)
            .where(Task.id == task_id)
            .options(
                selectinload(Task.labels),
                selectinload(Task.assignee),
                selectinload(Task.creator),
                selectinload(Task.task_labels).selectinload(TaskLabel.label),
            )
        )
        return result.scalar_one_or_none()

    async def list_for_project(
        self,
        project_id: UUID,
        filters: TaskFilters,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Task], int]:
        """List tasks for a project with filters/sort/pagination. N+1-free."""
        conditions = [Task.project_id == project_id]

        if filters.status:
            conditions.append(Task.status.in_(filters.status))
        if filters.priority:
            conditions.append(Task.priority.in_(filters.priority))
        if filters.assignee_id is not None:
            conditions.append(Task.assignee_id == filters.assignee_id)
        if filters.search:
            search_term = f"%{filters.search}%"
            conditions.append(Task.title.ilike(search_term))

        base_query = select(Task).where(and_(*conditions))

        # Apply label filter via subquery (avoid cartesian product)
        if filters.label_ids:
            for label_id in filters.label_ids:
                label_subq = (
                    select(TaskLabel.task_id)
                    .where(TaskLabel.label_id == label_id)
                    .scalar_subquery()
                )
                base_query = base_query.where(Task.id.in_(label_subq))

        # Count total (without pagination)
        count_result = await self.session.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total = count_result.scalar_one()

        # Apply sort
        sort_field = (
            filters.sort_by if filters.sort_by in ALLOWED_SORT_FIELDS else "created_at"
        )
        sort_col = getattr(Task, sort_field)
        if filters.sort_order.lower() == "asc":
            base_query = base_query.order_by(sort_col.asc())
        else:
            base_query = base_query.order_by(sort_col.desc())

        result = await self.session.execute(
            base_query.options(
                selectinload(Task.labels),
                selectinload(Task.assignee),
                selectinload(Task.creator),
            )
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all()), total

    async def update_with_version_check(
        self,
        task_id: UUID,
        expected_version: int,
        updates: dict[str, object],
    ) -> bool:
        """Atomically update a task only if its version matches.

        Returns True if the update succeeded, False if the version
        didn't match (concurrent modification detected).

        The version is incremented atomically as part of the UPDATE
        statement so no race condition exists between read and write.
        """
        stmt = (
            update(Task)
            .where(Task.id == task_id, Task.version == expected_version)
            .values(**updates, version=Task.version + 1)
            .returning(Task.id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def add_label(self, task_id: UUID, label_id: UUID) -> None:
        task_label = TaskLabel(task_id=task_id, label_id=label_id)
        self.session.add(task_label)
        await self.session.flush()

    async def remove_label(self, task_id: UUID, label_id: UUID) -> None:
        result = await self.session.execute(
            select(TaskLabel).where(
                TaskLabel.task_id == task_id, TaskLabel.label_id == label_id
            )
        )
        task_label = result.scalar_one_or_none()
        if task_label:
            await self.session.delete(task_label)
            await self.session.flush()
