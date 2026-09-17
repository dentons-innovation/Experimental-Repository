"""Unit tests for the real-time manager."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.infrastructure.realtime.manager import (
    RealtimeConnectionManager,
    RealtimeSubscriptionManager,
)


class TestRealtimeConnectionManager:
    def test_connect_and_disconnect(self):
        manager = RealtimeConnectionManager()
        user_id = uuid4()
        ws = MagicMock()

        manager.connect(user_id, ws)
        assert len(manager.get_connections(user_id)) > 0
        assert ws in manager.get_connections(user_id)

        manager.disconnect(user_id, ws)
        assert len(manager.get_connections(user_id)) == 0
        assert ws not in manager.get_connections(user_id)

    def test_multiple_connections_same_user(self):
        manager = RealtimeConnectionManager()
        user_id = uuid4()
        ws1 = MagicMock()
        ws2 = MagicMock()

        manager.connect(user_id, ws1)
        manager.connect(user_id, ws2)
        
        conns = manager.get_connections(user_id)
        assert len(conns) == 2
        assert ws1 in conns
        assert ws2 in conns

        manager.disconnect(user_id, ws1)
        assert len(manager.get_connections(user_id)) == 1
        assert len(manager.get_connections(user_id)) > 0


class TestRealtimeSubscriptionManager:
    def test_subscribe_and_unsubscribe(self):
        manager = RealtimeSubscriptionManager()
        user_id = uuid4()
        ws = MagicMock()
        channel = "workspace:123"

        manager.subscribe(channel, user_id, ws)
        subs = manager.get_subscribers(channel)
        assert len(subs) == 1
        assert (user_id, ws) in subs

        manager.unsubscribe(channel, user_id, ws)
        assert len(manager.get_subscribers(channel)) == 0

    def test_unsubscribe_all(self):
        manager = RealtimeSubscriptionManager()
        user_id = uuid4()
        ws = MagicMock()

        manager.subscribe("channel:1", user_id, ws)
        manager.subscribe("channel:2", user_id, ws)

        manager.unsubscribe_all(user_id, ws)
        assert len(manager.get_subscribers("channel:1")) == 0
        assert len(manager.get_subscribers("channel:2")) == 0

    @pytest.mark.asyncio
    async def test_broadcast_to_channel(self):
        manager = RealtimeSubscriptionManager()
        user_id1, user_id2 = uuid4(), uuid4()
        ws1, ws2 = AsyncMock(), AsyncMock()

        manager.subscribe("test:1", user_id1, ws1)
        manager.subscribe("test:1", user_id2, ws2)

        await manager.broadcast_to_channel("test:1", "hello")

        ws1.send_text.assert_called_once_with("hello")
        ws2.send_text.assert_called_once_with("hello")

    @pytest.mark.asyncio
    async def test_broadcast_with_exclude(self):
        manager = RealtimeSubscriptionManager()
        user_id1, user_id2 = uuid4(), uuid4()
        ws1, ws2 = AsyncMock(), AsyncMock()

        manager.subscribe("test:1", user_id1, ws1)
        manager.subscribe("test:1", user_id2, ws2)

        await manager.broadcast_to_channel("test:1", "hello", exclude_user_id=user_id1)

        ws1.send_text.assert_not_called()
        ws2.send_text.assert_called_once_with("hello")
