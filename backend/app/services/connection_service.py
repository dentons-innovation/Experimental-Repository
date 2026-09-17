"""Connection service — user relationship lifecycle."""

from __future__ import annotations

from uuid import UUID

import structlog

from app.domain.enums import ConnectionStatus
from app.domain.exceptions import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.domain.models import User, UserConnection
from app.infrastructure.realtime.publisher import RealtimeEventPublisher
from app.infrastructure.realtime.types import RealtimeEvent
from app.repositories.connection_repository import ConnectionRepository
from app.repositories.user_repository import UserRepository

logger = structlog.get_logger(__name__)


class ConnectionService:
    def __init__(
        self,
        connection_repo: ConnectionRepository,
        user_repo: UserRepository,
        publisher: RealtimeEventPublisher,
    ) -> None:
        self._conn_repo = connection_repo
        self._user_repo = user_repo
        self._publisher = publisher

    # ─────────────────────────────────────────────────────────
    # User search
    # ─────────────────────────────────────────────────────────

    async def search_users(
        self,
        query: str,
        user_id: UUID,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[User], int]:
        """Paginated user search, excluding the searching user."""
        if not query or not query.strip():
            return [], 0
        return await self._user_repo.search(
            query=query,
            exclude_user_id=user_id,
            offset=offset,
            limit=limit,
        )

    # ─────────────────────────────────────────────────────────
    # Connection lifecycle
    # ─────────────────────────────────────────────────────────

    async def send_request(self, sender_id: UUID, receiver_id: UUID) -> UserConnection:
        """Send a connection/friend request.

        Validates:
        - No self-request
        - Receiver exists
        - No existing connection (any status)
        """
        if sender_id == receiver_id:
            raise ValidationError("Cannot send a connection request to yourself")

        receiver = await self._user_repo.get_by_id(receiver_id)
        if receiver is None:
            raise NotFoundError("User", str(receiver_id))

        # Check for existing connection in any state
        existing = await self._conn_repo.get_between(sender_id, receiver_id)
        if existing is not None:
            if existing.status == ConnectionStatus.ACCEPTED:
                raise ConflictError("You are already connected with this user")
            if existing.status == ConnectionStatus.PENDING:
                raise ConflictError("A pending connection request already exists")
            if existing.status == ConnectionStatus.REJECTED:
                # Allow re-request after rejection: delete old and create new
                await self._conn_repo.delete(existing)

        connection = await self._conn_repo.create_connection(
            sender_id=sender_id,
            receiver_id=receiver_id,
        )

        # Publish event to receiver's user channel
        await self._publisher.publish(
            RealtimeEvent(
                channel=f"user:{receiver_id}",
                event_type="connection.requested",
                payload={
                    "connection_id": str(connection.id),
                    "sender_id": str(sender_id),
                },
            )
        )

        return connection

    async def accept_request(
        self, user_id: UUID, connection_id: UUID
    ) -> UserConnection:
        """Accept a pending connection request.

        Only the receiver (the non-requester) can accept.
        """
        connection = await self._conn_repo.get_by_id(connection_id)
        if connection is None:
            raise NotFoundError("Connection", str(connection_id))

        if connection.status != ConnectionStatus.PENDING:
            raise ConflictError("Connection is not in pending state")

        # Only the receiver can accept
        receiver_id = self._get_receiver_id(connection)
        if user_id != receiver_id:
            raise AuthorizationError(
                "Only the receiver can accept a connection request"
            )

        updated = await self._conn_repo.update_status(
            connection_id, ConnectionStatus.ACCEPTED
        )

        # Publish to requester's user channel
        await self._publisher.publish(
            RealtimeEvent(
                channel=f"user:{connection.requester_id}",
                event_type="connection.accepted",
                payload={
                    "connection_id": str(connection.id),
                    "accepted_by": str(user_id),
                },
            )
        )

        return updated

    async def reject_request(self, user_id: UUID, connection_id: UUID) -> None:
        """Reject a pending connection request.

        Only the receiver can reject.
        """
        connection = await self._conn_repo.get_by_id(connection_id)
        if connection is None:
            raise NotFoundError("Connection", str(connection_id))

        if connection.status != ConnectionStatus.PENDING:
            raise ConflictError("Connection is not in pending state")

        receiver_id = self._get_receiver_id(connection)
        if user_id != receiver_id:
            raise AuthorizationError(
                "Only the receiver can reject a connection request"
            )

        await self._conn_repo.update_status(connection_id, ConnectionStatus.REJECTED)

    async def remove_connection(self, user_id: UUID, connection_id: UUID) -> None:
        """Remove an accepted connection or cancel a pending request.

        Either party can remove/cancel.
        """
        connection = await self._conn_repo.get_by_id(connection_id)
        if connection is None:
            raise NotFoundError("Connection", str(connection_id))

        # User must be part of the connection
        if user_id not in (connection.user_lo, connection.user_hi):
            raise AuthorizationError("You are not part of this connection")

        await self._conn_repo.delete(connection)

    async def list_connections(
        self, user_id: UUID, offset: int = 0, limit: int = 20
    ) -> tuple[list[UserConnection], int]:
        """List accepted connections."""
        return await self._conn_repo.list_connections(
            user_id, status=ConnectionStatus.ACCEPTED, offset=offset, limit=limit
        )

    async def list_pending_incoming(
        self, user_id: UUID, offset: int = 0, limit: int = 20
    ) -> tuple[list[UserConnection], int]:
        return await self._conn_repo.list_pending_incoming(
            user_id, offset=offset, limit=limit
        )

    async def list_pending_outgoing(
        self, user_id: UUID, offset: int = 0, limit: int = 20
    ) -> tuple[list[UserConnection], int]:
        return await self._conn_repo.list_pending_outgoing(
            user_id, offset=offset, limit=limit
        )

    # ─────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────

    @staticmethod
    def _get_receiver_id(connection: UserConnection) -> UUID:
        """Return the user who is NOT the requester."""
        if connection.requester_id == connection.user_lo:
            return connection.user_hi
        return connection.user_lo
