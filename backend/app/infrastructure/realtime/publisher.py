"""Event publisher abstraction and in-process implementation.

Business/service code depends on ``RealtimeEventPublisher`` (the protocol),
never on the concrete ``InProcessEventPublisher``.  When the system needs
to scale horizontally, swap in a Redis Pub/Sub-backed publisher that
implements the same protocol — no service code changes required.
"""

from __future__ import annotations

import json
from typing import Protocol, runtime_checkable
from uuid import UUID

import structlog

from app.infrastructure.realtime.manager import RealtimeSubscriptionManager
from app.infrastructure.realtime.types import RealtimeEvent

logger = structlog.get_logger(__name__)


def _serialize_event(event: RealtimeEvent) -> str:
    """Produce the JSON string sent over the WebSocket."""
    return json.dumps(
        {
            "channel": event.channel,
            "event": event.event_type,
            "data": event.payload,
        },
        default=str,  # handle UUIDs, datetimes, etc.
    )


@runtime_checkable
class RealtimeEventPublisher(Protocol):
    """Abstract publisher that services depend on."""

    async def publish(self, event: RealtimeEvent) -> None: ...

    async def publish_many(self, events: list[RealtimeEvent]) -> None: ...


class InProcessEventPublisher:
    """Single-instance publisher that fans out via the local subscription manager.

    Architecture note:
        This implementation delivers events only to WebSocket connections
        managed by the current process.  For horizontally-scaled
        multi-instance deployment, replace this class with one that
        publishes to Redis Pub/Sub (or equivalent) and have each instance
        subscribe and fan-out locally.
    """

    def __init__(self, sub_manager: RealtimeSubscriptionManager) -> None:
        self._sub_manager = sub_manager

    async def publish(self, event: RealtimeEvent) -> None:
        message = _serialize_event(event)
        logger.debug(
            "realtime_publish",
            channel=event.channel,
            event_type=event.event_type,
        )
        await self._sub_manager.broadcast_to_channel(
            channel=event.channel,
            message=message,
            exclude_user_id=event.exclude_user_id,
        )

        # Automatically revoke active subscriptions if a member was removed
        if event.event_type == "project.member_removed" and event.payload:
            user_id = event.payload.get("user_id")
            project_id = event.payload.get("project_id")
            if user_id and project_id:
                try:
                    self._sub_manager.unsubscribe_user_from_channel(
                        f"project:{project_id}", UUID(str(user_id))
                    )
                except (ValueError, TypeError):
                    pass
        elif event.event_type == "workspace.member_removed" and event.payload:
            user_id = event.payload.get("user_id")
            workspace_id = event.payload.get("workspace_id")
            if user_id and workspace_id:
                try:
                    self._sub_manager.unsubscribe_user_from_channel(
                        f"workspace:{workspace_id}", UUID(str(user_id))
                    )
                except (ValueError, TypeError):
                    pass

    async def publish_many(self, events: list[RealtimeEvent]) -> None:
        for event in events:
            await self.publish(event)


class NoOpEventPublisher:
    """Publisher that discards all events — used in tests and offline contexts."""

    async def publish(self, event: RealtimeEvent) -> None:
        pass

    async def publish_many(self, events: list[RealtimeEvent]) -> None:
        pass
