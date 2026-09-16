"""Label endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Response, status

from app.api.v1.schemas.schemas import LabelCreate, LabelResponse, LabelUpdate
from app.core.dependencies import CurrentUserId, DbSession
from app.repositories.label_repository import LabelRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.services.authorization import AuthorizationService
from app.services.label_service import LabelService

router = APIRouter(tags=["labels"])


def _make_service(session: DbSession) -> LabelService:
    ws_repo = WorkspaceRepository(session)
    proj_repo = ProjectRepository(session)
    label_repo = LabelRepository(session)
    auth = AuthorizationService(ws_repo, proj_repo)
    return LabelService(label_repo, ws_repo, auth)


@router.post(
    "/workspaces/{workspace_id}/labels",
    response_model=LabelResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_label(
    workspace_id: UUID,
    payload: LabelCreate,
    user_id: CurrentUserId,
    session: DbSession,
) -> LabelResponse:
    svc = _make_service(session)
    label = await svc.create_label(workspace_id, user_id, payload.name, payload.color)
    return LabelResponse.model_validate(label)


@router.get("/workspaces/{workspace_id}/labels", response_model=list[LabelResponse])
async def list_labels(
    workspace_id: UUID,
    user_id: CurrentUserId,
    session: DbSession,
) -> list[LabelResponse]:
    svc = _make_service(session)
    labels = await svc.list_labels(workspace_id, user_id)
    return [LabelResponse.model_validate(la) for la in labels]


@router.patch("/labels/{label_id}", response_model=LabelResponse)
async def update_label(
    label_id: UUID,
    payload: LabelUpdate,
    user_id: CurrentUserId,
    session: DbSession,
) -> LabelResponse:
    svc = _make_service(session)
    label = await svc.update_label(
        label_id, user_id, name=payload.name, color=payload.color
    )
    return LabelResponse.model_validate(label)


@router.delete("/labels/{label_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_label(
    label_id: UUID,
    user_id: CurrentUserId,
    session: DbSession,
) -> Response:
    svc = _make_service(session)
    await svc.delete_label(label_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
