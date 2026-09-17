"""Tests for project endpoints."""

from __future__ import annotations

from httpx import AsyncClient


class TestProjectEndpoints:
    async def _create_workspace(self, client: AsyncClient) -> dict:
        resp = await client.post("/api/v1/workspaces", json={"name": "Project WS"})
        assert resp.status_code == 201
        return resp.json()

    async def test_create_and_get_project(self, api_client: AsyncClient):
        ws = await self._create_workspace(api_client)
        resp = await api_client.post(
            f"/api/v1/workspaces/{ws['id']}/projects",
            json={
                "name": "Alpha Project",
                "description": "Alpha Description",
            },
        )
        assert resp.status_code == 201
        proj = resp.json()
        assert proj["name"] == "Alpha Project"
        assert proj["description"] == "Alpha Description"
        assert proj["workspace_id"] == ws["id"]

        # Get project
        get_resp = await api_client.get(f"/api/v1/projects/{proj['id']}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == proj["id"]

    async def test_list_projects(self, api_client: AsyncClient):
        ws = await self._create_workspace(api_client)
        await api_client.post(
            f"/api/v1/workspaces/{ws['id']}/projects",
            json={"name": "Proj 1"},
        )
        await api_client.post(
            f"/api/v1/workspaces/{ws['id']}/projects",
            json={"name": "Proj 2"},
        )

        resp = await api_client.get(f"/api/v1/workspaces/{ws['id']}/projects")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2
        assert len(data["items"]) >= 2

    async def test_update_project(self, api_client: AsyncClient):
        ws = await self._create_workspace(api_client)
        proj = (
            await api_client.post(
                f"/api/v1/workspaces/{ws['id']}/projects",
                json={"name": "Old Project Name", "description": "Old Desc"},
            )
        ).json()

        update_resp = await api_client.patch(
            f"/api/v1/projects/{proj['id']}",
            json={"name": "New Project Name", "description": "New Desc"},
        )
        assert update_resp.status_code == 200
        updated = update_resp.json()
        assert updated["name"] == "New Project Name"
        assert updated["description"] == "New Desc"

    async def test_delete_project(self, api_client: AsyncClient):
        ws = await self._create_workspace(api_client)
        proj = (
            await api_client.post(
                f"/api/v1/workspaces/{ws['id']}/projects",
                json={"name": "To Delete"},
            )
        ).json()

        del_resp = await api_client.delete(f"/api/v1/projects/{proj['id']}")
        assert del_resp.status_code == 204

        get_resp = await api_client.get(f"/api/v1/projects/{proj['id']}")
        assert get_resp.status_code == 404

    async def test_project_members_management(self, api_client_factory):
        client_owner, owner = await api_client_factory(
            "owner_p", "owner_p@example.com", "ownerp"
        )
        client_member, member = await api_client_factory(
            "member_p", "member_p@example.com", "memberp"
        )

        ws = (
            await client_owner.post(
                "/api/v1/workspaces", json={"name": "Collab Workspace"}
            )
        ).json()

        # Add member to workspace first
        await client_owner.post(
            f"/api/v1/workspaces/{ws['id']}/members",
            json={"user_id": str(member.id), "role": "member"},
        )

        # Create project
        proj = (
            await client_owner.post(
                f"/api/v1/workspaces/{ws['id']}/projects",
                json={"name": "Shared Project"},
            )
        ).json()

        # Add member to project
        add_resp = await client_owner.post(
            f"/api/v1/projects/{proj['id']}/members",
            json={"user_id": str(member.id), "role": "member"},
        )
        assert add_resp.status_code == 201

        # List members
        members_resp = await client_owner.get(f"/api/v1/projects/{proj['id']}/members")
        assert members_resp.status_code == 200
        members = members_resp.json()
        assert any(m["user"]["id"] == str(member.id) for m in members)

        # Remove member
        rem_resp = await client_owner.delete(
            f"/api/v1/projects/{proj['id']}/members/{member.id}"
        )
        assert rem_resp.status_code == 204
