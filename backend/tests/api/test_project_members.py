"""API tests for the project members endpoints."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.domain.enums import ProjectRole, WorkspaceRole
from app.domain.models import Project, User, Workspace
from tests.conftest import create_project, create_user, create_workspace


@pytest.fixture
async def other_user(db_session) -> User:
    return await create_user(
        db_session, "otherproj", "otherproj@test.com", "Other Proj User"
    )


@pytest.fixture
async def test_workspace(db_session, api_client: AsyncClient) -> Workspace:
    return await create_workspace(db_session, owner=api_client._test_user)


@pytest.fixture
async def test_project(
    db_session, api_client: AsyncClient, test_workspace: Workspace
) -> Project:
    return await create_project(
        db_session, workspace=test_workspace, creator=api_client._test_user
    )


@pytest.mark.asyncio
class TestProjectMembersAPI:
    async def test_update_member_role_success(
        self,
        api_client: AsyncClient,
        test_workspace: Workspace,
        test_project: Project,
        other_user: User,
    ):
        # Must add to workspace first
        await api_client.post(
            f"/api/v1/workspaces/{test_workspace.id}/members",
            json={"user_id": str(other_user.id), "role": WorkspaceRole.MEMBER},
        )

        # Add the other user as a project member first
        add_resp = await api_client.post(
            f"/api/v1/projects/{test_project.id}/members",
            json={"user_id": str(other_user.id), "role": ProjectRole.MEMBER},
        )
        assert add_resp.status_code == 201

        # Now update their role to ADMIN
        update_resp = await api_client.put(
            f"/api/v1/projects/{test_project.id}/members/{other_user.id}",
            json={"role": ProjectRole.ADMIN},
        )
        assert update_resp.status_code == 200
        data = update_resp.json()
        assert data["role"] == ProjectRole.ADMIN

    async def test_update_missing_member_fails(
        self,
        api_client: AsyncClient,
        test_project: Project,
    ):
        update_resp = await api_client.put(
            f"/api/v1/projects/{test_project.id}/members/{uuid4()}",
            json={"role": ProjectRole.ADMIN},
        )
        assert update_resp.status_code == 404
