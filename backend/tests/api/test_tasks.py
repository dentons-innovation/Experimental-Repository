"""Task API integration tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.fixture
async def workspace_and_project(api_client: AsyncClient):
    ws = (
        await api_client.post("/api/v1/workspaces", json={"name": "Task Test WS"})
    ).json()
    proj = (
        await api_client.post(
            f"/api/v1/workspaces/{ws['id']}/projects",
            json={"name": "Task Test Proj"},
        )
    ).json()
    return ws, proj


class TestTaskCreate:
    async def test_create_task_minimal(
        self, api_client: AsyncClient, workspace_and_project
    ):
        _, proj = workspace_and_project
        resp = await api_client.post(
            f"/api/v1/projects/{proj['id']}/tasks",
            json={"title": "My first task"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "My first task"
        assert data["status"] == "backlog"
        assert data["priority"] == "medium"
        assert data["version"] == 0

    async def test_create_task_with_all_fields(
        self, api_client: AsyncClient, workspace_and_project
    ):
        _, proj = workspace_and_project
        resp = await api_client.post(
            f"/api/v1/projects/{proj['id']}/tasks",
            json={
                "title": "Full task",
                "description": "A detailed description",
                "status": "todo",
                "priority": "high",
                "due_date": "2026-12-31",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "todo"
        assert data["priority"] == "high"
        assert data["due_date"] == "2026-12-31"

    async def test_create_task_validates_title(
        self, api_client: AsyncClient, workspace_and_project
    ):
        _, proj = workspace_and_project
        resp = await api_client.post(
            f"/api/v1/projects/{proj['id']}/tasks", json={"title": ""}
        )
        assert resp.status_code == 422


class TestTaskList:
    async def test_list_tasks_empty(
        self, api_client: AsyncClient, workspace_and_project
    ):
        _, proj = workspace_and_project
        resp = await api_client.get(f"/api/v1/projects/{proj['id']}/tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_filter_by_status(
        self, api_client: AsyncClient, workspace_and_project
    ):
        _, proj = workspace_and_project
        await api_client.post(
            f"/api/v1/projects/{proj['id']}/tasks",
            json={"title": "Todo task", "status": "todo"},
        )
        await api_client.post(
            f"/api/v1/projects/{proj['id']}/tasks",
            json={"title": "Backlog task", "status": "backlog"},
        )
        resp = await api_client.get(f"/api/v1/projects/{proj['id']}/tasks?status=todo")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "todo"

    async def test_filter_by_priority(
        self, api_client: AsyncClient, workspace_and_project
    ):
        _, proj = workspace_and_project
        await api_client.post(
            f"/api/v1/projects/{proj['id']}/tasks",
            json={"title": "Critical task", "priority": "critical"},
        )
        resp = await api_client.get(
            f"/api/v1/projects/{proj['id']}/tasks?priority=critical"
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    async def test_search_by_title(
        self, api_client: AsyncClient, workspace_and_project
    ):
        _, proj = workspace_and_project
        await api_client.post(
            f"/api/v1/projects/{proj['id']}/tasks",
            json={"title": "Unique searchable task xyz"},
        )
        resp = await api_client.get(f"/api/v1/projects/{proj['id']}/tasks?search=xyz")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1


class TestTaskUpdate:
    async def test_update_task_title(
        self, api_client: AsyncClient, workspace_and_project
    ):
        _, proj = workspace_and_project
        task = (
            await api_client.post(
                f"/api/v1/projects/{proj['id']}/tasks",
                json={"title": "Original Title"},
            )
        ).json()

        resp = await api_client.patch(
            f"/api/v1/tasks/{task['id']}",
            json={"title": "Updated Title", "version": 0},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Title"
        assert resp.json()["version"] == 1

    async def test_update_task_status(
        self, api_client: AsyncClient, workspace_and_project
    ):
        _, proj = workspace_and_project
        task = (
            await api_client.post(
                f"/api/v1/projects/{proj['id']}/tasks", json={"title": "T"}
            )
        ).json()
        resp = await api_client.patch(
            f"/api/v1/tasks/{task['id']}",
            json={"status": "in_progress", "version": 0},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "in_progress"


class TestTaskDelete:
    async def test_admin_can_delete_task(
        self, api_client: AsyncClient, workspace_and_project
    ):
        _, proj = workspace_and_project
        task = (
            await api_client.post(
                f"/api/v1/projects/{proj['id']}/tasks", json={"title": "Delete Me"}
            )
        ).json()
        resp = await api_client.delete(f"/api/v1/tasks/{task['id']}")
        assert resp.status_code == 204

    async def test_deleted_task_returns_404(
        self, api_client: AsyncClient, workspace_and_project
    ):
        _, proj = workspace_and_project
        task = (
            await api_client.post(
                f"/api/v1/projects/{proj['id']}/tasks", json={"title": "Gone"}
            )
        ).json()
        await api_client.delete(f"/api/v1/tasks/{task['id']}")
        resp = await api_client.get(f"/api/v1/tasks/{task['id']}")
        assert resp.status_code == 404


class TestTaskActivity:
    async def test_activity_created_on_task_create(
        self, api_client: AsyncClient, workspace_and_project
    ):
        _, proj = workspace_and_project
        task = (
            await api_client.post(
                f"/api/v1/projects/{proj['id']}/tasks", json={"title": "Activity Task"}
            )
        ).json()
        resp = await api_client.get(f"/api/v1/tasks/{task['id']}/activity")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert any(a["action"] == "task_created" for a in data["items"])

    async def test_activity_created_on_status_change(
        self, api_client: AsyncClient, workspace_and_project
    ):
        _, proj = workspace_and_project
        task = (
            await api_client.post(
                f"/api/v1/projects/{proj['id']}/tasks", json={"title": "Status Task"}
            )
        ).json()
        await api_client.patch(
            f"/api/v1/tasks/{task['id']}",
            json={"status": "done", "version": 0},
        )
        resp = await api_client.get(f"/api/v1/tasks/{task['id']}/activity")
        actions = [a["action"] for a in resp.json()["items"]]
        assert "status_changed" in actions


class TestTaskGet:
    async def test_get_existing_task_success(
        self, api_client: AsyncClient, workspace_and_project
    ):
        _, proj = workspace_and_project
        created = (
            await api_client.post(
                f"/api/v1/projects/{proj['id']}/tasks",
                json={"title": "Fetchable task"},
            )
        ).json()
        resp = await api_client.get(f"/api/v1/tasks/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]


class TestTaskLabelsApi:
    async def test_add_and_remove_label_from_task(
        self, api_client: AsyncClient, workspace_and_project
    ):
        ws, proj = workspace_and_project
        label = (
            await api_client.post(
                f"/api/v1/workspaces/{ws['id']}/labels",
                json={"name": "Frontend", "color": "#3b82f6"},
            )
        ).json()

        task = (
            await api_client.post(
                f"/api/v1/projects/{proj['id']}/tasks",
                json={"title": "Task with label"},
            )
        ).json()

        # Add label
        add_resp = await api_client.post(
            f"/api/v1/tasks/{task['id']}/labels",
            json={"label_id": label["id"]},
        )
        assert add_resp.status_code == 200
        assert any(l["id"] == label["id"] for l in add_resp.json()["labels"])

        # Filter by label
        filter_resp = await api_client.get(
            f"/api/v1/projects/{proj['id']}/tasks?label_ids={label['id']}"
        )
        assert filter_resp.status_code == 200
        assert filter_resp.json()["total"] == 1

        # Remove label
        del_resp = await api_client.delete(
            f"/api/v1/tasks/{task['id']}/labels/{label['id']}"
        )
        assert del_resp.status_code == 200
        assert not any(l["id"] == label["id"] for l in del_resp.json()["labels"])


class TestTaskListAdvancedFilters:
    async def test_filter_and_sort(
        self, api_client: AsyncClient, workspace_and_project
    ):
        _, proj = workspace_and_project
        await api_client.post(
            f"/api/v1/projects/{proj['id']}/tasks",
            json={"title": "Task A", "priority": "low"},
        )
        await api_client.post(
            f"/api/v1/projects/{proj['id']}/tasks",
            json={"title": "Task B", "priority": "high"},
        )

        resp = await api_client.get(
            f"/api/v1/projects/{proj['id']}/tasks?sort_by=priority&sort_order=asc"
        )
        assert resp.status_code == 200
        assert resp.json()["total"] >= 2
