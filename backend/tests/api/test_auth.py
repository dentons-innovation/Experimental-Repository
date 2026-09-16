"""Tests for email/password authentication and JWT tokens."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import dependencies
from app.main import create_app


class TestAuthentication:
    """Test register, login, and me endpoints."""

    async def test_register_and_login_flow(self, db_session: AsyncSession):
        app = create_app()

        async def override_db():
            yield db_session

        app.dependency_overrides[dependencies.get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # 1. Register new user
            reg_resp = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "newuser@example.com",
                    "username": "newuser",
                    "full_name": "New User",
                    "password": "strongpassword123",
                },
            )
            assert reg_resp.status_code == 201
            reg_data = reg_resp.json()
            assert "access_token" in reg_data
            assert reg_data["user"]["email"] == "newuser@example.com"
            assert reg_data["user"]["username"] == "newuser"

            token = reg_data["access_token"]

            # 2. Duplicate registration fails
            dup_resp = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "newuser@example.com",
                    "username": "differentuser",
                    "full_name": "Duplicate User",
                    "password": "strongpassword123",
                },
            )
            assert dup_resp.status_code == 409

            # 3. Login with correct password
            login_resp = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": "newuser@example.com",
                    "password": "strongpassword123",
                },
            )
            assert login_resp.status_code == 200
            login_data = login_resp.json()
            assert "access_token" in login_data

            # 4. Login with invalid password fails
            bad_login = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": "newuser@example.com",
                    "password": "wrongpassword",
                },
            )
            assert bad_login.status_code == 401

            # 5. Access /auth/me with Bearer token
            me_resp = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert me_resp.status_code == 200
            assert me_resp.json()["email"] == "newuser@example.com"

            # 6. Access /auth/me without token fails
            no_auth_resp = await client.get("/api/v1/auth/me")
            assert no_auth_resp.status_code == 401
