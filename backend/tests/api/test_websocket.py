from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.auth import create_access_token
from app.main import create_app


def test_websocket_connect():
    app = create_app()
    user_id = uuid4()
    token = create_access_token(
        user_id=user_id, email="test@example.com", username="testuser"
    )
    with TestClient(app) as client:
        with client.websocket_connect(f"/ws?token={token}") as websocket:
            websocket.send_json({"action": "subscribe", "channel": f"user:{user_id}"})
            assert True


def test_websocket_reject_invalid_token():
    app = create_app()
    with TestClient(app) as client:
        with pytest.raises(Exception):
            with client.websocket_connect("/ws?token=invalid") as websocket:
                websocket.receive_json()
