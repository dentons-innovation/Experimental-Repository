"""Health and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session

router = APIRouter(tags=["health"])


@router.get("/health", include_in_schema=False)
async def health() -> dict[str, str]:
    """Basic liveness check — always returns 200 if the process is up."""
    return {"status": "ok"}


@router.get("/readiness", include_in_schema=False)
async def readiness(session: AsyncSession = Depends(get_db_session)) -> dict[str, str]:
    """Readiness check — verifies database connectivity.

    Returns 503 (via exception) if the database is unreachable.
    Used by load balancers and orchestrators before routing traffic.
    """
    await session.execute(text("SELECT 1"))
    return {"status": "ready"}
