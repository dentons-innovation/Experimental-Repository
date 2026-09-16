"""Workspace endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Response, status

from app.api.v1.schemas.common import PaginatedResponse
from app.api.v1.schemas.schemas import (
    AddWorkspaceMemberRequest,
    WorkspaceCreate,
    WorkspaceMemberResponse,
    WorkspaceResponse,
    WorkspaceUpdate,
)
from app.core.dependencies import CurrentUserId, DbSession, Pagination
from app.repositories.project_repository import ProjectRepository
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.services.authorization import AuthorizationService
from app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def _make_service(session: DbSession) -> WorkspaceService:
    ws_repo = WorkspaceRepository(session)
    proj_repo = ProjectRepository(session)
    user_repo = UserRepository(session)
    auth = AuthorizationService(ws_repo, proj_repo)
    return WorkspaceService(ws_repo, user_repo, auth)


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    payload: WorkspaceCreate,
    user_id: CurrentUserId,
    session: DbSession,
) -> WorkspaceResponse:
    svc = _make_service(session)
    ws = await svc.create_workspace(
        owner_id=user_id,
        name=payload.name,
        description=payload.description,
        slug=payload.slug,
    )
    return WorkspaceResponse.model_validate(ws)


@router.get("", response_model=PaginatedResponse[WorkspaceResponse])
async def list_workspaces(
    user_id: CurrentUserId,
    session: DbSession,
    pagination: Pagination,
) -> PaginatedResponse[WorkspaceResponse]:
    svc = _make_service(session)
    workspaces, total = await svc.list_workspaces(
        user_id, offset=pagination.offset, limit=pagination.limit
    )
    return PaginatedResponse.create(
        items=[WorkspaceResponse.model_validate(w) for w in workspaces],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: UUID,
    user_id: CurrentUserId,
    session: DbSession,
) -> WorkspaceResponse:
    svc = _make_service(session)
    ws = await svc.get_workspace(workspace_id, user_id)
    return WorkspaceResponse.model_validate(ws)


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: UUID,
    payload: WorkspaceUpdate,
    user_id: CurrentUserId,
    session: DbSession,
) -> WorkspaceResponse:
    svc = _make_service(session)
    ws = await svc.update_workspace(
        workspace_id, user_id, name=payload.name, description=payload.description
    )
    return WorkspaceResponse.model_validate(ws)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: UUID,
    user_id: CurrentUserId,
    session: DbSession,
) -> Response:
    svc = _make_service(session)
    await svc.delete_workspace(workspace_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{workspace_id}/members", response_model=list[WorkspaceMemberResponse])
async def list_workspace_members(
    workspace_id: UUID,
    user_id: CurrentUserId,
    session: DbSession,
) -> list[WorkspaceMemberResponse]:
    svc = _make_service(session)
    members = await svc.list_members(workspace_id, user_id)
    return [WorkspaceMemberResponse.model_validate(m) for m in members]


@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_workspace_member(
    workspace_id: UUID,
    payload: AddWorkspaceMemberRequest,
    user_id: CurrentUserId,
    session: DbSession,
) -> WorkspaceMemberResponse:
    svc = _make_service(session)
    member = await svc.add_member(workspace_id, user_id, payload.user_id, payload.role)
    return WorkspaceMemberResponse.model_validate(member)


@router.delete(
    "/{workspace_id}/members/{target_user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_workspace_member(
    workspace_id: UUID,
    target_user_id: UUID,
    user_id: CurrentUserId,
    session: DbSession,
) -> Response:
    svc = _make_service(session)
    await svc.remove_member(workspace_id, user_id, target_user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
