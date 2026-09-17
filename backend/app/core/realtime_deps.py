"""FastAPI dependencies for the real-time infrastructure."""

from __future__ import annotations

from typing import cast

from fastapi import Request

from app.infrastructure.realtime.publisher import (
    NoOpEventPublisher,
    RealtimeEventPublisher,
)


def get_event_publisher(request: Request) -> RealtimeEventPublisher:
    """Retrieve the event publisher from app state.

    Falls back to a no-op publisher if real-time is not initialized
    (e.g. in test environments).
    """
    publisher = getattr(request.app.state, "realtime_publisher", None)
    if publisher is None:
        return NoOpEventPublisher()
    return cast(RealtimeEventPublisher, publisher)
