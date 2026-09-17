"""Connection repository — persistence for user-to-user connections."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.enums import ConnectionStatus
from app.domain.models import UserConnection
from app.repositories.base import BaseRepository


def _canonical_pair(user_a: UUID, user_b: UUID) -> tuple[UUID, UUID]:
    """Return (user_lo, user_hi) ensuring user_lo < user_hi."""
    if str(user_a) < str(user_b):
        return user_a, user_b
    return user_b, user_a


class ConnectionRepository(BaseRepository[UserConnection]):
    model = UserConnection

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_between(self, user_a: UUID, user_b: UUID) -> UserConnection | None:
        """Find the connection between two users (auto-canonicalizes)."""
        lo, hi = _canonical_pair(user_a, user_b)
        result = await self.session.execute(
            select(UserConnection)
            .where(UserConnection.user_lo == lo, UserConnection.user_hi == hi)
            .options(
                selectinload(UserConnection.user_lo_rel),
                selectinload(UserConnection.user_hi_rel),
                selectinload(UserConnection.requester),
            )
        )
        return result.scalar_one_or_none()

    async def create_connection(
        self,
        sender_id: UUID,
        receiver_id: UUID,
    ) -> UserConnection:
        """Create a new PENDING connection request.

        Canonicalizes the pair so user_lo < user_hi.
        """
        lo, hi = _canonical_pair(sender_id, receiver_id)
        conn = UserConnection(
            user_lo=lo,
            user_hi=hi,
            requester_id=sender_id,
            status=ConnectionStatus.PENDING,
        )
        self.session.add(conn)
        await self.session.flush()
        # Reload with relationships
        result = await self.session.execute(
            select(UserConnection)
            .where(UserConnection.id == conn.id)
            .options(
                selectinload(UserConnection.user_lo_rel),
                selectinload(UserConnection.user_hi_rel),
                selectinload(UserConnection.requester),
            )
        )
        return result.scalar_one()

    async def update_status(
        self, connection_id: UUID, status: ConnectionStatus
    ) -> UserConnection:
        result = await self.session.execute(
            select(UserConnection)
            .where(UserConnection.id == connection_id)
            .options(
                selectinload(UserConnection.user_lo_rel),
                selectinload(UserConnection.user_hi_rel),
                selectinload(UserConnection.requester),
            )
        )
        conn = result.scalar_one()
        conn.status = status
        await self.session.flush()
        await self.session.refresh(conn)
        return conn

    async def list_connections(
        self,
        user_id: UUID,
        status: ConnectionStatus | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[UserConnection], int]:
        """List connections for a user, optionally filtered by status."""
        base_filter = or_(
            UserConnection.user_lo == user_id,
            UserConnection.user_hi == user_id,
        )
        filters = [base_filter]
        if status is not None:
            filters.append(UserConnection.status == status)

        count_result = await self.session.execute(
            select(func.count()).select_from(
                select(UserConnection).where(*filters).subquery()
            )
        )
        total = count_result.scalar_one()

        result = await self.session.execute(
            select(UserConnection)
            .where(*filters)
            .options(
                selectinload(UserConnection.user_lo_rel),
                selectinload(UserConnection.user_hi_rel),
                selectinload(UserConnection.requester),
            )
            .order_by(UserConnection.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all()), total

    async def list_pending_incoming(
        self, user_id: UUID, offset: int = 0, limit: int = 20
    ) -> tuple[list[UserConnection], int]:
        """Pending connections where user is the receiver (not the requester)."""
        filters = [
            or_(
                UserConnection.user_lo == user_id,
                UserConnection.user_hi == user_id,
            ),
            UserConnection.status == ConnectionStatus.PENDING,
            UserConnection.requester_id != user_id,
        ]

        count_result = await self.session.execute(
            select(func.count()).select_from(
                select(UserConnection).where(*filters).subquery()
            )
        )
        total = count_result.scalar_one()

        result = await self.session.execute(
            select(UserConnection)
            .where(*filters)
            .options(
                selectinload(UserConnection.user_lo_rel),
                selectinload(UserConnection.user_hi_rel),
                selectinload(UserConnection.requester),
            )
            .order_by(UserConnection.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all()), total

    async def list_pending_outgoing(
        self, user_id: UUID, offset: int = 0, limit: int = 20
    ) -> tuple[list[UserConnection], int]:
        """Pending connections where user is the requester."""
        filters = [
            or_(
                UserConnection.user_lo == user_id,
                UserConnection.user_hi == user_id,
            ),
            UserConnection.status == ConnectionStatus.PENDING,
            UserConnection.requester_id == user_id,
        ]

        count_result = await self.session.execute(
            select(func.count()).select_from(
                select(UserConnection).where(*filters).subquery()
            )
        )
        total = count_result.scalar_one()

        result = await self.session.execute(
            select(UserConnection)
            .where(*filters)
            .options(
                selectinload(UserConnection.user_lo_rel),
                selectinload(UserConnection.user_hi_rel),
                selectinload(UserConnection.requester),
            )
            .order_by(UserConnection.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all()), total
