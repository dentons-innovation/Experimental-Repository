"""Connection schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.api.v1.schemas.schemas import UserResponse
from app.domain.enums import ConnectionStatus


class ConnectionRequest(BaseModel):
    receiver_id: UUID


class ConnectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_lo: UUID
    user_hi: UUID
    requester_id: UUID
    status: ConnectionStatus
    created_at: datetime
    updated_at: datetime

    # These fields are hydrated from relationships
    user_lo_rel: UserResponse
    user_hi_rel: UserResponse
