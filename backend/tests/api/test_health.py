"""Tests for health and readiness endpoints."""

from __future__ import annotations

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import dependencies
from app.main import create_app


class TestHealth:
    async def test_health_check(self):
        app = create_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/health")
            assert resp.status_code == 200
            assert resp.json() == {"status": "ok"}

    async def test_readiness_check(self, db_session: AsyncSession):
        app = create_app()

        async def override_db():
            yield db_session

        app.dependency_overrides[dependencies.get_db_session] = override_db
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/readiness")
            assert resp.status_code == 200
            assert resp.json() == {"status": "ready"}
