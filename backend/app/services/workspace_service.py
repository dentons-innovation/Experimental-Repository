"""Workspace service — all workspace business logic."""

from __future__ import annotations

import re
from uuid import UUID

from app.domain.enums import WorkspaceRole
from app.domain.exceptions import ConflictError, NotFoundError, ValidationError
from app.domain.models import Workspace, WorkspaceMember
from app.infrastructure.realtime.publisher import RealtimeEventPublisher
from app.infrastructure.realtime.types import RealtimeEvent
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.services.authorization import AuthorizationService


def _slugify(name: str) -> str:
    """Convert a workspace name to a URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    slug = slug.strip("-")
    return slug[:64]


UNSET: object = object()


class WorkspaceService:
    def __init__(
        self,
        workspace_repo: WorkspaceRepository,
        user_repo: UserRepository,
        auth_service: AuthorizationService,
        publisher: RealtimeEventPublisher,
    ) -> None:
        self._ws_repo = workspace_repo
        self._user_repo = user_repo
        self._auth = auth_service
        self._publisher = publisher

    async def create_workspace(
        self,
        owner_id: UUID,
        name: str,
        description: str | None = None,
        slug: str | None = None,
    ) -> Workspace:
        final_slug = slug or _slugify(name)
        if not final_slug:
            final_slug = "workspace"

        # Ensure slug is unique
        existing = await self._ws_repo.get_by_slug(final_slug)
        if existing:
            raise ConflictError(f"Workspace slug '{final_slug}' is already taken")

        workspace = Workspace(
            name=name,
            slug=final_slug,
            description=description,
            owner_id=owner_id,
        )
        self._ws_repo.session.add(workspace)
        await self._ws_repo.session.flush()
        await self._ws_repo.session.refresh(workspace)

        # Auto-add owner as OWNER member
        await self._ws_repo.add_member(workspace.id, owner_id, WorkspaceRole.OWNER)

        return workspace

    async def list_workspaces(
        self, user_id: UUID, offset: int = 0, limit: int = 20
    ) -> tuple[list[Workspace], int]:
        return await self._ws_repo.list_for_user(user_id, offset=offset, limit=limit)

    async def get_workspace(self, workspace_id: UUID, user_id: UUID) -> Workspace:
        await self._auth.require_workspace_member(user_id, workspace_id)
        workspace = await self._ws_repo.get_by_id_with_members(workspace_id)
        if workspace is None:
            raise NotFoundError("Workspace", str(workspace_id))
        return workspace

    async def update_workspace(
        self,
        workspace_id: UUID,
        user_id: UUID,
        name: str | None = None,
        description: str | object | None = UNSET,
    ) -> Workspace:
        await self._auth.require_workspace_owner(user_id, workspace_id)
        workspace = await self._ws_repo.get_by_id_with_members(workspace_id)
        if workspace is None:
            raise NotFoundError("Workspace", str(workspace_id))

        if name is not None:
            workspace.name = name
        if description is not UNSET:
            workspace.description = description  # type: ignore[assignment]

        await self._ws_repo.session.flush()
        await self._ws_repo.session.refresh(workspace)
        return workspace

    async def delete_workspace(self, workspace_id: UUID, user_id: UUID) -> None:
        await self._auth.require_workspace_owner(user_id, workspace_id)
        workspace = await self._ws_repo.get_by_id_with_members(workspace_id)
        if workspace is None:
            raise NotFoundError("Workspace", str(workspace_id))
        await self._ws_repo.delete(workspace)

    async def add_member(
        self,
        workspace_id: UUID,
        requester_id: UUID,
        target_user_id: UUID,
        role: WorkspaceRole = WorkspaceRole.MEMBER,
    ) -> WorkspaceMember:
        await self._auth.require_workspace_owner(requester_id, workspace_id)

        # Verify target user exists
        target = await self._user_repo.get_by_id(target_user_id)
        if target is None:
            raise NotFoundError("User", str(target_user_id))

        # Check for existing membership
        existing = await self._ws_repo.get_member(workspace_id, target_user_id)
        if existing:
            raise ConflictError("User is already a member of this workspace")

        member = await self._ws_repo.add_member(workspace_id, target_user_id, role)

        # Publish to both workspace and user channels
        event_payload = {
            "workspace_id": str(workspace_id),
            "user_id": str(target_user_id),
            "role": role.value,
        }
        await self._publisher.publish_many(
            [
                RealtimeEvent(
                    channel=f"workspace:{workspace_id}",
                    event_type="workspace.member_added",
                    payload=event_payload,
                ),
                RealtimeEvent(
                    channel=f"user:{target_user_id}",
                    event_type="workspace.member_added",
                    payload=event_payload,
                ),
            ]
        )

        return member

    async def remove_member(
        self,
        workspace_id: UUID,
        requester_id: UUID,
        target_user_id: UUID,
    ) -> None:
        await self._auth.require_workspace_owner(requester_id, workspace_id)

        # Cannot remove the owner
        workspace = await self._ws_repo.get_by_id_with_members(workspace_id)
        if workspace and workspace.owner_id == target_user_id:
            raise ConflictError("Cannot remove the workspace owner")

        member = await self._ws_repo.get_member(workspace_id, target_user_id)
        if member is None:
            raise NotFoundError("WorkspaceMember")

        await self._ws_repo.remove_member(member)

        # Publish to both workspace and user channels
        event_payload = {
            "workspace_id": str(workspace_id),
            "user_id": str(target_user_id),
        }
        await self._publisher.publish_many(
            [
                RealtimeEvent(
                    channel=f"workspace:{workspace_id}",
                    event_type="workspace.member_removed",
                    payload=event_payload,
                ),
                RealtimeEvent(
                    channel=f"user:{target_user_id}",
                    event_type="workspace.member_removed",
                    payload=event_payload,
                ),
            ]
        )

    async def update_member_role(
        self,
        workspace_id: UUID,
        requester_id: UUID,
        target_user_id: UUID,
        new_role: WorkspaceRole,
    ) -> WorkspaceMember:
        """Change a member's role within the workspace."""
        await self._auth.require_workspace_owner(requester_id, workspace_id)

        # Cannot change the owner's role
        workspace = await self._ws_repo.get_by_id_with_members(workspace_id)
        if workspace and workspace.owner_id == target_user_id:
            raise ValidationError("Cannot change the workspace owner's role")

        member = await self._ws_repo.get_member(workspace_id, target_user_id)
        if member is None:
            raise NotFoundError("WorkspaceMember")

        member.role = new_role
        await self._ws_repo.session.flush()
        await self._ws_repo.session.refresh(member)

        # Publish role change event
        await self._publisher.publish(
            RealtimeEvent(
                channel=f"workspace:{workspace_id}",
                event_type="workspace.member_role_changed",
                payload={
                    "workspace_id": str(workspace_id),
                    "user_id": str(target_user_id),
                    "new_role": new_role.value,
                },
            )
        )

        return member

    async def list_members(
        self, workspace_id: UUID, requester_id: UUID
    ) -> list[WorkspaceMember]:
        await self._auth.require_workspace_member(requester_id, workspace_id)
        return await self._ws_repo.list_members(workspace_id)
