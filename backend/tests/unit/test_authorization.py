"""Unit tests for AuthorizationService.

Covers the full role × resource × operation matrix plus:
- Cross-workspace access attempts
- Cross-project access attempts
- Enumeration prevention (404 vs 403)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.domain.enums import ProjectRole, WorkspaceRole
from app.domain.exceptions import AuthorizationError, NotFoundError
from app.domain.models import Comment, Project, Task
from app.services.authorization import AuthorizationService


def _make_auth(
    ws_role: WorkspaceRole | None = None,
    proj_role: ProjectRole | None = None,
) -> AuthorizationService:
    """Create an AuthorizationService with mocked repositories."""
    ws_repo = MagicMock()
    proj_repo = MagicMock()

    # Mock get_member for workspace
    if ws_role is not None:
        ws_member = MagicMock()
        ws_member.role = ws_role
        ws_repo.get_member = AsyncMock(return_value=ws_member)
    else:
        ws_repo.get_member = AsyncMock(return_value=None)

    # Mock get_member for project
    if proj_role is not None:
        proj_member = MagicMock()
        proj_member.role = proj_role
        proj_repo.get_member = AsyncMock(return_value=proj_member)
    else:
        proj_repo.get_member = AsyncMock(return_value=None)

    return AuthorizationService(ws_repo, proj_repo)


def _task(
    project_id=None, workspace_id=None, assignee_id=None, creator_id=None
) -> Task:
    task = MagicMock(spec=Task)
    task.id = uuid4()
    task.project_id = project_id or uuid4()
    task.workspace_id = workspace_id or uuid4()
    task.assignee_id = assignee_id
    task.creator_id = creator_id or uuid4()
    return task


def _project(workspace_id=None) -> Project:
    project = MagicMock(spec=Project)
    project.id = uuid4()
    project.workspace_id = workspace_id or uuid4()
    return project


def _comment(author_id=None, task_id=None) -> Comment:
    comment = MagicMock(spec=Comment)
    comment.id = uuid4()
    comment.author_id = author_id or uuid4()
    comment.task_id = task_id or uuid4()
    return comment


# ─────────────────────────────────────────────────────────────
# Workspace membership checks
# ─────────────────────────────────────────────────────────────

class TestWorkspaceMembership:
    async def test_owner_can_access_workspace(self):
        auth = _make_auth(ws_role=WorkspaceRole.OWNER)
        role = await auth.require_workspace_member(uuid4(), uuid4())
        assert role == WorkspaceRole.OWNER

    async def test_member_can_access_workspace(self):
        auth = _make_auth(ws_role=WorkspaceRole.MEMBER)
        role = await auth.require_workspace_member(uuid4(), uuid4())
        assert role == WorkspaceRole.MEMBER

    async def test_non_member_gets_404(self):
        auth = _make_auth(ws_role=None)
        with pytest.raises(NotFoundError):
            await auth.require_workspace_member(uuid4(), uuid4())

    async def test_owner_only_action_by_owner_passes(self):
        auth = _make_auth(ws_role=WorkspaceRole.OWNER)
        await auth.require_workspace_owner(uuid4(), uuid4())  # no exception

    async def test_owner_only_action_by_member_raises_403(self):
        auth = _make_auth(ws_role=WorkspaceRole.MEMBER)
        with pytest.raises(AuthorizationError):
            await auth.require_workspace_owner(uuid4(), uuid4())

    async def test_owner_only_action_by_non_member_raises_404(self):
        auth = _make_auth(ws_role=None)
        with pytest.raises(NotFoundError):
            await auth.require_workspace_owner(uuid4(), uuid4())


# ─────────────────────────────────────────────────────────────
# Project membership checks
# ─────────────────────────────────────────────────────────────

class TestProjectMembership:
    async def test_project_admin_gets_admin_role(self):
        auth = _make_auth(proj_role=ProjectRole.ADMIN)
        role = await auth.require_project_member(uuid4(), uuid4())
        assert role == ProjectRole.ADMIN

    async def test_project_member_gets_member_role(self):
        auth = _make_auth(proj_role=ProjectRole.MEMBER)
        role = await auth.require_project_member(uuid4(), uuid4())
        assert role == ProjectRole.MEMBER

    async def test_non_project_member_gets_404(self):
        auth = _make_auth(proj_role=None)
        with pytest.raises(NotFoundError):
            await auth.require_project_member(uuid4(), uuid4())

    async def test_project_admin_action_by_admin_passes(self):
        auth = _make_auth(proj_role=ProjectRole.ADMIN)
        await auth.require_project_admin(uuid4(), uuid4())

    async def test_project_admin_action_by_member_raises_403(self):
        auth = _make_auth(proj_role=ProjectRole.MEMBER)
        with pytest.raises(AuthorizationError):
            await auth.require_project_admin(uuid4(), uuid4())


# ─────────────────────────────────────────────────────────────
# Project operations — full matrix
# ─────────────────────────────────────────────────────────────

class TestProjectOperations:
    async def test_ws_owner_can_update_project(self):
        project = _project()
        auth = _make_auth(ws_role=WorkspaceRole.OWNER, proj_role=None)
        await auth.can_update_project(uuid4(), project)  # no exception

    async def test_ws_member_cannot_update_project(self):
        project = _project()
        auth = _make_auth(ws_role=WorkspaceRole.MEMBER, proj_role=None)
        with pytest.raises((AuthorizationError, NotFoundError)):
            await auth.can_update_project(uuid4(), project)

    async def test_project_admin_can_update_project(self):
        project = _project()
        auth = _make_auth(ws_role=None, proj_role=ProjectRole.ADMIN)
        await auth.can_update_project(uuid4(), project)

    async def test_project_member_cannot_update_project(self):
        project = _project()
        auth = _make_auth(ws_role=None, proj_role=ProjectRole.MEMBER)
        with pytest.raises(AuthorizationError):
            await auth.can_update_project(uuid4(), project)

    async def test_ws_owner_can_delete_project(self):
        project = _project()
        auth = _make_auth(ws_role=WorkspaceRole.OWNER)
        await auth.can_delete_project(uuid4(), project)

    async def test_project_member_cannot_delete_project(self):
        project = _project()
        auth = _make_auth(ws_role=None, proj_role=ProjectRole.MEMBER)
        with pytest.raises(AuthorizationError):
            await auth.can_delete_project(uuid4(), project)

    async def test_ws_member_can_create_project(self):
        auth = _make_auth(ws_role=WorkspaceRole.MEMBER)
        await auth.can_create_project(uuid4(), uuid4())

    async def test_non_ws_member_cannot_create_project(self):
        auth = _make_auth(ws_role=None)
        with pytest.raises(NotFoundError):
            await auth.can_create_project(uuid4(), uuid4())


# ─────────────────────────────────────────────────────────────
# Task operations — full matrix
# ─────────────────────────────────────────────────────────────

class TestTaskOperations:
    async def test_project_member_can_create_task(self):
        auth = _make_auth(proj_role=ProjectRole.MEMBER)
        await auth.can_create_task(uuid4(), uuid4())

    async def test_non_project_member_cannot_create_task(self):
        auth = _make_auth(proj_role=None)
        with pytest.raises(NotFoundError):
            await auth.can_create_task(uuid4(), uuid4())

    async def test_project_member_can_read_task(self):
        task = _task()
        auth = _make_auth(proj_role=ProjectRole.MEMBER)
        await auth.can_read_task(uuid4(), task)

    async def test_non_member_cannot_read_task(self):
        task = _task()
        auth = _make_auth(proj_role=None)
        with pytest.raises(NotFoundError):
            await auth.can_read_task(uuid4(), task)

    async def test_project_member_can_update_task(self):
        task = _task()
        auth = _make_auth(proj_role=ProjectRole.MEMBER)
        await auth.can_update_task(uuid4(), task)

    async def test_project_admin_can_delete_task(self):
        task = _task()
        auth = _make_auth(ws_role=None, proj_role=ProjectRole.ADMIN)
        await auth.can_delete_task(uuid4(), task)

    async def test_project_member_cannot_delete_task(self):
        task = _task()
        auth = _make_auth(ws_role=None, proj_role=ProjectRole.MEMBER)
        with pytest.raises(AuthorizationError):
            await auth.can_delete_task(uuid4(), task)

    async def test_ws_owner_can_delete_task(self):
        task = _task()
        auth = _make_auth(ws_role=WorkspaceRole.OWNER, proj_role=None)
        await auth.can_delete_task(uuid4(), task)


# ─────────────────────────────────────────────────────────────
# Comment operations
# ─────────────────────────────────────────────────────────────

class TestCommentOperations:
    async def test_author_can_edit_own_comment(self):
        user_id = uuid4()
        comment = _comment(author_id=user_id)
        task = _task()
        auth = _make_auth(proj_role=ProjectRole.MEMBER)
        await auth.can_edit_comment(user_id, comment, task)

    async def test_non_author_cannot_edit_comment(self):
        comment = _comment(author_id=uuid4())
        task = _task()
        auth = _make_auth(proj_role=ProjectRole.ADMIN)
        with pytest.raises(AuthorizationError):
            await auth.can_edit_comment(uuid4(), comment, task)

    async def test_author_can_delete_own_comment(self):
        user_id = uuid4()
        comment = _comment(author_id=user_id)
        task = _task()
        auth = _make_auth(proj_role=ProjectRole.MEMBER)
        await auth.can_delete_comment(user_id, comment, task)

    async def test_project_admin_can_delete_others_comment(self):
        comment = _comment(author_id=uuid4())
        task = _task()
        auth = _make_auth(ws_role=None, proj_role=ProjectRole.ADMIN)
        await auth.can_delete_comment(uuid4(), comment, task)

    async def test_project_member_cannot_delete_others_comment(self):
        comment = _comment(author_id=uuid4())
        task = _task()
        auth = _make_auth(ws_role=None, proj_role=ProjectRole.MEMBER)
        with pytest.raises(AuthorizationError):
            await auth.can_delete_comment(uuid4(), comment, task)

    async def test_ws_owner_can_delete_any_comment(self):
        comment = _comment(author_id=uuid4())
        task = _task()
        auth = _make_auth(ws_role=WorkspaceRole.OWNER, proj_role=None)
        await auth.can_delete_comment(uuid4(), comment, task)


# ─────────────────────────────────────────────────────────────
# Label operations
# ─────────────────────────────────────────────────────────────

class TestLabelOperations:
    async def test_ws_member_can_manage_labels(self):
        auth = _make_auth(ws_role=WorkspaceRole.MEMBER)
        role = await auth.can_manage_labels(uuid4(), uuid4())
        assert role == WorkspaceRole.MEMBER

    async def test_ws_owner_can_delete_label(self):
        auth = _make_auth(ws_role=WorkspaceRole.OWNER)
        await auth.can_delete_label(uuid4(), uuid4())

    async def test_ws_member_cannot_delete_label(self):
        auth = _make_auth(ws_role=WorkspaceRole.MEMBER)
        with pytest.raises(AuthorizationError):
            await auth.can_delete_label(uuid4(), uuid4())


# ─────────────────────────────────────────────────────────────
# Cross-resource isolation
# ─────────────────────────────────────────────────────────────

class TestCrossResourceIsolation:
    def test_task_in_wrong_project_raises_404(self):
        task = _task(project_id=uuid4())
        wrong_project_id = uuid4()
        with pytest.raises(NotFoundError):
            AuthorizationService.assert_task_in_project(task, wrong_project_id)

    def test_task_in_correct_project_passes(self):
        project_id = uuid4()
        task = _task(project_id=project_id)
        AuthorizationService.assert_task_in_project(task, project_id)  # no exception

    def test_project_in_wrong_workspace_raises_404(self):
        project = _project(workspace_id=uuid4())
        wrong_ws_id = uuid4()
        with pytest.raises(NotFoundError):
            AuthorizationService.assert_project_in_workspace(project, wrong_ws_id)

    def test_project_in_correct_workspace_passes(self):
        workspace_id = uuid4()
        project = _project(workspace_id=workspace_id)
        AuthorizationService.assert_project_in_workspace(project, workspace_id)  # no exception
