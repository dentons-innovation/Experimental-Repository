"""Label service."""

from __future__ import annotations

from uuid import UUID

from app.domain.exceptions import ConflictError, NotFoundError
from app.domain.models import Label
from app.repositories.label_repository import LabelRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.services.authorization import AuthorizationService


class LabelService:
    def __init__(
        self,
        label_repo: LabelRepository,
        workspace_repo: WorkspaceRepository,
        auth_service: AuthorizationService,
    ) -> None:
        self._label_repo = label_repo
        self._ws_repo = workspace_repo
        self._auth = auth_service

    async def create_label(
        self,
        workspace_id: UUID,
        user_id: UUID,
        name: str,
        color: str = "#6366f1",
    ) -> Label:
        await self._auth.can_manage_labels(user_id, workspace_id)

        existing = await self._label_repo.get_by_workspace_and_name(workspace_id, name)
        if existing:
            raise ConflictError(f"Label '{name}' already exists in this workspace")

        label = Label(workspace_id=workspace_id, name=name, color=color)
        self._label_repo.session.add(label)
        await self._label_repo.session.flush()
        await self._label_repo.session.refresh(label)
        return label

    async def list_labels(
        self, workspace_id: UUID, user_id: UUID
    ) -> list[Label]:
        await self._auth.require_workspace_member(user_id, workspace_id)
        return await self._label_repo.list_for_workspace(workspace_id)

    async def update_label(
        self,
        label_id: UUID,
        user_id: UUID,
        name: str | None = None,
        color: str | None = None,
    ) -> Label:
        label = await self._label_repo.get_by_id(label_id)
        if label is None:
            raise NotFoundError("Label", str(label_id))
        await self._auth.can_manage_labels(user_id, label.workspace_id)

        if name is not None:
            # Check uniqueness
            existing = await self._label_repo.get_by_workspace_and_name(
                label.workspace_id, name
            )
            if existing and existing.id != label_id:
                raise ConflictError(f"Label '{name}' already exists")
            label.name = name
        if color is not None:
            label.color = color

        await self._label_repo.session.flush()
        return label

    async def delete_label(self, label_id: UUID, user_id: UUID) -> None:
        label = await self._label_repo.get_by_id(label_id)
        if label is None:
            raise NotFoundError("Label", str(label_id))
        await self._auth.can_delete_label(user_id, label.workspace_id)
        await self._label_repo.delete(label)
