"""API tests for the connections endpoints."""

import pytest
from httpx import AsyncClient

from app.domain.enums import ConnectionStatus
from app.domain.models import User, UserConnection
from tests.conftest import create_user


@pytest.fixture
async def target_user(db_session) -> User:
    return await create_user(db_session, "target", "target@test.com", "Target User")


@pytest.mark.asyncio
class TestSearchUsers:
    async def test_search_users_success(
        self,
        api_client: AsyncClient,
        target_user: User,
    ):
        response = await api_client.get("/api/v1/connections/users/search?q=target")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == str(target_user.id)


@pytest.mark.asyncio
class TestSendConnectionRequest:
    async def test_send_request_success(
        self,
        api_client: AsyncClient,
        target_user: User,
    ):
        response = await api_client.post(
            "/api/v1/connections",
            json={"receiver_id": str(target_user.id)},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending"

    async def test_send_request_to_self_fails(
        self,
        api_client: AsyncClient,
    ):
        test_user = api_client._test_user
        response = await api_client.post(
            "/api/v1/connections",
            json={"receiver_id": str(test_user.id)},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
class TestAcceptConnection:
    async def test_accept_success(
        self,
        api_client: AsyncClient,
        target_user: User,
        db_session,
    ):
        test_user = api_client._test_user
        # Target sends request to test user
        conn = UserConnection(
            user_lo=min(test_user.id, target_user.id),
            user_hi=max(test_user.id, target_user.id),
            requester_id=target_user.id,
            status=ConnectionStatus.PENDING,
        )
        db_session.add(conn)
        await db_session.commit()
        await db_session.refresh(conn)

        response = await api_client.post(f"/api/v1/connections/{conn.id}/accept")
        assert response.status_code == 200
        assert response.json()["status"] == "accepted"


@pytest.mark.asyncio
class TestRejectConnection:
    async def test_reject_success(
        self,
        api_client: AsyncClient,
        target_user: User,
        db_session,
    ):
        test_user = api_client._test_user
        # Target sends request to test user
        conn = UserConnection(
            user_lo=min(test_user.id, target_user.id),
            user_hi=max(test_user.id, target_user.id),
            requester_id=target_user.id,
            status=ConnectionStatus.PENDING,
        )
        db_session.add(conn)
        await db_session.commit()
        await db_session.refresh(conn)

        response = await api_client.post(f"/api/v1/connections/{conn.id}/reject")
        assert response.status_code == 204


@pytest.mark.asyncio
class TestRemoveConnection:
    async def test_remove_success(
        self,
        api_client: AsyncClient,
        target_user: User,
        db_session,
    ):
        test_user = api_client._test_user
        conn = UserConnection(
            user_lo=min(test_user.id, target_user.id),
            user_hi=max(test_user.id, target_user.id),
            requester_id=target_user.id,
            status=ConnectionStatus.ACCEPTED,
        )
        db_session.add(conn)
        await db_session.commit()
        await db_session.refresh(conn)

        response = await api_client.delete(f"/api/v1/connections/{conn.id}")
        assert response.status_code == 204
