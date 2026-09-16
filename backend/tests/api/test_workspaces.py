"""API integration tests — workspace endpoints.

These tests run against a real PostgreSQL instance via the test session fixture.
Each test is isolated by transaction rollback.
"""

from __future__ import annotations

from httpx import AsyncClient


class TestWorkspaceCreate:
    async def test_create_workspace_success(self, api_client: AsyncClient):
        resp = await api_client.post(
            "/api/v1/workspaces",
            json={"name": "My Workspace", "description": "Test workspace"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "My Workspace"
        assert data["slug"] == "my-workspace"
        assert "id" in data

    async def test_create_workspace_duplicate_slug_fails(self, api_client: AsyncClient):
        # Create first
        await api_client.post(
            "/api/v1/workspaces", json={"name": "Dup", "slug": "dup-slug"}
        )
        # Create second with same slug
        resp = await api_client.post(
            "/api/v1/workspaces", json={"name": "Dup 2", "slug": "dup-slug"}
        )
        assert resp.status_code == 409

    async def test_create_workspace_requires_auth(self, api_client: AsyncClient):
        """Remove auth header and verify 401."""
        resp = await api_client.post(
            "/api/v1/workspaces",
            json={"name": "No Auth"},
            headers={"Authorization": ""},
        )
        assert resp.status_code == 401

    async def test_create_workspace_validates_name(self, api_client: AsyncClient):
        resp = await api_client.post("/api/v1/workspaces", json={"name": ""})
        assert resp.status_code == 422


class TestWorkspaceList:
    async def test_list_workspaces_empty(self, api_client: AsyncClient):
        resp = await api_client.get("/api/v1/workspaces")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    async def test_list_workspaces_returns_owned(self, api_client: AsyncClient):
        await api_client.post("/api/v1/workspaces", json={"name": "WS 1"})
        await api_client.post("/api/v1/workspaces", json={"name": "WS 2"})
        resp = await api_client.get("/api/v1/workspaces")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 2

    async def test_list_workspaces_pagination(self, api_client: AsyncClient):
        for i in range(5):
            await api_client.post("/api/v1/workspaces", json={"name": f"WS {i}"})
        resp = await api_client.get("/api/v1/workspaces?page=1&page_size=2")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 2
        assert data["page"] == 1
        assert data["page_size"] == 2


class TestWorkspaceGet:
    async def test_get_existing_workspace(self, api_client: AsyncClient):
        created = (
            await api_client.post("/api/v1/workspaces", json={"name": "Get Test"})
        ).json()
        resp = await api_client.get(f"/api/v1/workspaces/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]

    async def test_get_nonexistent_workspace_returns_404(self, api_client: AsyncClient):
        resp = await api_client.get(
            "/api/v1/workspaces/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404


class TestWorkspaceUpdate:
    async def test_update_workspace_name(self, api_client: AsyncClient):
        created = (
            await api_client.post("/api/v1/workspaces", json={"name": "Old Name"})
        ).json()
        resp = await api_client.patch(
            f"/api/v1/workspaces/{created['id']}",
            json={"name": "New Name"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"


class TestWorkspaceDelete:
    async def test_owner_can_delete_workspace(self, api_client: AsyncClient):
        created = (
            await api_client.post("/api/v1/workspaces", json={"name": "To Delete"})
        ).json()
        resp = await api_client.delete(f"/api/v1/workspaces/{created['id']}")
        assert resp.status_code == 204

    async def test_deleted_workspace_not_found(self, api_client: AsyncClient):
        created = (
            await api_client.post("/api/v1/workspaces", json={"name": "Gone"})
        ).json()
        await api_client.delete(f"/api/v1/workspaces/{created['id']}")
        resp = await api_client.get(f"/api/v1/workspaces/{created['id']}")
        assert resp.status_code == 404


class TestWorkspaceMembers:
    async def test_list_members_includes_owner(self, api_client: AsyncClient):
        ws = (
            await api_client.post("/api/v1/workspaces", json={"name": "Members WS"})
        ).json()
        resp = await api_client.get(f"/api/v1/workspaces/{ws['id']}/members")
        assert resp.status_code == 200
        members = resp.json()
        assert len(members) >= 1
        assert any(m["role"] == "owner" for m in members)
