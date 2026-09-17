"""Unit tests for authentication infrastructure, JWT verification, and dependencies."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.core.config import get_settings
from app.core.dependencies import (
    PaginationParams,
    get_current_user,
    get_current_user_id,
)
from app.domain.exceptions import AuthenticationError
from app.domain.models import User
from app.infrastructure.auth import (
    JWTVerifier,
    create_access_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_and_verify_success(self):
        pwd = "SecurePassword123!"
        hashed = hash_password(pwd)
        assert hashed != pwd
        assert verify_password(pwd, hashed) is True

    def test_verify_incorrect_password(self):
        pwd = "SecurePassword123!"
        hashed = hash_password(pwd)
        assert verify_password("WrongPassword!", hashed) is False

    def test_verify_corrupted_hash(self):
        # Malformed hash triggers exception branch in verify_password
        assert verify_password("password", "not-a-valid-bcrypt-hash") is False


class TestJWTToken:
    def test_create_and_verify_token_success(self):
        user_id = uuid4()
        token = create_access_token(
            user_id=user_id,
            email="dev@example.com",
            username="developer",
        )
        verifier = JWTVerifier(get_settings())
        extracted_id = verifier.verify(token)
        assert extracted_id == str(user_id)

    def test_create_token_with_custom_expiry(self):
        user_id = uuid4()
        token = create_access_token(
            user_id=user_id,
            email="dev@example.com",
            username="developer",
            expires_delta=timedelta(minutes=5),
        )
        verifier = JWTVerifier(get_settings())
        claims = verifier.verify_token(token)
        assert claims["sub"] == str(user_id)

    def test_expired_token_raises_authentication_error(self):
        user_id = uuid4()
        # Create token already expired in the past
        token = create_access_token(
            user_id=user_id,
            email="dev@example.com",
            username="developer",
            expires_delta=timedelta(seconds=-10),
        )
        verifier = JWTVerifier(get_settings())
        with pytest.raises(AuthenticationError) as exc_info:
            verifier.verify_token(token)
        assert "expired" in str(exc_info.value).lower()

    def test_malformed_token_raises_authentication_error(self):
        verifier = JWTVerifier(get_settings())
        with pytest.raises(AuthenticationError) as exc_info:
            verifier.verify_token("not.a.valid.jwt")
        assert "invalid token" in str(exc_info.value).lower()

    def test_token_missing_sub_raises_authentication_error(self):
        import jwt

        s = get_settings()
        # Encode token without "sub" claim
        token = jwt.encode(
            {"email": "nosub@example.com"}, s.jwt_secret_key, algorithm=s.jwt_algorithm
        )
        verifier = JWTVerifier(s)
        with pytest.raises(AuthenticationError) as exc_info:
            verifier.verify(token)
        assert "missing subject" in str(exc_info.value).lower()


class TestDependencies:
    async def test_get_current_user_id_success(self):
        user_id = uuid4()
        verifier = MagicMock()
        verifier.verify.return_value = str(user_id)

        result = await get_current_user_id(
            authorization="Bearer test-token",
            jwt_verifier=verifier,
        )
        assert result == user_id

    async def test_get_current_user_id_missing_header_raises_401(self):
        verifier = MagicMock()
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_id(authorization=None, jwt_verifier=verifier)
        assert exc_info.value.status_code == 401
        assert "Missing" in exc_info.value.detail

    async def test_get_current_user_id_invalid_scheme_raises_401(self):
        verifier = MagicMock()
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_id(
                authorization="Basic token", jwt_verifier=verifier
            )
        assert exc_info.value.status_code == 401
        assert "Expected: Bearer" in exc_info.value.detail

    async def test_get_current_user_id_bad_token_raises_401(self):
        verifier = MagicMock()
        verifier.verify.side_effect = AuthenticationError("Invalid signature")
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_id(
                authorization="Bearer bad-token", jwt_verifier=verifier
            )
        assert exc_info.value.status_code == 401

    async def test_get_current_user_success(self):
        user_id = uuid4()
        user = MagicMock(spec=User)
        user.id = user_id

        session = MagicMock()
        session.execute = AsyncMock()
        # Mock UserRepository inside get_current_user
        with pytest.MonkeyPatch.context() as mp:
            user_repo_mock = MagicMock()
            user_repo_mock.get_by_id = AsyncMock(return_value=user)
            mp.setattr(
                "app.repositories.user_repository.UserRepository",
                lambda s: user_repo_mock,
            )

            res = await get_current_user(user_id=user_id, session=session)
            assert res == user

    async def test_get_current_user_not_found_raises_401(self):
        user_id = uuid4()
        session = MagicMock()
        with pytest.MonkeyPatch.context() as mp:
            user_repo_mock = MagicMock()
            user_repo_mock.get_by_id = AsyncMock(return_value=None)
            mp.setattr(
                "app.repositories.user_repository.UserRepository",
                lambda s: user_repo_mock,
            )

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(user_id=user_id, session=session)
            assert exc_info.value.status_code == 401
            assert "User not found" in exc_info.value.detail

    def test_pagination_params(self):
        params = PaginationParams(page=3, page_size=15)
        assert params.offset == 30
        assert params.limit == 15
