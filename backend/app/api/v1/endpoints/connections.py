"""Connection endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.v1.schemas.common import PaginatedResponse
from app.api.v1.schemas.connections import ConnectionRequest, ConnectionResponse
from app.api.v1.schemas.schemas import UserResponse
from app.core.dependencies import CurrentUserId, DbSession, Pagination
from app.core.realtime_deps import get_event_publisher
from app.infrastructure.realtime.publisher import RealtimeEventPublisher
from app.repositories.connection_repository import ConnectionRepository
from app.repositories.user_repository import UserRepository
from app.services.connection_service import ConnectionService

router = APIRouter(prefix="/connections", tags=["connections"])


def _make_service(
    session: DbSession, publisher: RealtimeEventPublisher
) -> ConnectionService:
    conn_repo = ConnectionRepository(session)
    user_repo = UserRepository(session)
    return ConnectionService(conn_repo, user_repo, publisher)


@router.get("/users/search", response_model=PaginatedResponse[UserResponse])
async def search_users(
    user_id: CurrentUserId,
    session: DbSession,
    pagination: Pagination,
    q: str = Query(..., min_length=1, max_length=100),
    publisher: RealtimeEventPublisher = Depends(get_event_publisher),
) -> PaginatedResponse[UserResponse]:
    """Search for users by username, email, or full name."""
    svc = _make_service(session, publisher)
    users, total = await svc.search_users(
        query=q, user_id=user_id, offset=pagination.offset, limit=pagination.limit
    )
    return PaginatedResponse.create(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("", response_model=ConnectionResponse, status_code=status.HTTP_201_CREATED)
async def send_connection_request(
    payload: ConnectionRequest,
    user_id: CurrentUserId,
    session: DbSession,
    publisher: RealtimeEventPublisher = Depends(get_event_publisher),
) -> ConnectionResponse:
    """Send a connection request to another user."""
    svc = _make_service(session, publisher)
    connection = await svc.send_request(
        sender_id=user_id, receiver_id=payload.receiver_id
    )
    return ConnectionResponse.model_validate(connection)


@router.get("", response_model=PaginatedResponse[ConnectionResponse])
async def list_connections(
    user_id: CurrentUserId,
    session: DbSession,
    pagination: Pagination,
    publisher: RealtimeEventPublisher = Depends(get_event_publisher),
) -> PaginatedResponse[ConnectionResponse]:
    """List all accepted connections."""
    svc = _make_service(session, publisher)
    connections, total = await svc.list_connections(
        user_id, offset=pagination.offset, limit=pagination.limit
    )
    return PaginatedResponse.create(
        items=[ConnectionResponse.model_validate(c) for c in connections],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/pending/incoming", response_model=PaginatedResponse[ConnectionResponse])
async def list_pending_incoming(
    user_id: CurrentUserId,
    session: DbSession,
    pagination: Pagination,
    publisher: RealtimeEventPublisher = Depends(get_event_publisher),
) -> PaginatedResponse[ConnectionResponse]:
    """List pending connections received by the user."""
    svc = _make_service(session, publisher)
    connections, total = await svc.list_pending_incoming(
        user_id, offset=pagination.offset, limit=pagination.limit
    )
    return PaginatedResponse.create(
        items=[ConnectionResponse.model_validate(c) for c in connections],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/pending/outgoing", response_model=PaginatedResponse[ConnectionResponse])
async def list_pending_outgoing(
    user_id: CurrentUserId,
    session: DbSession,
    pagination: Pagination,
    publisher: RealtimeEventPublisher = Depends(get_event_publisher),
) -> PaginatedResponse[ConnectionResponse]:
    """List pending connections sent by the user."""
    svc = _make_service(session, publisher)
    connections, total = await svc.list_pending_outgoing(
        user_id, offset=pagination.offset, limit=pagination.limit
    )
    return PaginatedResponse.create(
        items=[ConnectionResponse.model_validate(c) for c in connections],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("/{connection_id}/accept", response_model=ConnectionResponse)
async def accept_connection(
    connection_id: UUID,
    user_id: CurrentUserId,
    session: DbSession,
    publisher: RealtimeEventPublisher = Depends(get_event_publisher),
) -> ConnectionResponse:
    """Accept a pending connection request."""
    svc = _make_service(session, publisher)
    connection = await svc.accept_request(user_id, connection_id)
    return ConnectionResponse.model_validate(connection)


@router.post("/{connection_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
async def reject_connection(
    connection_id: UUID,
    user_id: CurrentUserId,
    session: DbSession,
    publisher: RealtimeEventPublisher = Depends(get_event_publisher),
) -> Response:
    """Reject a pending connection request."""
    svc = _make_service(session, publisher)
    await svc.reject_request(user_id, connection_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_connection(
    connection_id: UUID,
    user_id: CurrentUserId,
    session: DbSession,
    publisher: RealtimeEventPublisher = Depends(get_event_publisher),
) -> Response:
    """Remove an accepted connection or cancel a pending one."""
    svc = _make_service(session, publisher)
    await svc.remove_connection(user_id, connection_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
