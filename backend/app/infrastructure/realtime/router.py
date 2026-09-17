"""WebSocket endpoint for real-time event subscriptions.

Protocol:
    1. Client connects to ``/ws?token=<jwt>``
    2. Server authenticates the token; rejects with 4001 if invalid
    3. Server auto-subscribes client to ``user:<user_id>``
    4. Client sends JSON commands:
        {"action": "subscribe",   "channel": "workspace:abc-123"}
        {"action": "unsubscribe", "channel": "workspace:abc-123"}
    5. Server validates authorization before subscribing
    6. Server pushes events as JSON:
        {"channel": "...", "event": "...", "data": {...}}
    7. On disconnect, all subscriptions are cleaned up
"""

from __future__ import annotations

import json
from uuid import UUID

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session_factory
from app.domain.exceptions import AuthenticationError
from app.infrastructure.auth import JWTVerifier
from app.infrastructure.realtime.auth import authenticate_ws_token
from app.infrastructure.realtime.manager import (
    RealtimeConnectionManager,
    RealtimeSubscriptionManager,
)
from app.repositories.project_repository import ProjectRepository
from app.repositories.workspace_repository import WorkspaceRepository

logger = structlog.get_logger(__name__)

ws_router = APIRouter()


async def _check_channel_authorization(
    channel: str,
    user_id: UUID,
    session: AsyncSession,
) -> bool:
    """Verify the user is authorized to subscribe to the given channel.

    Returns True if authorized, False otherwise.
    User channels are always authorized for the authenticated user.
    """
    parts = channel.split(":", 1)
    if len(parts) != 2:
        return False

    channel_type, channel_id = parts

    if channel_type == "user":
        # Users can only subscribe to their own user channel
        try:
            return UUID(channel_id) == user_id
        except ValueError:
            return False

    if channel_type == "workspace":
        try:
            workspace_id = UUID(channel_id)
        except ValueError:
            return False
        ws_repo = WorkspaceRepository(session)
        member = await ws_repo.get_member(workspace_id, user_id)
        return member is not None

    if channel_type == "project":
        try:
            project_id = UUID(channel_id)
        except ValueError:
            return False
        proj_repo = ProjectRepository(session)
        proj_member = await proj_repo.get_member(project_id, user_id)
        return proj_member is not None

    return False


@ws_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Main WebSocket endpoint for real-time event subscriptions."""
    # ── Extract dependencies from app state ──────────────────
    app = websocket.app
    conn_manager: RealtimeConnectionManager = app.state.realtime_conn_manager
    sub_manager: RealtimeSubscriptionManager = app.state.realtime_sub_manager
    jwt_verifier: JWTVerifier = app.state.jwt_verifier

    # ── Authenticate ─────────────────────────────────────────
    token = websocket.query_params.get("ticket") or websocket.query_params.get("token")
    try:
        user_id = authenticate_ws_token(token, jwt_verifier)
    except AuthenticationError:
        await websocket.close(code=4001, reason="Authentication failed")
        return

    # ── Accept and register ──────────────────────────────────
    await websocket.accept()
    conn_manager.connect(user_id, websocket)

    # Auto-subscribe to user-scoped channel
    user_channel = f"user:{user_id}"
    sub_manager.subscribe(user_channel, user_id, websocket)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "Invalid JSON"}))
                continue

            action = msg.get("action")
            channel = msg.get("channel")

            if not action or not channel:
                await websocket.send_text(
                    json.dumps({"error": "Missing 'action' or 'channel'"})
                )
                continue

            if action == "subscribe":
                # Check authorization
                async with get_session_factory()() as session:
                    authorized = await _check_channel_authorization(
                        channel, user_id, session
                    )
                if not authorized:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "error": "Unauthorized",
                                "channel": channel,
                            }
                        )
                    )
                    continue

                sub_manager.subscribe(channel, user_id, websocket)
                await websocket.send_text(
                    json.dumps(
                        {
                            "action": "subscribed",
                            "channel": channel,
                        }
                    )
                )

            elif action == "unsubscribe":
                sub_manager.unsubscribe(channel, user_id, websocket)
                await websocket.send_text(
                    json.dumps(
                        {
                            "action": "unsubscribed",
                            "channel": channel,
                        }
                    )
                )
            else:
                await websocket.send_text(
                    json.dumps({"error": f"Unknown action: {action}"})
                )

    except WebSocketDisconnect:
        logger.debug("ws_client_disconnected", user_id=str(user_id))
    except Exception:
        logger.exception("ws_unexpected_error", user_id=str(user_id))
    finally:
        sub_manager.unsubscribe_all(user_id, websocket)
        conn_manager.disconnect(user_id, websocket)
