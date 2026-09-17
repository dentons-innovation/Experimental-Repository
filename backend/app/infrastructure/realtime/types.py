"""Typed event definitions for the real-time layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RealtimeEvent:
    """An event to be published to subscribers of a specific channel.

    Attributes:
        channel: The subscription channel, e.g. ``"project:abc-123"``
                 or ``"user:def-456"``.
        event_type: A dotted event name, e.g. ``"task.created"``,
                    ``"workspace.member_added"``.
        payload: JSON-serializable event data.
        exclude_user_id: If set, this user will *not* receive the event
                         (used to prevent echoing an action back to
                         the actor who triggered it).
    """

    channel: str
    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    exclude_user_id: UUID | None = None
