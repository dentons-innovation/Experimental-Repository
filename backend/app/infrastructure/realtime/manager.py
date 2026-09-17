"""In-process connection and subscription managers.

These track which WebSocket connections are active and which channels
each connection is subscribed to.  All data lives in dictionaries local
to the process — no external dependencies.

Replace the subscription lookup with a Redis-backed registry when
deploying multiple backend instances.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import TYPE_CHECKING
from uuid import UUID

import structlog

if TYPE_CHECKING:
    from fastapi import WebSocket

logger = structlog.get_logger(__name__)


class RealtimeConnectionManager:
    """Tracks active WebSocket connections per user.

    Thread-safety: relies on the asyncio single-threaded event loop.
    No locks required because all access is from coroutines on the
    same loop.
    """

    def __init__(self) -> None:
        # user_id → set of active websockets (a user may have multiple tabs)
        self._connections: dict[UUID, set[WebSocket]] = defaultdict(set)

    def connect(self, user_id: UUID, ws: WebSocket) -> None:
        self._connections[user_id].add(ws)
        logger.debug("ws_connected", user_id=str(user_id), total=len(self._connections[user_id]))

    def disconnect(self, user_id: UUID, ws: WebSocket) -> None:
        conns = self._connections.get(user_id)
        if conns:
            conns.discard(ws)
            if not conns:
                del self._connections[user_id]
        logger.debug("ws_disconnected", user_id=str(user_id))

    def get_connections(self, user_id: UUID) -> set[WebSocket]:
        return self._connections.get(user_id, set())

    @property
    def active_user_count(self) -> int:
        return len(self._connections)


class RealtimeSubscriptionManager:
    """Maps channels to (user_id, websocket) pairs.

    Channels are strings like ``"user:abc"``, ``"workspace:def"``,
    ``"project:ghi"``.
    """

    def __init__(self) -> None:
        # channel → set of (user_id, ws)
        self._subscriptions: dict[str, set[tuple[UUID, WebSocket]]] = defaultdict(set)
        # ws → set of channels (for fast cleanup on disconnect)
        self._ws_channels: dict[WebSocket, set[str]] = defaultdict(set)

    def subscribe(self, channel: str, user_id: UUID, ws: WebSocket) -> None:
        self._subscriptions[channel].add((user_id, ws))
        self._ws_channels[ws].add(channel)
        logger.debug("ws_subscribed", channel=channel, user_id=str(user_id))

    def unsubscribe(self, channel: str, user_id: UUID, ws: WebSocket) -> None:
        subs = self._subscriptions.get(channel)
        if subs:
            subs.discard((user_id, ws))
            if not subs:
                del self._subscriptions[channel]
        ws_chans = self._ws_channels.get(ws)
        if ws_chans:
            ws_chans.discard(channel)

    def unsubscribe_all(self, user_id: UUID, ws: WebSocket) -> None:
        """Remove a connection from all channels (disconnect cleanup)."""
        channels = self._ws_channels.pop(ws, set())
        for channel in channels:
            subs = self._subscriptions.get(channel)
            if subs:
                subs.discard((user_id, ws))
                if not subs:
                    del self._subscriptions[channel]
        logger.debug(
            "ws_unsubscribed_all",
            user_id=str(user_id),
            channel_count=len(channels),
        )

    def get_subscribers(self, channel: str) -> set[tuple[UUID, WebSocket]]:
        return self._subscriptions.get(channel, set())

    def get_channels_for_ws(self, ws: WebSocket) -> set[str]:
        return self._ws_channels.get(ws, set())

    async def broadcast_to_channel(
        self,
        channel: str,
        message: str,
        exclude_user_id: UUID | None = None,
    ) -> None:
        """Send a text message to all subscribers of a channel.

        Failed sends (broken connections) are silently dropped; the
        connection will be cleaned up on the next receive failure.
        """
        subscribers = self.get_subscribers(channel)
        if not subscribers:
            return

        tasks = []
        for uid, ws in subscribers:
            if exclude_user_id and uid == exclude_user_id:
                continue
            tasks.append(self._safe_send(ws, message))

        if tasks:
            await asyncio.gather(*tasks)

    @staticmethod
    async def _safe_send(ws: WebSocket, message: str) -> None:
        try:
            await ws.send_text(message)
        except Exception:
            # Connection is broken; will be cleaned up on disconnect
            pass
