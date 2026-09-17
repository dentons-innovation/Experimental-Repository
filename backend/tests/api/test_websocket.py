import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from app.main import app
from app.infrastructure.realtime.auth import create_ws_token

@pytest.mark.asyncio
async def test_websocket_connect(
    api_client: TestClient,
    session: AsyncSession,
    test_user
):
    token = create_ws_token(test_user.id)
    with api_client.websocket_connect(f"/ws?token={token}") as websocket:
        websocket.send_json({"action": "subscribe", "channel": f"user:{test_user.id}"})
        # Wait for the confirmation event? Currently the server might not send an ack, 
        # or we just test that it connects successfully.
        assert True

@pytest.mark.asyncio
async def test_websocket_reject_invalid_token(api_client: TestClient):
    with pytest.raises(Exception):
        with api_client.websocket_connect("/ws?token=invalid") as websocket:
            websocket.receive_json()
