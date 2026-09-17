"""Unit tests for UserService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.domain.exceptions import NotFoundError
from app.domain.models import User
from app.services.user_service import UserService


class TestUserService:
    async def test_get_by_id_success(self):
        user = MagicMock(spec=User)
        user.id = uuid4()
        user_repo = MagicMock()
        user_repo.get_by_id = AsyncMock(return_value=user)

        svc = UserService(user_repo)
        result = await svc.get_by_id(user.id)
        assert result == user

    async def test_get_by_id_not_found(self):
        user_repo = MagicMock()
        user_repo.get_by_id = AsyncMock(return_value=None)

        svc = UserService(user_repo)
        with pytest.raises(NotFoundError):
            await svc.get_by_id(uuid4())

    async def test_get_by_email_success(self):
        user = MagicMock(spec=User)
        user.email = "test@example.com"
        user_repo = MagicMock()
        user_repo.get_by_email = AsyncMock(return_value=user)

        svc = UserService(user_repo)
        result = await svc.get_by_email("test@example.com")
        assert result == user

    async def test_get_by_email_not_found(self):
        user_repo = MagicMock()
        user_repo.get_by_email = AsyncMock(return_value=None)

        svc = UserService(user_repo)
        with pytest.raises(NotFoundError):
            await svc.get_by_email("missing@example.com")
