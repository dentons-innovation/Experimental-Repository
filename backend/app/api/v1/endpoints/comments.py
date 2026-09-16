"""Comment endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Response, status

from app.api.v1.schemas.common import PaginatedResponse
from app.api.v1.schemas.schemas import CommentCreate, CommentResponse, CommentUpdate
from app.core.dependencies import CurrentUserId, DbSession, Pagination
from app.repositories.activity_repository import ActivityRepository
from app.repositories.comment_repository import CommentRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.services.authorization import AuthorizationService
from app.services.comment_service import CommentService

router = APIRouter(tags=["comments"])


def _make_service(session: DbSession) -> CommentService:
    ws_repo = WorkspaceRepository(session)
    proj_repo = ProjectRepository(session)
    task_repo = TaskRepository(session)
    comment_repo = CommentRepository(session)
    activity_repo = ActivityRepository(session)
    auth = AuthorizationService(ws_repo, proj_repo)
    return CommentService(comment_repo, task_repo, activity_repo, auth)


@router.post(
    "/tasks/{task_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_comment(
    task_id: UUID,
    payload: CommentCreate,
    user_id: CurrentUserId,
    session: DbSession,
) -> CommentResponse:
    svc = _make_service(session)
    comment = await svc.create_comment(task_id, user_id, payload.body)
    return CommentResponse.model_validate(comment)


@router.get(
    "/tasks/{task_id}/comments",
    response_model=PaginatedResponse[CommentResponse],
)
async def list_comments(
    task_id: UUID,
    user_id: CurrentUserId,
    session: DbSession,
    pagination: Pagination,
) -> PaginatedResponse[CommentResponse]:
    svc = _make_service(session)
    comments, total = await svc.list_comments(
        task_id, user_id, offset=pagination.offset, limit=pagination.limit
    )
    return PaginatedResponse.create(
        items=[CommentResponse.model_validate(c) for c in comments],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.patch("/comments/{comment_id}", response_model=CommentResponse)
async def update_comment(
    comment_id: UUID,
    payload: CommentUpdate,
    user_id: CurrentUserId,
    session: DbSession,
) -> CommentResponse:
    svc = _make_service(session)
    comment = await svc.update_comment(comment_id, user_id, payload.body)
    return CommentResponse.model_validate(comment)


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: UUID,
    user_id: CurrentUserId,
    session: DbSession,
) -> Response:
    svc = _make_service(session)
    await svc.delete_comment(comment_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
