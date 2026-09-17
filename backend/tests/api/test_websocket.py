import json
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from starlette.websockets import WebSocketDisconnect

from app.core.config import get_settings
from app.infrastructure.auth import JWTVerifier, create_access_token
from app.infrastructure.realtime.manager import (
    RealtimeConnectionManager,
    RealtimeSubscriptionManager,
)
from app.infrastructure.realtime.router import websocket_endpoint


@pytest.mark.asyncio
async def test_websocket_reject_invalid_token():
    mock_ws = AsyncMock()
    mock_ws.query_params = {"token": "invalid"}
    mock_ws.app.state.jwt_verifier = JWTVerifier(get_settings())
    mock_ws.close = AsyncMock()

    await websocket_endpoint(mock_ws)
    mock_ws.close.assert_called_once_with(code=4001, reason="Authentication failed")


@pytest.mark.asyncio
async def test_websocket_connect_and_disconnect():
    user_id = uuid4()
    token = create_access_token(
        user_id=user_id, email="test@example.com", username="testuser"
    )

    mock_ws = AsyncMock()
    mock_ws.query_params = {"token": token}
    conn_manager = RealtimeConnectionManager()
    sub_manager = RealtimeSubscriptionManager()
    mock_ws.app.state.realtime_conn_manager = conn_manager
    mock_ws.app.state.realtime_sub_manager = sub_manager
    mock_ws.app.state.jwt_verifier = JWTVerifier(get_settings())

    # Simulate client disconnect on first receive_text
    mock_ws.receive_text = AsyncMock(side_effect=WebSocketDisconnect(code=1000))

    await websocket_endpoint(mock_ws)

    mock_ws.accept.assert_called_once()
    assert len(conn_manager.get_connections(user_id)) == 0


@pytest.mark.asyncio
async def test_websocket_message_handling():
    user_id = uuid4()
    token = create_access_token(
        user_id=user_id, email="test@example.com", username="testuser"
    )

    mock_ws = AsyncMock()
    mock_ws.query_params = {"token": token}
    conn_manager = RealtimeConnectionManager()
    sub_manager = RealtimeSubscriptionManager()
    mock_ws.app.state.realtime_conn_manager = conn_manager
    mock_ws.app.state.realtime_sub_manager = sub_manager
    mock_ws.app.state.jwt_verifier = JWTVerifier(get_settings())

    sent_messages: list[str] = []

    async def fake_send_text(data: str):
        sent_messages.append(data)

    mock_ws.send_text = AsyncMock(side_effect=fake_send_text)

    # Sequence of incoming messages, then disconnect
    mock_ws.receive_text = AsyncMock(
        side_effect=[
            "invalid json",
            json.dumps({"action": "unknown"}),
            json.dumps({"action": "unsubscribe", "channel": f"user:{user_id}"}),
            WebSocketDisconnect(code=1000),
        ]
    )

    await websocket_endpoint(mock_ws)

    assert len(sent_messages) == 3
    assert "Invalid JSON" in sent_messages[0]
    assert "Missing 'action' or 'channel'" in sent_messages[1]
    assert "unsubscribed" in sent_messages[2]
