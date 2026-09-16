"""Task endpoints with filtering, sorting, pagination, and OCC."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from app.api.v1.schemas.common import PaginatedResponse
from app.api.v1.schemas.schemas import (
    ActivityLogResponse,
    TaskCreate,
    TaskLabelRequest,
    TaskResponse,
    TaskUpdate,
)
from app.core.dependencies import CurrentUserId, DbSession, Pagination
from app.domain.enums import TaskPriority, TaskStatus
from app.repositories.activity_repository import ActivityRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.task_repository import TaskFilters, TaskRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.services.authorization import AuthorizationService
from app.services.task_service import UNSET, TaskService

router = APIRouter(tags=["tasks"])


def _make_service(session: DbSession) -> TaskService:
    ws_repo = WorkspaceRepository(session)
    proj_repo = ProjectRepository(session)
    task_repo = TaskRepository(session)
    activity_repo = ActivityRepository(session)
    auth = AuthorizationService(ws_repo, proj_repo)
    return TaskService(task_repo, proj_repo, ws_repo, activity_repo, auth)


@router.post(
    "/projects/{project_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_task(
    project_id: UUID,
    payload: TaskCreate,
    user_id: CurrentUserId,
    session: DbSession,
) -> TaskResponse:
    svc = _make_service(session)
    task = await svc.create_task(
        project_id=project_id,
        creator_id=user_id,
        title=payload.title,
        description=payload.description,
        status=payload.status,
        priority=payload.priority,
        assignee_id=payload.assignee_id,
        due_date=payload.due_date,
        label_ids=payload.label_ids,
    )
    return TaskResponse.model_validate(task)


@router.get(
    "/projects/{project_id}/tasks",
    response_model=PaginatedResponse[TaskResponse],
)
async def list_tasks(
    project_id: UUID,
    user_id: CurrentUserId,
    session: DbSession,
    pagination: Pagination,
    status: Annotated[list[TaskStatus], Query()] = [],  # noqa: B006
    priority: Annotated[list[TaskPriority], Query()] = [],  # noqa: B006
    assignee_id: UUID | None = None,
    label_ids: Annotated[list[UUID], Query()] = [],  # noqa: B006
    search: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> PaginatedResponse[TaskResponse]:
    svc = _make_service(session)
    filters = TaskFilters(
        status=list(status),
        priority=list(priority),
        assignee_id=assignee_id,
        label_ids=list(label_ids),
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    tasks, total = await svc.list_tasks(
        project_id, user_id, filters, offset=pagination.offset, limit=pagination.limit
    )
    return PaginatedResponse.create(
        items=[TaskResponse.model_validate(t) for t in tasks],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    user_id: CurrentUserId,
    session: DbSession,
) -> TaskResponse:
    svc = _make_service(session)
    task = await svc.get_task(task_id, user_id)
    return TaskResponse.model_validate(task)


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    payload: TaskUpdate,
    user_id: CurrentUserId,
    session: DbSession,
) -> TaskResponse:
    svc = _make_service(session)
    task = await svc.update_task(
        task_id=task_id,
        user_id=user_id,
        expected_version=payload.version,
        title=payload.title,
        description=payload.description
        if "description" in payload.model_fields_set
        else UNSET,
        status=payload.status,
        priority=payload.priority,
        assignee_id=payload.assignee_id,
        due_date=payload.due_date,
    )
    return TaskResponse.model_validate(task)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID,
    user_id: CurrentUserId,
    session: DbSession,
) -> Response:
    svc = _make_service(session)
    await svc.delete_task(task_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/tasks/{task_id}/labels",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
)
async def add_task_label(
    task_id: UUID,
    payload: TaskLabelRequest,
    user_id: CurrentUserId,
    session: DbSession,
) -> TaskResponse:
    svc = _make_service(session)
    task = await svc.add_label(task_id, payload.label_id, user_id)
    return TaskResponse.model_validate(task)


@router.delete(
    "/tasks/{task_id}/labels/{label_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
)
async def remove_task_label(
    task_id: UUID,
    label_id: UUID,
    user_id: CurrentUserId,
    session: DbSession,
) -> TaskResponse:
    svc = _make_service(session)
    task = await svc.remove_label(task_id, label_id, user_id)
    return TaskResponse.model_validate(task)


@router.get(
    "/tasks/{task_id}/activity",
    response_model=PaginatedResponse[ActivityLogResponse],
)
async def get_task_activity(
    task_id: UUID,
    user_id: CurrentUserId,
    session: DbSession,
    pagination: Pagination,
) -> PaginatedResponse[ActivityLogResponse]:
    svc = _make_service(session)
    logs, total = await svc.list_activity(
        task_id, user_id, offset=pagination.offset, limit=pagination.limit
    )
    return PaginatedResponse.create(
        items=[ActivityLogResponse.model_validate(a) for a in logs],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )
