"""Project service — project lifecycle and membership."""

from __future__ import annotations

import re
from uuid import UUID

from app.domain.enums import ProjectRole
from app.domain.exceptions import ConflictError, NotFoundError
from app.domain.models import Project, ProjectMember
from app.repositories.project_repository import ProjectRepository
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.services.authorization import AuthorizationService


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    return slug.strip("-")[:64]


class ProjectService:
    def __init__(
        self,
        project_repo: ProjectRepository,
        workspace_repo: WorkspaceRepository,
        user_repo: UserRepository,
        auth_service: AuthorizationService,
    ) -> None:
        self._proj_repo = project_repo
        self._ws_repo = workspace_repo
        self._user_repo = user_repo
        self._auth = auth_service

    async def create_project(
        self,
        workspace_id: UUID,
        creator_id: UUID,
        name: str,
        description: str | None = None,
        slug: str | None = None,
    ) -> Project:
        await self._auth.can_create_project(creator_id, workspace_id)

        final_slug = slug or _slugify(name) or "project"
        existing = await self._proj_repo.get_by_workspace_and_slug(
            workspace_id, final_slug
        )
        if existing:
            raise ConflictError(f"Project slug '{final_slug}' already exists in this workspace")

        project = Project(
            workspace_id=workspace_id,
            name=name,
            slug=final_slug,
            description=description,
        )
        self._proj_repo.session.add(project)
        await self._proj_repo.session.flush()
        await self._proj_repo.session.refresh(project)

        # Auto-add creator as ADMIN
        await self._proj_repo.add_member(project.id, creator_id, ProjectRole.ADMIN)

        return project

    async def list_projects(
        self,
        workspace_id: UUID,
        user_id: UUID,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Project], int]:
        return await self._proj_repo.list_for_workspace(
            workspace_id, user_id, offset=offset, limit=limit
        )

    async def get_project(
        self, project_id: UUID, user_id: UUID
    ) -> Project:
        project = await self._proj_repo.get_by_id_with_members(project_id)
        if project is None:
            raise NotFoundError("Project", str(project_id))
        await self._auth.can_read_project(user_id, project)
        return project

    async def update_project(
        self,
        project_id: UUID,
        user_id: UUID,
        name: str | None = None,
        description: str | None = None,
    ) -> Project:
        project = await self._proj_repo.get_by_id_with_members(project_id)
        if project is None:
            raise NotFoundError("Project", str(project_id))
        await self._auth.can_update_project(user_id, project)

        if name is not None:
            project.name = name
        if description is not None:
            project.description = description

        await self._proj_repo.session.flush()
        await self._proj_repo.session.refresh(project)
        return project

    async def delete_project(self, project_id: UUID, user_id: UUID) -> None:
        project = await self._proj_repo.get_by_id_with_members(project_id)
        if project is None:
            raise NotFoundError("Project", str(project_id))
        await self._auth.can_delete_project(user_id, project)
        await self._proj_repo.delete(project)

    async def add_member(
        self,
        project_id: UUID,
        requester_id: UUID,
        target_user_id: UUID,
        role: ProjectRole = ProjectRole.MEMBER,
    ) -> ProjectMember:
        project = await self._proj_repo.get_by_id_with_members(project_id)
        if project is None:
            raise NotFoundError("Project", str(project_id))
        await self._auth.can_manage_project_members(requester_id, project)

        target = await self._user_repo.get_by_id(target_user_id)
        if target is None:
            raise NotFoundError("User", str(target_user_id))

        existing = await self._proj_repo.get_member(project_id, target_user_id)
        if existing:
            raise ConflictError("User is already a member of this project")

        return await self._proj_repo.add_member(project_id, target_user_id, role)

    async def remove_member(
        self, project_id: UUID, requester_id: UUID, target_user_id: UUID
    ) -> None:
        project = await self._proj_repo.get_by_id_with_members(project_id)
        if project is None:
            raise NotFoundError("Project", str(project_id))
        await self._auth.can_manage_project_members(requester_id, project)

        member = await self._proj_repo.get_member(project_id, target_user_id)
        if member is None:
            raise NotFoundError("ProjectMember")

        await self._proj_repo.remove_member(member)

    async def list_members(
        self, project_id: UUID, requester_id: UUID
    ) -> list[ProjectMember]:
        project = await self._proj_repo.get_by_id_with_members(project_id)
        if project is None:
            raise NotFoundError("Project", str(project_id))
        await self._auth.can_read_project(requester_id, project)
        return await self._proj_repo.list_members(project_id)
