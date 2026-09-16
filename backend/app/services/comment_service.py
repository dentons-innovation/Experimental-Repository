"""Comment service."""

from __future__ import annotations

from uuid import UUID

from app.domain.enums import ActivityAction
from app.domain.exceptions import NotFoundError
from app.domain.models import Comment
from app.repositories.activity_repository import ActivityRepository
from app.repositories.comment_repository import CommentRepository
from app.repositories.task_repository import TaskRepository
from app.services.authorization import AuthorizationService


class CommentService:
    def __init__(
        self,
        comment_repo: CommentRepository,
        task_repo: TaskRepository,
        activity_repo: ActivityRepository,
        auth_service: AuthorizationService,
    ) -> None:
        self._comment_repo = comment_repo
        self._task_repo = task_repo
        self._activity_repo = activity_repo
        self._auth = auth_service

    async def create_comment(
        self, task_id: UUID, author_id: UUID, body: str
    ) -> Comment:
        task = await self._task_repo.get_by_id_with_details(task_id)
        if task is None:
            raise NotFoundError("Task", str(task_id))
        await self._auth.can_create_comment(author_id, task)

        comment = Comment(task_id=task_id, author_id=author_id, body=body)
        self._comment_repo.session.add(comment)
        await self._comment_repo.session.flush()
        await self._comment_repo.session.refresh(comment)

        await self._activity_repo.create(
            task_id=task_id,
            workspace_id=task.workspace_id,
            project_id=task.project_id,
            actor_id=author_id,
            action=ActivityAction.COMMENT_ADDED,
        )

        loaded = await self._comment_repo.get_by_id_with_author(comment.id)
        assert loaded is not None
        return loaded

    async def list_comments(
        self, task_id: UUID, user_id: UUID, offset: int = 0, limit: int = 50
    ) -> tuple[list[Comment], int]:
        task = await self._task_repo.get_by_id_with_details(task_id)
        if task is None:
            raise NotFoundError("Task", str(task_id))
        await self._auth.can_read_task(user_id, task)
        return await self._comment_repo.list_for_task(
            task_id, offset=offset, limit=limit
        )

    async def update_comment(
        self, comment_id: UUID, user_id: UUID, body: str
    ) -> Comment:
        comment = await self._comment_repo.get_by_id_with_author(comment_id)
        if comment is None:
            raise NotFoundError("Comment", str(comment_id))

        task = await self._task_repo.get_by_id_with_details(comment.task_id)
        if task is None:
            raise NotFoundError("Task", str(comment.task_id))

        await self._auth.can_edit_comment(user_id, comment, task)

        comment.body = body
        comment.is_edited = True
        await self._comment_repo.session.flush()

        await self._activity_repo.create(
            task_id=task.id,
            workspace_id=task.workspace_id,
            project_id=task.project_id,
            actor_id=user_id,
            action=ActivityAction.COMMENT_EDITED,
        )

        return comment

    async def delete_comment(self, comment_id: UUID, user_id: UUID) -> None:
        comment = await self._comment_repo.get_by_id_with_author(comment_id)
        if comment is None:
            raise NotFoundError("Comment", str(comment_id))

        task = await self._task_repo.get_by_id_with_details(comment.task_id)
        if task is None:
            raise NotFoundError("Task", str(comment.task_id))

        await self._auth.can_delete_comment(user_id, comment, task)
        await self._comment_repo.delete(comment)

        await self._activity_repo.create(
            task_id=task.id,
            workspace_id=task.workspace_id,
            project_id=task.project_id,
            actor_id=user_id,
            action=ActivityAction.COMMENT_DELETED,
        )
