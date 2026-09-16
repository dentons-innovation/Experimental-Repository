"""User endpoints — profile and user retrieval."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.api.v1.schemas.schemas import UserResponse
from app.core.dependencies import CurrentUserId, DbSession
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


def _user_service(session: DbSession) -> UserService:
    return UserService(UserRepository(session))


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user",
)
async def get_me(
    user_id: CurrentUserId,
    session: DbSession,
) -> UserResponse:
    service = _user_service(session)
    user = await service.get_by_id(user_id)
    return UserResponse.model_validate(user)


@router.get(
    "/{target_user_id}",
    response_model=UserResponse,
    summary="Get user by ID",
)
async def get_user_by_id(
    target_user_id: UUID,
    _user_id: CurrentUserId,
    session: DbSession,
) -> UserResponse:
    service = _user_service(session)
    user = await service.get_by_id(target_user_id)
    return UserResponse.model_validate(user)
