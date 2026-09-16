"""Project repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.enums import ProjectRole
from app.domain.models import Project, ProjectMember
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    model = Project

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_id_with_members(self, project_id: UUID) -> Project | None:
        result = await self.session.execute(
            select(Project)
            .where(Project.id == project_id)
            .options(selectinload(Project.members).selectinload(ProjectMember.user))
        )
        return result.scalar_one_or_none()

    async def get_by_workspace_and_slug(
        self, workspace_id: UUID, slug: str
    ) -> Project | None:
        result = await self.session.execute(
            select(Project).where(
                Project.workspace_id == workspace_id, Project.slug == slug
            )
        )
        return result.scalar_one_or_none()

    async def list_for_workspace(
        self, workspace_id: UUID, user_id: UUID, offset: int = 0, limit: int = 20
    ) -> tuple[list[Project], int]:
        """Return projects in a workspace that the user is a member of."""
        base_query = (
            select(Project)
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(
                Project.workspace_id == workspace_id,
                ProjectMember.user_id == user_id,
            )
        )
        count_result = await self.session.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total = count_result.scalar_one()

        result = await self.session.execute(
            base_query.order_by(Project.created_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def get_member(self, project_id: UUID, user_id: UUID) -> ProjectMember | None:
        result = await self.session.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_members(self, project_id: UUID) -> list[ProjectMember]:
        result = await self.session.execute(
            select(ProjectMember)
            .where(ProjectMember.project_id == project_id)
            .options(selectinload(ProjectMember.user))
            .order_by(ProjectMember.created_at)
        )
        return list(result.scalars().all())

    async def add_member(
        self, project_id: UUID, user_id: UUID, role: ProjectRole
    ) -> ProjectMember:
        member = ProjectMember(project_id=project_id, user_id=user_id, role=role)
        self.session.add(member)
        await self.session.flush()
        await self.session.refresh(member)
        return member

    async def remove_member(self, member: ProjectMember) -> None:
        await self.session.delete(member)
        await self.session.flush()
