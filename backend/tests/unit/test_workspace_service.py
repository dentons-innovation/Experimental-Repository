"""Unit tests for WorkspaceService — business logic and membership validation."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.domain.enums import WorkspaceRole
from app.domain.exceptions import ConflictError, NotFoundError
from app.domain.models import Workspace, WorkspaceMember
from app.services.workspace_service import WorkspaceService, _slugify


def _make_workspace(owner_id=None) -> Workspace:
    ws = MagicMock(spec=Workspace)
    ws.id = uuid4()
    ws.name = "Test Workspace"
    ws.slug = "test-workspace"
    ws.description = "A workspace"
    ws.owner_id = owner_id or uuid4()
    return ws


def _make_service(
    workspace: Workspace | None = None,
    existing_slug_workspace: Workspace | None = None,
    target_user=None,
    existing_member: WorkspaceMember | None = None,
) -> WorkspaceService:
    ws_repo = MagicMock()
    ws_repo.get_by_id_with_members = AsyncMock(return_value=workspace)
    ws_repo.get_by_slug = AsyncMock(return_value=existing_slug_workspace)
    ws_repo.get_member = AsyncMock(return_value=existing_member)
    ws_repo.add_member = AsyncMock(return_value=MagicMock(spec=WorkspaceMember))
    ws_repo.remove_member = AsyncMock()
    ws_repo.list_for_user = AsyncMock(return_value=([workspace] if workspace else [], 1 if workspace else 0))
    ws_repo.list_members = AsyncMock(return_value=[existing_member] if existing_member else [])
    ws_repo.delete = AsyncMock()
    ws_repo.session = MagicMock()
    ws_repo.session.add = MagicMock()
    ws_repo.session.flush = AsyncMock()
    ws_repo.session.refresh = AsyncMock()

    user_repo = MagicMock()
    user_repo.get_by_id = AsyncMock(return_value=target_user)

    auth = MagicMock()
    auth.require_workspace_member = AsyncMock()
    auth.require_workspace_owner = AsyncMock()

    return WorkspaceService(ws_repo, user_repo, auth)


class TestSlugify:
    def test_slugify_clean_input(self):
        assert _slugify("My Workspace") == "my-workspace"

    def test_slugify_special_characters(self):
        assert _slugify("Hello! @World #2026") == "hello-world-2026"

    def test_slugify_empty_string(self):
        assert _slugify("   ") == ""


class TestCreateWorkspace:
    async def test_create_workspace_success(self):
        svc = _make_service(existing_slug_workspace=None)
        owner_id = uuid4()
        ws = await svc.create_workspace(
            owner_id=owner_id,
            name="New Team",
            description="Team desc",
        )
        assert ws.name == "New Team"
        assert ws.slug == "new-team"
        svc._ws_repo.session.add.assert_called_once()
        svc._ws_repo.add_member.assert_called_once_with(ws.id, owner_id, WorkspaceRole.OWNER)

    async def test_create_workspace_empty_slug_fallback(self):
        svc = _make_service(existing_slug_workspace=None)
        owner_id = uuid4()
        ws = await svc.create_workspace(
            owner_id=owner_id,
            name="???",  # slugify results in empty string
        )
        assert ws.slug == "workspace"

    async def test_create_workspace_duplicate_slug_raises_conflict(self):
        existing = _make_workspace()
        svc = _make_service(existing_slug_workspace=existing)
        with pytest.raises(ConflictError) as exc_info:
            await svc.create_workspace(
                owner_id=uuid4(),
                name="Existing Team",
            )
        assert "already taken" in str(exc_info.value)


class TestGetWorkspace:
    async def test_get_existing_workspace(self):
        ws = _make_workspace()
        svc = _make_service(workspace=ws)
        result = await svc.get_workspace(ws.id, ws.owner_id)
        assert result == ws
        svc._auth.require_workspace_member.assert_called_once_with(ws.owner_id, ws.id)

    async def test_get_missing_workspace_raises_404(self):
        svc = _make_service(workspace=None)
        with pytest.raises(NotFoundError):
            await svc.get_workspace(uuid4(), uuid4())


class TestUpdateWorkspace:
    async def test_update_workspace_name_and_description(self):
        ws = _make_workspace()
        svc = _make_service(workspace=ws)
        result = await svc.update_workspace(
            ws.id, ws.owner_id, name="Renamed", description="New desc"
        )
        assert result.name == "Renamed"
        assert result.description == "New desc"
        svc._auth.require_workspace_owner.assert_called_once_with(ws.owner_id, ws.id)

    async def test_update_missing_workspace_raises_404(self):
        svc = _make_service(workspace=None)
        with pytest.raises(NotFoundError):
            await svc.update_workspace(uuid4(), uuid4(), name="Renamed")


class TestDeleteWorkspace:
    async def test_delete_existing_workspace(self):
        ws = _make_workspace()
        svc = _make_service(workspace=ws)
        await svc.delete_workspace(ws.id, ws.owner_id)
        svc._ws_repo.delete.assert_called_once_with(ws)

    async def test_delete_missing_workspace_raises_404(self):
        svc = _make_service(workspace=None)
        with pytest.raises(NotFoundError):
            await svc.delete_workspace(uuid4(), uuid4())


class TestWorkspaceMembers:
    async def test_add_member_success(self):
        target_user = MagicMock()
        target_user.id = uuid4()
        svc = _make_service(target_user=target_user, existing_member=None)

        ws_id = uuid4()
        owner_id = uuid4()
        await svc.add_member(ws_id, owner_id, target_user.id, WorkspaceRole.MEMBER)
        svc._ws_repo.add_member.assert_called_once_with(ws_id, target_user.id, WorkspaceRole.MEMBER)

    async def test_add_member_missing_user_raises_404(self):
        svc = _make_service(target_user=None)
        with pytest.raises(NotFoundError):
            await svc.add_member(uuid4(), uuid4(), uuid4())

    async def test_add_member_already_member_raises_conflict(self):
        target_user = MagicMock()
        existing = MagicMock(spec=WorkspaceMember)
        svc = _make_service(target_user=target_user, existing_member=existing)
        with pytest.raises(ConflictError):
            await svc.add_member(uuid4(), uuid4(), uuid4())

    async def test_remove_member_success(self):
        owner_id = uuid4()
        target_id = uuid4()
        ws = _make_workspace(owner_id=owner_id)
        member = MagicMock(spec=WorkspaceMember)
        svc = _make_service(workspace=ws, existing_member=member)

        await svc.remove_member(ws.id, owner_id, target_id)
        svc._ws_repo.remove_member.assert_called_once_with(member)

    async def test_remove_owner_raises_conflict(self):
        owner_id = uuid4()
        ws = _make_workspace(owner_id=owner_id)
        svc = _make_service(workspace=ws)

        with pytest.raises(ConflictError) as exc_info:
            await svc.remove_member(ws.id, owner_id, owner_id)
        assert "Cannot remove the workspace owner" in str(exc_info.value)

    async def test_remove_missing_member_raises_404(self):
        owner_id = uuid4()
        target_id = uuid4()
        ws = _make_workspace(owner_id=owner_id)
        svc = _make_service(workspace=ws, existing_member=None)

        with pytest.raises(NotFoundError):
            await svc.remove_member(ws.id, owner_id, target_id)

    async def test_list_members_success(self):
        member = MagicMock(spec=WorkspaceMember)
        svc = _make_service(existing_member=member)
        ws_id = uuid4()
        user_id = uuid4()
        members = await svc.list_members(ws_id, user_id)
        assert members == [member]
        svc._auth.require_workspace_member.assert_called_once_with(user_id, ws_id)
