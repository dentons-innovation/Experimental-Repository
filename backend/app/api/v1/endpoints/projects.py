"""Project endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Response, status

from app.api.v1.schemas.common import PaginatedResponse
from app.api.v1.schemas.schemas import (
    AddProjectMemberRequest,
    ProjectCreate,
    ProjectMemberResponse,
    ProjectResponse,
    ProjectUpdate,
    UpdateProjectMemberRequest,
)
from app.core.dependencies import CurrentUserId, DbSession, Pagination
from app.core.realtime_deps import get_event_publisher
from app.infrastructure.realtime.publisher import RealtimeEventPublisher
from app.repositories.project_repository import ProjectRepository
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.services.authorization import AuthorizationService
from app.services.project_service import UNSET, ProjectService
from fastapi import Depends

router = APIRouter(tags=["projects"])


def _make_service(
    session: DbSession, publisher: RealtimeEventPublisher
) -> ProjectService:
    ws_repo = WorkspaceRepository(session)
    proj_repo = ProjectRepository(session)
    user_repo = UserRepository(session)
    auth = AuthorizationService(ws_repo, proj_repo)
    return ProjectService(proj_repo, ws_repo, user_repo, auth, publisher)


@router.post(
    "/workspaces/{workspace_id}/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    workspace_id: UUID,
    payload: ProjectCreate,
    user_id: CurrentUserId,
    session: DbSession,
    publisher: RealtimeEventPublisher = Depends(get_event_publisher),
) -> ProjectResponse:
    svc = _make_service(session, publisher)
    project = await svc.create_project(
        workspace_id=workspace_id,
        creator_id=user_id,
        name=payload.name,
        description=payload.description,
        slug=payload.slug,
    )
    return ProjectResponse.model_validate(project)


@router.get(
    "/workspaces/{workspace_id}/projects",
    response_model=PaginatedResponse[ProjectResponse],
)
async def list_projects(
    workspace_id: UUID,
    user_id: CurrentUserId,
    session: DbSession,
    pagination: Pagination,
    publisher: RealtimeEventPublisher = Depends(get_event_publisher),
) -> PaginatedResponse[ProjectResponse]:
    svc = _make_service(session, publisher)
    projects, total = await svc.list_projects(
        workspace_id, user_id, offset=pagination.offset, limit=pagination.limit
    )
    return PaginatedResponse.create(
        items=[ProjectResponse.model_validate(p) for p in projects],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    user_id: CurrentUserId,
    session: DbSession,
    publisher: RealtimeEventPublisher = Depends(get_event_publisher),
) -> ProjectResponse:
    svc = _make_service(session, publisher)
    project = await svc.get_project(project_id, user_id)
    return ProjectResponse.model_validate(project)


@router.patch("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    payload: ProjectUpdate,
    user_id: CurrentUserId,
    session: DbSession,
    publisher: RealtimeEventPublisher = Depends(get_event_publisher),
) -> ProjectResponse:
    svc = _make_service(session, publisher)
    project = await svc.update_project(
        project_id,
        user_id,
        name=payload.name,
        description=payload.description
        if "description" in payload.model_fields_set
        else UNSET,
    )
    return ProjectResponse.model_validate(project)


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    user_id: CurrentUserId,
    session: DbSession,
    publisher: RealtimeEventPublisher = Depends(get_event_publisher),
) -> Response:
    svc = _make_service(session, publisher)
    await svc.delete_project(project_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/projects/{project_id}/members",
    response_model=list[ProjectMemberResponse],
)
async def list_project_members(
    project_id: UUID,
    user_id: CurrentUserId,
    session: DbSession,
    publisher: RealtimeEventPublisher = Depends(get_event_publisher),
) -> list[ProjectMemberResponse]:
    svc = _make_service(session, publisher)
    members = await svc.list_members(project_id, user_id)
    return [ProjectMemberResponse.model_validate(m) for m in members]


@router.post(
    "/projects/{project_id}/members",
    response_model=ProjectMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_project_member(
    project_id: UUID,
    payload: AddProjectMemberRequest,
    user_id: CurrentUserId,
    session: DbSession,
    publisher: RealtimeEventPublisher = Depends(get_event_publisher),
) -> ProjectMemberResponse:
    svc = _make_service(session, publisher)
    member = await svc.add_member(project_id, user_id, payload.user_id, payload.role)
    return ProjectMemberResponse.model_validate(member)


@router.delete(
    "/projects/{project_id}/members/{target_user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_project_member(
    project_id: UUID,
    target_user_id: UUID,
    user_id: CurrentUserId,
    session: DbSession,
    publisher: RealtimeEventPublisher = Depends(get_event_publisher),
) -> Response:
    svc = _make_service(session, publisher)
    await svc.remove_member(project_id, user_id, target_user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put(
    "/projects/{project_id}/members/{target_user_id}",
    response_model=ProjectMemberResponse,
)
async def update_project_member_role(
    project_id: UUID,
    target_user_id: UUID,
    payload: UpdateProjectMemberRequest,
    user_id: CurrentUserId,
    session: DbSession,
    publisher: RealtimeEventPublisher = Depends(get_event_publisher),
) -> ProjectMemberResponse:
    svc = _make_service(session, publisher)
    member = await svc.update_member_role(
        project_id=project_id,
        requester_id=user_id,
        target_user_id=target_user_id,
        new_role=payload.role,
    )
    return ProjectMemberResponse.model_validate(member)
