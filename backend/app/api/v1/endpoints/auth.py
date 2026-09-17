"""Authentication endpoints — registration, login, and token verification."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, status

from app.api.v1.schemas.schemas import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.core.dependencies import CurrentUserId, DbSession
from app.infrastructure.auth import create_access_token
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _auth_service(session: DbSession) -> AuthService:
    return AuthService(UserRepository(session))


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    payload: UserRegisterRequest,
    session: DbSession,
) -> TokenResponse:
    service = _auth_service(session)
    user, token = await service.register(
        email=payload.email,
        username=payload.username,
        full_name=payload.full_name,
        password=payload.password,
        avatar_url=payload.avatar_url,
    )
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Sign in with email and password",
)
async def login(
    payload: UserLoginRequest,
    session: DbSession,
) -> TokenResponse:
    service = _auth_service(session)
    user, token = await service.login(
        login_identifier=payload.email,
        password=payload.password,
    )
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user profile",
)
async def get_me(
    user_id: CurrentUserId,
    session: DbSession,
) -> UserResponse:
    service = _auth_service(session)
    user = await service.get_by_id(user_id)
    return UserResponse.model_validate(user)


@router.post(
    "/ws-ticket",
    summary="Generate a short-lived ticket for WebSocket connection handshake",
)
async def create_ws_ticket(
    user_id: CurrentUserId,
    session: DbSession,
) -> dict[str, str]:
    service = _auth_service(session)
    user = await service.get_by_id(user_id)
    ticket = create_access_token(
        user_id=user.id,
        email=user.email,
        username=user.username,
        expires_delta=timedelta(seconds=60),
    )
    return {"ticket": ticket}
