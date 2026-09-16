"""Unit tests for TaskService — mocked repositories."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.domain.enums import TaskPriority, TaskStatus
from app.domain.exceptions import NotFoundError, OptimisticLockError
from app.domain.models import Project, Task
from app.services.task_service import TaskService


def _make_task(project_id=None, workspace_id=None, version=0) -> Task:
    task = MagicMock(spec=Task)
    task.id = uuid4()
    task.project_id = project_id or uuid4()
    task.workspace_id = workspace_id or uuid4()
    task.version = version
    task.status = TaskStatus.BACKLOG
    task.priority = TaskPriority.MEDIUM
    task.title = "Test Task"
    task.description = None
    task.assignee_id = None
    task.due_date = None
    return task


def _make_project() -> Project:
    project = MagicMock(spec=Project)
    project.id = uuid4()
    project.workspace_id = uuid4()
    return project


def _make_service(
    task: Task | None = None,
    project: Project | None = None,
    version_check_result: bool = True,
) -> TaskService:
    task_repo = MagicMock()
    task_repo.get_by_id_with_details = AsyncMock(return_value=task)
    task_repo.update_with_version_check = AsyncMock(return_value=version_check_result)
    task_repo.add_label = AsyncMock()
    task_repo.session = MagicMock()
    task_repo.session.add = MagicMock()
    task_repo.session.flush = AsyncMock()
    task_repo.session.refresh = AsyncMock()

    proj_repo = MagicMock()
    proj_repo.get_by_id_with_members = AsyncMock(return_value=project)

    ws_repo = MagicMock()
    activity_repo = MagicMock()
    activity_repo.create = AsyncMock()

    auth = MagicMock()
    auth.can_read_task = AsyncMock()
    auth.can_create_task = AsyncMock()
    auth.can_update_task = AsyncMock()
    auth.can_delete_task = AsyncMock()
    auth.require_project_member = AsyncMock(return_value=MagicMock())

    return TaskService(task_repo, proj_repo, ws_repo, activity_repo, auth)


class TestGetTask:
    async def test_get_existing_task(self):
        task = _make_task()
        svc = _make_service(task=task)
        result = await svc.get_task(task.id, uuid4())
        assert result == task

    async def test_get_missing_task_raises_404(self):
        svc = _make_service(task=None)
        with pytest.raises(NotFoundError):
            await svc.get_task(uuid4(), uuid4())


class TestUpdateTask:
    async def test_successful_update(self):
        task = _make_task(version=0)
        updated_task = _make_task(version=1)
        svc = _make_service(task=task, version_check_result=True)
        # Second call returns the updated task
        svc._task_repo.get_by_id_with_details.side_effect = [task, updated_task]

        result = await svc.update_task(
            task_id=task.id,
            user_id=uuid4(),
            expected_version=0,
            title="New Title",
        )
        assert result == updated_task

    async def test_optimistic_lock_error_on_version_mismatch(self):
        task = _make_task(version=2)
        svc = _make_service(task=task, version_check_result=False)

        with pytest.raises(OptimisticLockError):
            await svc.update_task(
                task_id=task.id,
                user_id=uuid4(),
                expected_version=0,  # stale version
                title="New Title",
            )

    async def test_noop_update_returns_current_task(self):
        task = _make_task()
        svc = _make_service(task=task, version_check_result=True)

        # No changes
        result = await svc.update_task(
            task_id=task.id,
            user_id=uuid4(),
            expected_version=0,
        )
        assert result == task
        svc._task_repo.update_with_version_check.assert_not_called()

    async def test_missing_task_raises_404(self):
        svc = _make_service(task=None)
        with pytest.raises(NotFoundError):
            await svc.update_task(
                task_id=uuid4(),
                user_id=uuid4(),
                expected_version=0,
                title="x",
            )


class TestDeleteTask:
    async def test_delete_existing_task(self):
        task = _make_task()
        svc = _make_service(task=task)
        svc._task_repo.delete = AsyncMock()
        await svc.delete_task(task.id, uuid4())
        svc._task_repo.delete.assert_called_once_with(task)

    async def test_delete_missing_task_raises_404(self):
        svc = _make_service(task=None)
        with pytest.raises(NotFoundError):
            await svc.delete_task(uuid4(), uuid4())


class TestActivityLogging:
    async def test_status_change_creates_activity(self):
        task = _make_task(version=0)
        task.status = TaskStatus.BACKLOG
        task.priority = TaskPriority.MEDIUM
        task.title = "Original"
        updated = _make_task(version=1)
        svc = _make_service(task=task, version_check_result=True)
        svc._task_repo.get_by_id_with_details.side_effect = [task, updated]

        await svc.update_task(
            task_id=task.id,
            user_id=uuid4(),
            expected_version=0,
            status=TaskStatus.IN_PROGRESS,
        )
        svc._activity_repo.create.assert_called()
