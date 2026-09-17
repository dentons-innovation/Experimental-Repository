"""API v1 router — aggregates all resource routers."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    comments,
    connections,
    health,
    labels,
    projects,
    tasks,
    users,
    workspaces,
)

# Root router — mounted at /api/v1
api_router = APIRouter(prefix="/api/v1")

# Health checks — no auth, no versioning prefix needed
health_router = APIRouter()
health_router.include_router(health.router)

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(workspaces.router)
api_router.include_router(projects.router)
api_router.include_router(tasks.router)
api_router.include_router(comments.router)
api_router.include_router(connections.router)
api_router.include_router(labels.router)
