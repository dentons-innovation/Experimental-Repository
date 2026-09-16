"""Pydantic schemas for all domain resources."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.enums import (
    ActivityAction,
    ProjectRole,
    TaskPriority,
    TaskStatus,
    WorkspaceRole,
)


# ─────────────────────────────────────────────────────────────
# User & Auth schemas
# ─────────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    id: UUID
    email: str
    username: str
    full_name: str
    avatar_url: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserRegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=6, max_length=128)
    avatar_url: str | None = Field(default=None, max_length=2048)


class UserLoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=255, description="Email or username")
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ─────────────────────────────────────────────────────────────
# Workspace schemas
# ─────────────────────────────────────────────────────────────

class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    slug: str | None = Field(default=None, min_length=1, max_length=64, pattern=r"^[a-z0-9-]+$")


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)


class WorkspaceResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    description: str | None
    owner_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceMemberResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    user: UserResponse
    role: WorkspaceRole
    created_at: datetime

    model_config = {"from_attributes": True}


class AddWorkspaceMemberRequest(BaseModel):
    user_id: UUID
    role: WorkspaceRole = WorkspaceRole.MEMBER


# ─────────────────────────────────────────────────────────────
# Project schemas
# ─────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    slug: str | None = Field(default=None, min_length=1, max_length=64, pattern=r"^[a-z0-9-]+$")


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)


class ProjectResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    slug: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectMemberResponse(BaseModel):
    id: UUID
    project_id: UUID
    user: UserResponse
    role: ProjectRole
    created_at: datetime

    model_config = {"from_attributes": True}


class AddProjectMemberRequest(BaseModel):
    user_id: UUID
    role: ProjectRole = ProjectRole.MEMBER


# ─────────────────────────────────────────────────────────────
# Label schemas
# ─────────────────────────────────────────────────────────────

class LabelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    color: str = Field(
        default="#6366f1",
        pattern=r"^#[0-9a-fA-F]{6}$",
        description="Hex color code e.g. #6366f1",
    )


class LabelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    color: str | None = Field(
        default=None, pattern=r"^#[0-9a-fA-F]{6}$"
    )


class LabelResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    color: str

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────
# Task schemas
# ─────────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    description: str | None = Field(default=None)
    status: TaskStatus = TaskStatus.BACKLOG
    priority: TaskPriority = TaskPriority.MEDIUM
    assignee_id: UUID | None = None
    due_date: date | None = None
    label_ids: list[UUID] = Field(default_factory=list)


class TaskUpdate(BaseModel):
    """All fields optional; version is required for OCC."""

    title: str | None = Field(default=None, min_length=1, max_length=512)
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    assignee_id: UUID | None = None
    due_date: date | None = None
    version: int = Field(description="Current task version for optimistic concurrency")


class TaskResponse(BaseModel):
    id: UUID
    project_id: UUID
    workspace_id: UUID
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    assignee: UserResponse | None
    creator: UserResponse
    labels: list[LabelResponse]
    due_date: date | None
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskLabelRequest(BaseModel):
    label_id: UUID


# ─────────────────────────────────────────────────────────────
# Comment schemas
# ─────────────────────────────────────────────────────────────

class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=10000)


class CommentUpdate(BaseModel):
    body: str = Field(min_length=1, max_length=10000)


class CommentResponse(BaseModel):
    id: UUID
    task_id: UUID
    author: UserResponse
    body: str
    is_edited: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────
# Activity schemas
# ─────────────────────────────────────────────────────────────

class ActivityLogResponse(BaseModel):
    id: UUID
    task_id: UUID
    actor: UserResponse
    action: ActivityAction
    old_value: str | None
    new_value: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
