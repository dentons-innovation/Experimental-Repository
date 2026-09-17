"""Unit tests for the ConnectionService."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.domain.enums import ConnectionStatus
from app.domain.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.domain.models import UserConnection
from app.services.connection_service import ConnectionService


def _make_connection(status: ConnectionStatus = ConnectionStatus.PENDING) -> UserConnection:
    return UserConnection(
        id=uuid4(),
        user_lo=uuid4(),
        user_hi=uuid4(),
        requester_id=uuid4(),
        status=status,
    )


def _make_service(
    target_user: MagicMock | None = None,
    existing_connection: UserConnection | None = None,
) -> ConnectionService:
    conn_repo = MagicMock()
    conn_repo.get_between = AsyncMock(return_value=existing_connection)
    conn_repo.get_by_id = AsyncMock(return_value=existing_connection)
    conn_repo.create_connection = AsyncMock(return_value=_make_connection())
    conn_repo.update_status = AsyncMock(return_value=_make_connection())
    conn_repo.delete = AsyncMock()
    conn_repo.list_connections = AsyncMock(return_value=([], 0))

    user_repo = MagicMock()
    user_repo.get_by_id = AsyncMock(return_value=target_user)

    publisher = MagicMock()
    publisher.publish = AsyncMock()
    publisher.publish_many = AsyncMock()

    return ConnectionService(conn_repo, user_repo, publisher)


class TestSendRequest:
    async def test_send_request_success(self):
        target = MagicMock()
        target.id = uuid4()
        svc = _make_service(target_user=target, existing_connection=None)

        sender_id = uuid4()
        await svc.send_request(sender_id, target.id)
        svc._conn_repo.create_connection.assert_called_once_with(
            sender_id=sender_id, receiver_id=target.id
        )
        svc._publisher.publish.assert_called_once()

    async def test_send_request_to_self_raises_error(self):
        svc = _make_service()
        user_id = uuid4()
        with pytest.raises(Exception, match="yourself"):
            await svc.send_request(user_id, user_id)

    async def test_send_request_missing_user_raises_404(self):
        svc = _make_service(target_user=None)
        with pytest.raises(NotFoundError):
            await svc.send_request(uuid4(), uuid4())

    async def test_send_request_already_connected_raises_conflict(self):
        existing = _make_connection(status=ConnectionStatus.ACCEPTED)
        target = MagicMock()
        target.id = uuid4()
        svc = _make_service(target_user=target, existing_connection=existing)

        with pytest.raises(ConflictError, match="already connected"):
            await svc.send_request(uuid4(), target.id)

    async def test_send_request_already_pending_raises_conflict(self):
        existing = _make_connection(status=ConnectionStatus.PENDING)
        target = MagicMock()
        target.id = uuid4()
        svc = _make_service(target_user=target, existing_connection=existing)

        with pytest.raises(ConflictError, match="pending connection"):
            await svc.send_request(uuid4(), target.id)


class TestAcceptRequest:
    async def test_accept_request_success(self):
        existing = _make_connection(status=ConnectionStatus.PENDING)
        existing.requester_id = existing.user_lo
        receiver_id = existing.user_hi

        svc = _make_service(existing_connection=existing)
        await svc.accept_request(receiver_id, existing.id)
        
        svc._conn_repo.update_status.assert_called_once_with(
            existing.id, ConnectionStatus.ACCEPTED
        )
        svc._publisher.publish.assert_called_once()

    async def test_accept_request_as_requester_raises_auth_error(self):
        existing = _make_connection(status=ConnectionStatus.PENDING)
        requester_id = existing.requester_id
        svc = _make_service(existing_connection=existing)
        with pytest.raises(AuthorizationError, match="Only the receiver"):
            await svc.accept_request(requester_id, existing.id)


class TestRejectRequest:
    async def test_reject_request_success(self):
        existing = _make_connection(status=ConnectionStatus.PENDING)
        existing.requester_id = existing.user_lo
        receiver_id = existing.user_hi

        svc = _make_service(existing_connection=existing)
        await svc.reject_request(receiver_id, existing.id)
        
        svc._conn_repo.update_status.assert_called_once_with(
            existing.id, ConnectionStatus.REJECTED
        )


class TestRemoveConnection:
    async def test_remove_connection_success(self):
        existing = _make_connection(status=ConnectionStatus.ACCEPTED)
        svc = _make_service(existing_connection=existing)
        await svc.remove_connection(existing.user_lo, existing.id)
        svc._conn_repo.delete.assert_called_once_with(existing)

    async def test_remove_connection_not_participant_raises_auth_error(self):
        existing = _make_connection(status=ConnectionStatus.ACCEPTED)
        svc = _make_service(existing_connection=existing)
        with pytest.raises(AuthorizationError):
            await svc.remove_connection(uuid4(), existing.id)
