"""Unit tests for TaskService — mocked repositories."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.domain.enums import TaskPriority, TaskStatus
from app.domain.exceptions import NotFoundError, OptimisticLockError
from app.domain.models import Project, Task
from app.infrastructure.realtime.publisher import NoOpEventPublisher
from app.repositories.task_repository import TaskFilters
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
    task_repo.remove_label = AsyncMock()
    task_repo.list_for_project = AsyncMock(
        return_value=([task] if task else [], 1 if task else 0)
    )
    task_repo.session = MagicMock()
    task_repo.session.add = MagicMock()
    task_repo.session.flush = AsyncMock()
    task_repo.session.refresh = AsyncMock()

    proj_repo = MagicMock()
    proj_repo.get_by_id_with_members = AsyncMock(return_value=project)

    ws_repo = MagicMock()
    activity_repo = MagicMock()
    activity_repo.create = AsyncMock()
    activity_repo.list_for_task = AsyncMock(return_value=([], 0))

    auth = MagicMock()
    auth.can_read_task = AsyncMock()
    auth.can_create_task = AsyncMock()
    auth.can_update_task = AsyncMock()
    auth.can_delete_task = AsyncMock()
    auth.require_project_member = AsyncMock(return_value=MagicMock())

    return TaskService(
        task_repo, proj_repo, ws_repo, activity_repo, auth, NoOpEventPublisher()
    )


class TestCreateTask:
    async def test_create_task_success_with_labels(self):
        project = _make_project()
        created_task = _make_task(
            project_id=project.id, workspace_id=project.workspace_id
        )
        svc = _make_service(task=created_task, project=project)

        label_id = uuid4()
        result = await svc.create_task(
            project_id=project.id,
            creator_id=uuid4(),
            title="Created with label",
            label_ids=[label_id],
        )

        assert result == created_task
        svc._auth.can_create_task.assert_called_once()
        svc._task_repo.add_label.assert_called_once()
        svc._activity_repo.create.assert_called_once()

    async def test_create_task_missing_project_raises_404(self):
        svc = _make_service(project=None)
        with pytest.raises(NotFoundError):
            await svc.create_task(
                project_id=uuid4(),
                creator_id=uuid4(),
                title="Fail",
            )


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

    async def test_update_all_fields_records_activity(self):
        from datetime import date

        task = _make_task(version=0)
        task.title = "Old Title"
        task.description = "Old Desc"
        task.status = TaskStatus.BACKLOG
        task.priority = TaskPriority.LOW
        old_assignee = uuid4()
        task.assignee_id = old_assignee
        task.due_date = date(2026, 1, 1)

        updated_task = _make_task(version=1)
        svc = _make_service(task=task, version_check_result=True)
        svc._task_repo.get_by_id_with_details.side_effect = [task, updated_task]

        new_assignee = uuid4()
        new_due_date = date(2026, 12, 31)

        result = await svc.update_task(
            task_id=task.id,
            user_id=uuid4(),
            expected_version=0,
            title="New Title",
            description="New Desc",
            status=TaskStatus.DONE,
            priority=TaskPriority.CRITICAL,
            assignee_id=new_assignee,
            due_date=new_due_date,
        )
        assert result == updated_task
        assert svc._activity_repo.create.call_count == 6

    async def test_update_assignee_from_none(self):
        task = _make_task(version=0)
        task.assignee_id = None
        updated_task = _make_task(version=1)
        svc = _make_service(task=task, version_check_result=True)
        svc._task_repo.get_by_id_with_details.side_effect = [task, updated_task]

        new_assignee = uuid4()
        result = await svc.update_task(
            task_id=task.id,
            user_id=uuid4(),
            expected_version=0,
            assignee_id=new_assignee,
        )
        assert result == updated_task
        svc._activity_repo.create.assert_called_once()


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


class TestTaskLabels:
    async def test_add_label_success(self):
        task = _make_task()
        svc = _make_service(task=task)
        label_id = uuid4()
        result = await svc.add_label(task.id, label_id, uuid4())
        assert result == task
        svc._task_repo.add_label.assert_called_once_with(task.id, label_id)
        svc._activity_repo.create.assert_called_once()

    async def test_add_label_missing_task_raises_404(self):
        svc = _make_service(task=None)
        with pytest.raises(NotFoundError):
            await svc.add_label(uuid4(), uuid4(), uuid4())

    async def test_remove_label_success(self):
        task = _make_task()
        svc = _make_service(task=task)
        label_id = uuid4()
        result = await svc.remove_label(task.id, label_id, uuid4())
        assert result == task
        svc._task_repo.remove_label.assert_called_once_with(task.id, label_id)
        svc._activity_repo.create.assert_called_once()

    async def test_remove_label_missing_task_raises_404(self):
        svc = _make_service(task=None)
        with pytest.raises(NotFoundError):
            await svc.remove_label(uuid4(), uuid4(), uuid4())


class TestListTasks:
    async def test_list_tasks_success(self):

        task = _make_task()
        svc = _make_service(task=task)
        filters = TaskFilters(status=[TaskStatus.TODO])
        tasks, total = await svc.list_tasks(task.project_id, uuid4(), filters)
        assert tasks == [task]
        assert total == 1
        svc._auth.require_project_member.assert_called_once()


class TestTaskActivity:
    async def test_list_activity_success(self):
        task = _make_task()
        svc = _make_service(task=task)
        logs, total = await svc.list_activity(task.id, uuid4())
        assert logs == []
        assert total == 0
        svc._auth.can_read_task.assert_called_once()

    async def test_list_activity_missing_task_raises_404(self):
        svc = _make_service(task=None)
        with pytest.raises(NotFoundError):
            await svc.list_activity(uuid4(), uuid4())
