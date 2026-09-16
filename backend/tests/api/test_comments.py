"""Tests for comment endpoints."""

from __future__ import annotations

from httpx import AsyncClient


class TestCommentEndpoints:
    async def _setup_task(self, client: AsyncClient) -> dict:
        ws = (
            await client.post("/api/v1/workspaces", json={"name": "Comment WS"})
        ).json()
        proj = (
            await client.post(
                f"/api/v1/workspaces/{ws['id']}/projects",
                json={"name": "Comment Proj"},
            )
        ).json()
        task = (
            await client.post(
                f"/api/v1/projects/{proj['id']}/tasks",
                json={"title": "Comment Task"},
            )
        ).json()
        return task

    async def test_comment_lifecycle(self, api_client: AsyncClient):
        task = await self._setup_task(api_client)

        # 1. Create comment
        create_resp = await api_client.post(
            f"/api/v1/tasks/{task['id']}/comments",
            json={"body": "This is a test comment."},
        )
        assert create_resp.status_code == 201
        comment = create_resp.json()
        assert comment["body"] == "This is a test comment."
        assert comment["task_id"] == task["id"]

        # 2. List comments
        list_resp = await api_client.get(f"/api/v1/tasks/{task['id']}/comments")
        assert list_resp.status_code == 200
        data = list_resp.json()
        assert data["total"] >= 1
        assert any(c["id"] == comment["id"] for c in data["items"])

        # 3. Update comment
        update_resp = await api_client.patch(
            f"/api/v1/comments/{comment['id']}",
            json={"body": "Updated comment body."},
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["body"] == "Updated comment body."

        # 4. Delete comment
        del_resp = await api_client.delete(f"/api/v1/comments/{comment['id']}")
        assert del_resp.status_code == 204
