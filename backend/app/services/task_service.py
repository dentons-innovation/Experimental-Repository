"""Task service — task lifecycle, filtering, optimistic concurrency."""

from __future__ import annotations

from datetime import date
from uuid import UUID

import structlog

from app.domain.enums import ActivityAction, TaskPriority, TaskStatus
from app.domain.exceptions import NotFoundError, OptimisticLockError
from app.domain.models import ActivityLog, Task
from app.infrastructure.realtime.publisher import RealtimeEventPublisher
from app.infrastructure.realtime.types import RealtimeEvent
from app.repositories.activity_repository import ActivityRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.task_repository import TaskFilters, TaskRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.services.authorization import AuthorizationService

logger = structlog.get_logger(__name__)

UNSET: object = object()


class TaskService:
    def __init__(
        self,
        task_repo: TaskRepository,
        project_repo: ProjectRepository,
        workspace_repo: WorkspaceRepository,
        activity_repo: ActivityRepository,
        auth_service: AuthorizationService,
        publisher: RealtimeEventPublisher,
    ) -> None:
        self._task_repo = task_repo
        self._proj_repo = project_repo
        self._ws_repo = workspace_repo
        self._activity_repo = activity_repo
        self._auth = auth_service
        self._publisher = publisher

    async def create_task(
        self,
        project_id: UUID,
        creator_id: UUID,
        title: str,
        description: str | None = None,
        status: TaskStatus = TaskStatus.BACKLOG,
        priority: TaskPriority = TaskPriority.MEDIUM,
        assignee_id: UUID | None = None,
        due_date: date | None = None,
        label_ids: list[UUID] | None = None,
    ) -> Task:
        await self._auth.can_create_task(creator_id, project_id)

        project = await self._proj_repo.get_by_id_with_members(project_id)
        if project is None:
            raise NotFoundError("Project", str(project_id))

        task = Task(
            project_id=project_id,
            workspace_id=project.workspace_id,
            title=title,
            description=description,
            status=status,
            priority=priority,
            assignee_id=assignee_id,
            creator_id=creator_id,
            due_date=due_date,
            version=0,
        )
        self._task_repo.session.add(task)
        await self._task_repo.session.flush()
        await self._task_repo.session.refresh(task)

        # Add labels if provided
        if label_ids:
            for label_id in label_ids:
                await self._task_repo.add_label(task.id, label_id)

        # Record activity
        await self._activity_repo.create(
            task_id=task.id,
            workspace_id=task.workspace_id,
            project_id=task.project_id,
            actor_id=creator_id,
            action=ActivityAction.TASK_CREATED,
            new_value=title,
        )

        # Reload with eager-loaded associations
        loaded = await self._task_repo.get_by_id_with_details(task.id)
        assert loaded is not None

        # Publish event after successful DB operation
        await self._publisher.publish(
            RealtimeEvent(
                channel=f"project:{loaded.project_id}",
                event_type="task.created",
                payload={"task_id": str(loaded.id), "title": loaded.title},
                exclude_user_id=creator_id,
            )
        )

        return loaded

    async def list_tasks(
        self,
        project_id: UUID,
        user_id: UUID,
        filters: TaskFilters,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Task], int]:
        await self._auth.require_project_member(user_id, project_id)
        return await self._task_repo.list_for_project(
            project_id, filters, offset=offset, limit=limit
        )

    async def get_task(self, task_id: UUID, user_id: UUID) -> Task:
        task = await self._task_repo.get_by_id_with_details(task_id)
        if task is None:
            raise NotFoundError("Task", str(task_id))
        await self._auth.can_read_task(user_id, task)
        return task

    async def update_task(
        self,
        task_id: UUID,
        user_id: UUID,
        expected_version: int,
        title: str | None = None,
        description: str | object | None = UNSET,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        assignee_id: UUID | None = None,
        due_date: date | None = None,
    ) -> Task:
        """Update task with optimistic concurrency check.

        The caller MUST supply the version they last read. If another
        update has incremented the version in the meantime, an
        OptimisticLockError is raised (HTTP 409). The client must
        re-fetch and retry with the current version.
        """
        task = await self._task_repo.get_by_id_with_details(task_id)
        if task is None:
            raise NotFoundError("Task", str(task_id))
        await self._auth.can_update_task(user_id, task)

        updates: dict[str, object] = {}
        activity_entries: list[tuple[ActivityAction, str | None, str | None]] = []

        if title is not None and title != task.title:
            activity_entries.append((ActivityAction.TITLE_CHANGED, task.title, title))
            updates["title"] = title

        if description is not UNSET and description != task.description:
            activity_entries.append(
                (ActivityAction.DESCRIPTION_CHANGED, task.description, description)  # type: ignore[arg-type]
            )
            updates["description"] = description

        if status is not None and status != task.status:
            activity_entries.append(
                (ActivityAction.STATUS_CHANGED, task.status.value, status.value)
            )
            updates["status"] = status

        if priority is not None and priority != task.priority:
            activity_entries.append(
                (ActivityAction.PRIORITY_CHANGED, task.priority.value, priority.value)
            )
            updates["priority"] = priority

        if assignee_id is not None and assignee_id != task.assignee_id:
            if task.assignee_id is None:
                activity_entries.append(
                    (ActivityAction.ASSIGNED, None, str(assignee_id))
                )
            else:
                activity_entries.append(
                    (ActivityAction.ASSIGNED, str(task.assignee_id), str(assignee_id))
                )
            updates["assignee_id"] = assignee_id

        if due_date is not None and due_date != task.due_date:
            activity_entries.append(
                (
                    ActivityAction.DUE_DATE_SET,
                    str(task.due_date) if task.due_date else None,
                    str(due_date),
                )
            )
            updates["due_date"] = due_date

        if not updates:
            return task  # No-op — return current state

        # Atomic update with version check
        success = await self._task_repo.update_with_version_check(
            task_id, expected_version, updates
        )
        if not success:
            raise OptimisticLockError("Task")

        # Record activity entries in same transaction
        for action, old_val, new_val in activity_entries:
            await self._activity_repo.create(
                task_id=task_id,
                workspace_id=task.workspace_id,
                project_id=task.project_id,
                actor_id=user_id,
                action=action,
                old_value=old_val,
                new_value=new_val,
            )

        # Reload fresh state
        updated = await self._task_repo.get_by_id_with_details(task_id)
        assert updated is not None

        # Publish event after successful DB operation
        await self._publisher.publish(
            RealtimeEvent(
                channel=f"project:{updated.project_id}",
                event_type="task.updated",
                payload={"task_id": str(task_id)},
                exclude_user_id=user_id,
            )
        )

        return updated

    async def delete_task(self, task_id: UUID, user_id: UUID) -> None:
        task = await self._task_repo.get_by_id_with_details(task_id)
        if task is None:
            raise NotFoundError("Task", str(task_id))
        await self._auth.can_delete_task(user_id, task)

        project_id = task.project_id
        await self._task_repo.delete(task)

        # Publish event after successful DB operation
        await self._publisher.publish(
            RealtimeEvent(
                channel=f"project:{project_id}",
                event_type="task.deleted",
                payload={"task_id": str(task_id)},
                exclude_user_id=user_id,
            )
        )

    async def add_label(self, task_id: UUID, label_id: UUID, user_id: UUID) -> Task:
        task = await self._task_repo.get_by_id_with_details(task_id)
        if task is None:
            raise NotFoundError("Task", str(task_id))
        await self._auth.can_update_task(user_id, task)
        await self._task_repo.add_label(task_id, label_id)
        await self._activity_repo.create(
            task_id=task_id,
            workspace_id=task.workspace_id,
            project_id=task.project_id,
            actor_id=user_id,
            action=ActivityAction.LABEL_ADDED,
            new_value=str(label_id),
        )
        self._task_repo.session.expire(task)
        loaded = await self._task_repo.get_by_id_with_details(task_id)
        assert loaded is not None
        return loaded

    async def remove_label(self, task_id: UUID, label_id: UUID, user_id: UUID) -> Task:
        task = await self._task_repo.get_by_id_with_details(task_id)
        if task is None:
            raise NotFoundError("Task", str(task_id))
        await self._auth.can_update_task(user_id, task)
        await self._task_repo.remove_label(task_id, label_id)
        await self._activity_repo.create(
            task_id=task_id,
            workspace_id=task.workspace_id,
            project_id=task.project_id,
            actor_id=user_id,
            action=ActivityAction.LABEL_REMOVED,
            old_value=str(label_id),
        )
        self._task_repo.session.expire(task)
        loaded = await self._task_repo.get_by_id_with_details(task_id)
        assert loaded is not None
        return loaded

    async def list_activity(
        self,
        task_id: UUID,
        user_id: UUID,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[ActivityLog], int]:
        task = await self._task_repo.get_by_id_with_details(task_id)
        if task is None:
            raise NotFoundError("Task", str(task_id))
        await self._auth.can_read_task(user_id, task)
        return await self._activity_repo.list_for_task(
            task_id, offset=offset, limit=limit
        )
