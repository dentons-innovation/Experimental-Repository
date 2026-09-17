"""Comment service."""

from __future__ import annotations

import asyncio
from uuid import UUID

from sqlalchemy import event as sa_event
from sqlalchemy.orm import Session as SASession

from app.domain.enums import ActivityAction
from app.domain.exceptions import NotFoundError
from app.domain.models import Comment
from app.infrastructure.realtime.publisher import RealtimeEventPublisher
from app.infrastructure.realtime.types import RealtimeEvent
from app.repositories.activity_repository import ActivityRepository
from app.repositories.comment_repository import CommentRepository
from app.repositories.task_repository import TaskRepository
from app.services.authorization import AuthorizationService

_background_tasks: set[asyncio.Task[None]] = set()


class CommentService:
    def __init__(
        self,
        comment_repo: CommentRepository,
        task_repo: TaskRepository,
        activity_repo: ActivityRepository,
        auth_service: AuthorizationService,
        publisher: RealtimeEventPublisher,
    ) -> None:
        self._comment_repo = comment_repo
        self._task_repo = task_repo
        self._activity_repo = activity_repo
        self._auth = auth_service
        self._publisher = publisher

    async def _publish_after_commit(self, event: RealtimeEvent) -> None:
        session = getattr(self._comment_repo, "session", None)
        sync_session = getattr(session, "sync_session", None)
        if (
            isinstance(sync_session, SASession)
            and hasattr(sync_session, "is_active")
            and sync_session.is_active
        ):
            loop = asyncio.get_running_loop()
            pub = self._publisher

            def _on_commit() -> None:
                t = loop.create_task(pub.publish(event))
                _background_tasks.add(t)
                t.add_done_callback(_background_tasks.discard)

            sa_event.listen(sync_session, "after_commit", _on_commit, once=True)
        else:
            await self._publisher.publish(event)

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

        # Publish event after successful DB commit
        await self._publish_after_commit(
            RealtimeEvent(
                channel=f"project:{task.project_id}",
                event_type="comment.created",
                payload={
                    "comment_id": str(loaded.id),
                    "task_id": str(task_id),
                },
                exclude_user_id=author_id,
            )
        )

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

        loaded = await self._comment_repo.get_by_id_with_author(comment.id)
        assert loaded is not None

        # Publish event after successful DB commit
        await self._publish_after_commit(
            RealtimeEvent(
                channel=f"project:{task.project_id}",
                event_type="comment.updated",
                payload={
                    "comment_id": str(loaded.id),
                    "task_id": str(task.id),
                },
                exclude_user_id=user_id,
            )
        )

        return loaded

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

        # Publish event after successful DB commit
        await self._publish_after_commit(
            RealtimeEvent(
                channel=f"project:{task.project_id}",
                event_type="comment.deleted",
                payload={
                    "comment_id": str(comment_id),
                    "task_id": str(task.id),
                },
                exclude_user_id=user_id,
            )
        )
