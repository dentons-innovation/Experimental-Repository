"""Authentication service — handles registration, login, and token generation."""

from __future__ import annotations

from uuid import UUID

from app.domain.exceptions import AuthenticationError, ConflictError, NotFoundError
from app.domain.models import User
from app.infrastructure.auth import create_access_token, hash_password, verify_password
from app.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, user_repo: UserRepository) -> None:
        self._user_repo = user_repo

    async def register(
        self,
        email: str,
        username: str,
        full_name: str,
        password: str,
        avatar_url: str | None = None,
    ) -> tuple[User, str]:
        """Register a new user and generate a JWT access token."""
        normalized_email = email.strip().lower()
        normalized_username = username.strip().lower()

        existing_email = await self._user_repo.get_by_email(normalized_email)
        if existing_email:
            raise ConflictError(f"User with email '{normalized_email}' already exists")

        existing_username = await self._user_repo.get_by_username(normalized_username)
        if existing_username:
            raise ConflictError(f"Username '{normalized_username}' is already taken")

        pwd_hash = hash_password(password)
        user = await self._user_repo.create_user(
            email=normalized_email,
            username=normalized_username,
            full_name=full_name.strip(),
            password_hash=pwd_hash,
            avatar_url=avatar_url,
        )

        token = create_access_token(user.id, user.email, user.username)
        return user, token

    async def login(
        self,
        login_identifier: str,
        password: str,
    ) -> tuple[User, str]:
        """Authenticate user by email or username and password, returning JWT access token."""
        identifier = login_identifier.strip().lower()
        user: User | None = None

        if "@" in identifier:
            user = await self._user_repo.get_by_email(identifier)
        else:
            user = await self._user_repo.get_by_username(identifier)

        if user is None or not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid email or password")

        token = create_access_token(user.id, user.email, user.username)
        return user, token

    async def get_by_id(self, user_id: UUID) -> User:
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User", str(user_id))
        return user
