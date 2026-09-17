"""API tests for the workspace members endpoints."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.domain.enums import WorkspaceRole
from app.domain.models import User, Workspace
from tests.conftest import create_user, create_workspace


@pytest.fixture
async def other_user(db_session) -> User:
    return await create_user(
        db_session, "other", "other@test.com", "Other User"
    )


@pytest.fixture
async def test_workspace(db_session, api_client: AsyncClient) -> Workspace:
    return await create_workspace(db_session, owner=api_client._test_user)


@pytest.mark.asyncio
class TestWorkspaceMembersAPI:
    async def test_update_member_role_success(
        self,
        api_client: AsyncClient,
        test_workspace: Workspace,
        other_user: User,
    ):
        # Add the other user as a member first
        add_resp = await api_client.post(
            f"/api/v1/workspaces/{test_workspace.id}/members",
            json={"user_id": str(other_user.id), "role": WorkspaceRole.MEMBER},
        )
        assert add_resp.status_code == 201

        # Now update their role to OWNER
        update_resp = await api_client.put(
            f"/api/v1/workspaces/{test_workspace.id}/members/{other_user.id}",
            json={"role": WorkspaceRole.OWNER},
        )
        assert update_resp.status_code == 200
        data = update_resp.json()
        assert data["role"] == WorkspaceRole.OWNER

    async def test_update_missing_member_fails(
        self,
        api_client: AsyncClient,
        test_workspace: Workspace,
    ):
        update_resp = await api_client.put(
            f"/api/v1/workspaces/{test_workspace.id}/members/{uuid4()}",
            json={"role": WorkspaceRole.OWNER},
        )
        assert update_resp.status_code == 404
