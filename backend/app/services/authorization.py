"""Centralized authorization service.

All permission checks for every protected operation are defined here.
This is the single source of truth for the authorization model.

Authorization Matrix
────────────────────────────────────────────────────────────────────
Resource/Op          WS_OWNER  WS_MEMBER  PROJ_ADMIN  PROJ_MEMBER
workspace:read          ✓         ✓           ✓(via pm)    ✓(via pm)
workspace:update        ✓         ✗           ✗            ✗
workspace:delete        ✓         ✗           ✗            ✗
workspace:add_member    ✓         ✗           ✗            ✗
workspace:remove_member ✓         ✗           ✗            ✗
project:create          ✓         ✓           ✗            ✗
project:read            ✓         ✓(pm req)   ✓            ✓
project:update          ✓         ✗           ✓            ✗
project:delete          ✓         ✗           ✓            ✗
project:add_member      ✓         ✗           ✓            ✗
project:remove_member   ✓         ✗           ✓            ✗
task:create             ✓         ✗           ✓            ✓
task:read               ✓         ✗           ✓            ✓
task:update             ✓         ✗           ✓            ✓
task:delete             ✓         ✗           ✓            ✗
comment:create          ✓         ✗           ✓            ✓
comment:edit_own        ✓         ✗           ✓            ✓
comment:delete_own      ✓         ✗           ✓            ✓
comment:delete_any      ✓         ✗           ✓            ✗
label:create            ✓         ✓           ✗            ✗
label:read              ✓         ✓           ✓            ✓
label:update            ✓         ✓           ✗            ✗
label:delete            ✓         ✗           ✗            ✗
────────────────────────────────────────────────────────────────────

Design:
- All checks are async to allow future DB lookups if needed.
- Methods raise AuthorizationError (mapped to HTTP 403) or
  NotFoundError (mapped to HTTP 404 to prevent enumeration).
- Cross-workspace/cross-project isolation is enforced by checking
  that the resource belongs to the workspace/project being accessed.
"""

from __future__ import annotations

from uuid import UUID

import structlog

from app.domain.enums import ProjectRole, WorkspaceRole
from app.domain.exceptions import AuthorizationError, NotFoundError
from app.domain.models import Comment, Project, Task, Workspace
from app.repositories.project_repository import ProjectRepository
from app.repositories.workspace_repository import WorkspaceRepository

logger = structlog.get_logger(__name__)


