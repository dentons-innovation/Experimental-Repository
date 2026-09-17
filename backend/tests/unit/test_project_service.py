"""Unit tests for ProjectService — project management and membership."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.domain.enums import ProjectRole
from app.domain.exceptions import ConflictError, NotFoundError
from app.domain.models import Project, ProjectMember
from app.services.project_service import ProjectService, _slugify


def _make_project(workspace_id=None) -> Project:
    p = MagicMock(spec=Project)
    p.id = uuid4()
    p.name = "Project Flow"
    p.slug = "project-flow"
    p.description = "Project description"
    p.workspace_id = workspace_id or uuid4()
    return p


def _make_service(
    project: Project | None = None,
    existing_slug_project: Project | None = None,
    target_user=None,
    existing_member: ProjectMember | None = None,
) -> ProjectService:
    proj_repo = MagicMock()
    proj_repo.get_by_id_with_members = AsyncMock(return_value=project)
    proj_repo.get_by_workspace_and_slug = AsyncMock(return_value=existing_slug_project)
    proj_repo.get_member = AsyncMock(return_value=existing_member)
    proj_repo.add_member = AsyncMock(return_value=MagicMock(spec=ProjectMember))
    proj_repo.remove_member = AsyncMock()
    proj_repo.list_for_workspace = AsyncMock(
        return_value=([project] if project else [], 1 if project else 0)
    )
    proj_repo.list_members = AsyncMock(
        return_value=[existing_member] if existing_member else []
    )
    proj_repo.delete = AsyncMock()
    proj_repo.session = MagicMock()
    proj_repo.session.add = MagicMock()
    proj_repo.session.flush = AsyncMock()
    proj_repo.session.refresh = AsyncMock()

    ws_repo = MagicMock()
    user_repo = MagicMock()
    user_repo.get_by_id = AsyncMock(return_value=target_user)

    auth = MagicMock()
    auth.can_create_project = AsyncMock()
    auth.can_read_project = AsyncMock()
    auth.can_update_project = AsyncMock()
    auth.can_delete_project = AsyncMock()
    auth.can_manage_project_members = AsyncMock()

    return ProjectService(proj_repo, ws_repo, user_repo, auth)


class TestProjectSlugify:
    def test_slugify(self):
        assert _slugify("Test Project 123") == "test-project-123"


class TestCreateProject:
    async def test_create_project_success(self):
        svc = _make_service(existing_slug_project=None)
        ws_id = uuid4()
        creator_id = uuid4()
        project = await svc.create_project(
            workspace_id=ws_id,
            creator_id=creator_id,
            name="Sprint 1",
            description="First sprint",
        )
        assert project.name == "Sprint 1"
        assert project.slug == "sprint-1"
        svc._proj_repo.session.add.assert_called_once()
        svc._proj_repo.add_member.assert_called_once_with(
            project.id, creator_id, ProjectRole.ADMIN
        )

    async def test_create_project_slug_collision_raises_conflict(self):
        existing = _make_project()
        svc = _make_service(existing_slug_project=existing)
        with pytest.raises(ConflictError) as exc_info:
            await svc.create_project(
                workspace_id=uuid4(),
                creator_id=uuid4(),
                name="Existing Project",
            )
        assert "already exists in this workspace" in str(exc_info.value)


class TestGetProject:
    async def test_get_existing_project(self):
        p = _make_project()
        svc = _make_service(project=p)
        result = await svc.get_project(p.id, uuid4())
        assert result == p
        svc._auth.can_read_project.assert_called_once()

    async def test_get_missing_project_raises_404(self):
        svc = _make_service(project=None)
        with pytest.raises(NotFoundError):
            await svc.get_project(uuid4(), uuid4())


class TestUpdateProject:
    async def test_update_project_success(self):
        p = _make_project()
        svc = _make_service(project=p)
        result = await svc.update_project(
            p.id, uuid4(), name="Updated Name", description="Updated Desc"
        )
        assert result.name == "Updated Name"
        assert result.description == "Updated Desc"
        svc._auth.can_update_project.assert_called_once()

    async def test_update_missing_project_raises_404(self):
        svc = _make_service(project=None)
        with pytest.raises(NotFoundError):
            await svc.update_project(uuid4(), uuid4(), name="Renamed")


class TestDeleteProject:
    async def test_delete_existing_project(self):
        p = _make_project()
        svc = _make_service(project=p)
        await svc.delete_project(p.id, uuid4())
        svc._proj_repo.delete.assert_called_once_with(p)

    async def test_delete_missing_project_raises_404(self):
        svc = _make_service(project=None)
        with pytest.raises(NotFoundError):
            await svc.delete_project(uuid4(), uuid4())


class TestProjectMembers:
    async def test_add_member_success(self):
        p = _make_project()
        target = MagicMock()
        target.id = uuid4()
        svc = _make_service(project=p, target_user=target, existing_member=None)

        requester_id = uuid4()
        await svc.add_member(p.id, requester_id, target.id, ProjectRole.MEMBER)
        svc._proj_repo.add_member.assert_called_once_with(
            p.id, target.id, ProjectRole.MEMBER
        )

    async def test_add_member_missing_project_raises_404(self):
        svc = _make_service(project=None)
        with pytest.raises(NotFoundError):
            await svc.add_member(uuid4(), uuid4(), uuid4())

    async def test_add_member_missing_user_raises_404(self):
        p = _make_project()
        svc = _make_service(project=p, target_user=None)
        with pytest.raises(NotFoundError):
            await svc.add_member(p.id, uuid4(), uuid4())

    async def test_add_member_already_member_raises_conflict(self):
        p = _make_project()
        target = MagicMock()
        existing = MagicMock(spec=ProjectMember)
        svc = _make_service(project=p, target_user=target, existing_member=existing)
        with pytest.raises(ConflictError):
            await svc.add_member(p.id, uuid4(), target.id)

    async def test_remove_member_success(self):
        p = _make_project()
        member = MagicMock(spec=ProjectMember)
        svc = _make_service(project=p, existing_member=member)

        await svc.remove_member(p.id, uuid4(), uuid4())
        svc._proj_repo.remove_member.assert_called_once_with(member)

    async def test_remove_member_missing_project_raises_404(self):
        svc = _make_service(project=None)
        with pytest.raises(NotFoundError):
            await svc.remove_member(uuid4(), uuid4(), uuid4())

    async def test_remove_missing_member_raises_404(self):
        p = _make_project()
        svc = _make_service(project=p, existing_member=None)
        with pytest.raises(NotFoundError):
            await svc.remove_member(p.id, uuid4(), uuid4())

    async def test_list_members_success(self):
        p = _make_project()
        member = MagicMock(spec=ProjectMember)
        svc = _make_service(project=p, existing_member=member)
        members = await svc.list_members(p.id, uuid4())
        assert members == [member]

    async def test_list_members_missing_project_raises_404(self):
        svc = _make_service(project=None)
        with pytest.raises(NotFoundError):
            await svc.list_members(uuid4(), uuid4())
