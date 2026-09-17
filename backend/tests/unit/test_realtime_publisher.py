"""Unit tests for the real-time publisher."""

import json
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.infrastructure.realtime.manager import RealtimeSubscriptionManager
from app.infrastructure.realtime.publisher import InProcessEventPublisher
from app.infrastructure.realtime.types import RealtimeEvent


@pytest.mark.asyncio
class TestInProcessEventPublisher:
    async def test_publish_serializes_and_broadcasts(self):
        sub_manager = RealtimeSubscriptionManager()
        publisher = InProcessEventPublisher(sub_manager)

        # Mock broadcast
        sub_manager.broadcast_to_channel = AsyncMock()

        event = RealtimeEvent(
            channel="workspace:123",
            event_type="test.event",
            payload={"foo": "bar"},
            exclude_user_id=uuid4(),
        )

        await publisher.publish(event)

        sub_manager.broadcast_to_channel.assert_called_once()
        kwargs = sub_manager.broadcast_to_channel.call_args.kwargs
        assert kwargs["channel"] == "workspace:123"
        assert kwargs["exclude_user_id"] == event.exclude_user_id

        # Check serialization
        message = kwargs["message"]
        data = json.loads(message)
        assert data["channel"] == "workspace:123"
        assert data["event"] == "test.event"
        assert data["data"] == {"foo": "bar"}

    async def test_publish_many(self):
        sub_manager = RealtimeSubscriptionManager()
        publisher = InProcessEventPublisher(sub_manager)
        sub_manager.broadcast_to_channel = AsyncMock()

        events = [
            RealtimeEvent(channel="c1", event_type="e1", payload={}),
            RealtimeEvent(channel="c2", event_type="e2", payload={}),
        ]

        await publisher.publish_many(events)
        assert sub_manager.broadcast_to_channel.call_count == 2