class AuthorizationService:
    """Centralized, testable authorization service.

    Injected into all service classes that perform protected operations.
    All public methods raise AuthorizationError or NotFoundError;
    they never return False silently.
    """

    def __init__(
        self,
        workspace_repo: WorkspaceRepository,
        project_repo: ProjectRepository,
    ) -> None:
        self._ws_repo = workspace_repo
        self._proj_repo = project_repo

    # ─────────────────────────────────────────────────────────
    # Workspace checks
    # ─────────────────────────────────────────────────────────

    async def _get_ws_role(
        self, user_id: UUID, workspace_id: UUID
    ) -> WorkspaceRole | None:
        member = await self._ws_repo.get_member(workspace_id, user_id)
        return member.role if member else None

    async def require_workspace_member(
        self, user_id: UUID, workspace_id: UUID
    ) -> WorkspaceRole:
        """Require at least workspace member access. Returns the role."""
        role = await self._get_ws_role(user_id, workspace_id)
        if role is None:
            # Return 404 to prevent workspace enumeration
            raise NotFoundError("Workspace", str(workspace_id))
        return role

    async def require_workspace_owner(
        self, user_id: UUID, workspace_id: UUID
    ) -> None:
        role = await self._get_ws_role(user_id, workspace_id)
        if role is None:
            raise NotFoundError("Workspace", str(workspace_id))
        if role != WorkspaceRole.OWNER:
            raise AuthorizationError("Only workspace owners can perform this action")

    # ─────────────────────────────────────────────────────────
    # Project checks
    # ─────────────────────────────────────────────────────────

    async def _get_proj_role(
        self, user_id: UUID, project_id: UUID
    ) -> ProjectRole | None:
        member = await self._proj_repo.get_member(project_id, user_id)
        return member.role if member else None

    async def require_project_member(
        self, user_id: UUID, project_id: UUID
    ) -> ProjectRole:
        """Require at least project member access. Returns role."""
        role = await self._get_proj_role(user_id, project_id)
        if role is None:
            raise NotFoundError("Project", str(project_id))
        return role

    async def require_project_admin(
        self, user_id: UUID, project_id: UUID
    ) -> None:
        role = await self._get_proj_role(user_id, project_id)
        if role is None:
            raise NotFoundError("Project", str(project_id))
        if role != ProjectRole.ADMIN:
            raise AuthorizationError(
                "Only project admins can perform this action"
            )

    # ─────────────────────────────────────────────────────────
    # Combined / context-aware checks
    # ─────────────────────────────────────────────────────────

    async def can_create_project(
        self, user_id: UUID, workspace_id: UUID
    ) -> None:
        """Any workspace member can create a project."""
        await self.require_workspace_member(user_id, workspace_id)

    async def can_read_project(
        self, user_id: UUID, project: Project
    ) -> None:
        """User must be a project member OR a workspace owner."""
        ws_role = await self._get_ws_role(user_id, project.workspace_id)
        if ws_role == WorkspaceRole.OWNER:
            return
        proj_role = await self._get_proj_role(user_id, project.id)
        if proj_role is None:
            raise NotFoundError("Project", str(project.id))

    async def can_update_project(
        self, user_id: UUID, project: Project
    ) -> None:
        ws_role = await self._get_ws_role(user_id, project.workspace_id)
        if ws_role == WorkspaceRole.OWNER:
            return
        await self.require_project_admin(user_id, project.id)

    async def can_delete_project(
        self, user_id: UUID, project: Project
    ) -> None:
        ws_role = await self._get_ws_role(user_id, project.workspace_id)
        if ws_role == WorkspaceRole.OWNER:
            return
        await self.require_project_admin(user_id, project.id)

    async def can_manage_project_members(
        self, user_id: UUID, project: Project
    ) -> None:
        ws_role = await self._get_ws_role(user_id, project.workspace_id)
        if ws_role == WorkspaceRole.OWNER:
            return
        await self.require_project_admin(user_id, project.id)

    async def can_create_task(
        self, user_id: UUID, project_id: UUID
    ) -> None:
        await self.require_project_member(user_id, project_id)

    async def can_read_task(
        self, user_id: UUID, task: Task
    ) -> None:
        await self.require_project_member(user_id, task.project_id)

    async def can_update_task(
        self, user_id: UUID, task: Task
    ) -> None:
        await self.require_project_member(user_id, task.project_id)

    async def can_delete_task(
        self, user_id: UUID, task: Task
    ) -> None:
        ws_role = await self._get_ws_role(user_id, task.workspace_id)
        if ws_role == WorkspaceRole.OWNER:
            return
        await self.require_project_admin(user_id, task.project_id)

    async def can_create_comment(
        self, user_id: UUID, task: Task
    ) -> None:
        await self.require_project_member(user_id, task.project_id)

    async def can_edit_comment(
        self, user_id: UUID, comment: Comment, task: Task
    ) -> None:
        """Author can edit own comment; project admin/ws owner cannot edit others'."""
        if comment.author_id == user_id:
            # Still must be a project member
            await self.require_project_member(user_id, task.project_id)
            return
        raise AuthorizationError("You can only edit your own comments")

    async def can_delete_comment(
        self, user_id: UUID, comment: Comment, task: Task
    ) -> None:
        """Author can delete own; project admin can delete any."""
        if comment.author_id == user_id:
            await self.require_project_member(user_id, task.project_id)
            return
        ws_role = await self._get_ws_role(user_id, task.workspace_id)
        if ws_role == WorkspaceRole.OWNER:
            return
        proj_role = await self._get_proj_role(user_id, task.project_id)
        if proj_role == ProjectRole.ADMIN:
            return
        raise AuthorizationError(
            "Only project admins can delete other users' comments"
        )

    async def can_manage_labels(
        self, user_id: UUID, workspace_id: UUID
    ) -> WorkspaceRole:
        """Any workspace member can create/update labels.
        Only owner can delete.
        """
        return await self.require_workspace_member(user_id, workspace_id)

    async def can_delete_label(
        self, user_id: UUID, workspace_id: UUID
    ) -> None:
        await self.require_workspace_owner(user_id, workspace_id)

    # ─────────────────────────────────────────────────────────
    # Cross-resource isolation
    # ─────────────────────────────────────────────────────────

    @staticmethod
    def assert_task_in_project(task: Task, project_id: UUID) -> None:
        """Prevent cross-project access via direct task ID manipulation."""
        if task.project_id != project_id:
            raise NotFoundError("Task", str(task.id))

    @staticmethod
    def assert_project_in_workspace(project: Project, workspace_id: UUID) -> None:
        """Prevent cross-workspace access via direct project ID manipulation."""
        if project.workspace_id != workspace_id:
            raise NotFoundError("Project", str(project.id))
