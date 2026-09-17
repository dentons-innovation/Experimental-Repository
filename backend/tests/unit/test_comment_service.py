"""Unit tests for CommentService — task comments and activity tracking."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.domain.exceptions import NotFoundError
from app.domain.models import Comment, Task
from app.infrastructure.realtime.publisher import NoOpEventPublisher
from app.services.comment_service import CommentService


def _make_comment(task_id=None, author_id=None) -> Comment:
    c = MagicMock(spec=Comment)
    c.id = uuid4()
    c.task_id = task_id or uuid4()
    c.author_id = author_id or uuid4()
    c.body = "A comment"
    c.is_edited = False
    return c


def _make_service(
    comment: Comment | None = None,
    task: Task | None = None,
) -> CommentService:
    comment_repo = MagicMock()
    comment_repo.get_by_id_with_author = AsyncMock(return_value=comment)
    comment_repo.list_for_task = AsyncMock(
        return_value=([comment] if comment else [], 1 if comment else 0)
    )
    comment_repo.delete = AsyncMock()
    comment_repo.session = MagicMock()
    comment_repo.session.add = MagicMock()
    comment_repo.session.flush = AsyncMock()
    comment_repo.session.refresh = AsyncMock()

    task_repo = MagicMock()
    task_repo.get_by_id_with_details = AsyncMock(return_value=task)

    activity_repo = MagicMock()
    activity_repo.create = AsyncMock()

    auth = MagicMock()
    auth.can_create_comment = AsyncMock()
    auth.can_read_task = AsyncMock()
    auth.can_edit_comment = AsyncMock()
    auth.can_delete_comment = AsyncMock()

    return CommentService(
        comment_repo, task_repo, activity_repo, auth, NoOpEventPublisher()
    )


class TestCommentService:
    async def test_create_comment_success(self):
        task = MagicMock(spec=Task)
        task.id = uuid4()
        task.workspace_id = uuid4()
        task.project_id = uuid4()
        comment = _make_comment(task_id=task.id)

        svc = _make_service(comment=comment, task=task)
        result = await svc.create_comment(task.id, uuid4(), "Great job")
        assert result == comment
        svc._comment_repo.session.add.assert_called_once()
        svc._activity_repo.create.assert_called_once()

    async def test_create_comment_task_not_found(self):
        svc = _make_service(task=None)
        with pytest.raises(NotFoundError):
            await svc.create_comment(uuid4(), uuid4(), "Hello")

    async def test_list_comments_success(self):
        task = MagicMock(spec=Task)
        task.id = uuid4()
        comment = _make_comment(task_id=task.id)

        svc = _make_service(comment=comment, task=task)
        comments, total = await svc.list_comments(task.id, uuid4())
        assert comments == [comment]
        assert total == 1

    async def test_list_comments_task_not_found(self):
        svc = _make_service(task=None)
        with pytest.raises(NotFoundError):
            await svc.list_comments(uuid4(), uuid4())

    async def test_update_comment_success(self):
        task = MagicMock(spec=Task)
        task.id = uuid4()
        task.workspace_id = uuid4()
        task.project_id = uuid4()
        comment = _make_comment(task_id=task.id)

        svc = _make_service(comment=comment, task=task)
        result = await svc.update_comment(comment.id, comment.author_id, "Edited text")
        assert result == comment
        assert comment.body == "Edited text"
        assert comment.is_edited is True
        svc._activity_repo.create.assert_called_once()

    async def test_update_comment_not_found(self):
        svc = _make_service(comment=None)
        with pytest.raises(NotFoundError):
            await svc.update_comment(uuid4(), uuid4(), "Updated")

    async def test_update_comment_task_not_found(self):
        comment = _make_comment()
        svc = _make_service(comment=comment, task=None)
        with pytest.raises(NotFoundError):
            await svc.update_comment(comment.id, uuid4(), "Updated")

    async def test_delete_comment_success(self):
        task = MagicMock(spec=Task)
        task.id = uuid4()
        task.workspace_id = uuid4()
        task.project_id = uuid4()
        comment = _make_comment(task_id=task.id)

        svc = _make_service(comment=comment, task=task)
        await svc.delete_comment(comment.id, comment.author_id)
        svc._comment_repo.delete.assert_called_once_with(comment)
        svc._activity_repo.create.assert_called_once()

    async def test_delete_comment_not_found(self):
        svc = _make_service(comment=None)
        with pytest.raises(NotFoundError):
            await svc.delete_comment(uuid4(), uuid4())

    async def test_delete_comment_task_not_found(self):
        comment = _make_comment()
        svc = _make_service(comment=comment, task=None)
        with pytest.raises(NotFoundError):
            await svc.delete_comment(comment.id, uuid4())
