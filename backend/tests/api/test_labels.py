"""Tests for label endpoints."""

from __future__ import annotations

from httpx import AsyncClient


class TestLabelEndpoints:
    async def _setup_workspace(self, client: AsyncClient) -> dict:
        resp = await client.post("/api/v1/workspaces", json={"name": "Label WS"})
        assert resp.status_code == 201
        return resp.json()

    async def test_label_crud(self, api_client: AsyncClient):
        ws = await self._setup_workspace(api_client)

        # 1. Create label
        create_resp = await api_client.post(
            f"/api/v1/workspaces/{ws['id']}/labels",
            json={"name": "Bug", "color": "#FF0000"},
        )
        assert create_resp.status_code == 201
        label = create_resp.json()
        assert label["name"] == "Bug"
        assert label["color"] == "#FF0000"
        assert label["workspace_id"] == ws["id"]

        # 2. List labels
        list_resp = await api_client.get(f"/api/v1/workspaces/{ws['id']}/labels")
        assert list_resp.status_code == 200
        labels = list_resp.json()
        assert any(lbl["id"] == label["id"] for lbl in labels)

        # 3. Update label
        update_resp = await api_client.patch(
            f"/api/v1/labels/{label['id']}",
            json={"name": "Critical Bug", "color": "#990000"},
        )
        assert update_resp.status_code == 200
        updated = update_resp.json()
        assert updated["name"] == "Critical Bug"
        assert updated["color"] == "#990000"

        # 4. Delete label
        del_resp = await api_client.delete(f"/api/v1/labels/{label['id']}")
        assert del_resp.status_code == 204
