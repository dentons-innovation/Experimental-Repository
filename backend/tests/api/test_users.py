"""Tests for user retrieval endpoints."""

from __future__ import annotations

from uuid import uuid4

from httpx import AsyncClient


class TestUsers:
    async def test_get_me(self, api_client: AsyncClient):
        resp = await api_client.get("/api/v1/users/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "apitest@example.com"
        assert data["username"] == "apitestuser"

    async def test_get_user_by_id(self, api_client: AsyncClient):
        user_id = api_client._test_user.id  # type: ignore[attr-defined]
        resp = await api_client.get(f"/api/v1/users/{user_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(user_id)
        assert data["username"] == "apitestuser"

    async def test_get_nonexistent_user_returns_404(self, api_client: AsyncClient):
        resp = await api_client.get(f"/api/v1/users/{uuid4()}")
        assert resp.status_code == 404
