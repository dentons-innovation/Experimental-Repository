"""SQLAlchemy ORM models — the persistence layer data model.

Design decisions:
- UUIDv7 primary keys: time-ordered, globally unique, index-friendly.
  Monotonic UUID7 means new rows are appended near the end of the B-tree,
  avoiding page splits common with random UUID4 PKs.
- All timestamps stored in UTC with timezone information.
- workspace_id is denormalized onto Task (and ActivityLog) for efficient
  workspace-scoped queries without joining through project.
- Task.version enables optimistic concurrency control (OCC). On update,
  callers must supply the current version; the UPDATE checks
  WHERE id = ? AND version = ? and increments it atomically.
- No soft-delete in v1 (simplicity); hard delete with appropriate cascades.
- Cascade delete is used only where the child has no independent lifecycle
  (e.g., task labels, activity logs, comments belong to a task).
  Workspace membership is NOT cascade-deleted from the workspace owner
  to prevent accidental lockout.

Indexes are designed from actual access patterns (see docs/database.md):
- Composite indexes on (project_id, status), (project_id, assignee_id), etc.
- All FK columns are individually indexed by convention.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, cast

try:
    import uuid_extensions
except ImportError:
    uuid_extensions = None
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import Uuid as UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.domain.enums import (
    ActivityAction,
    ConnectionStatus,
    ProjectRole,
    TaskPriority,
    TaskStatus,
    WorkspaceRole,
)


def _enum_values(enum_cls: Any) -> list[str]:
    """Extract string values from Enum class for PostgreSQL enum compatibility."""
    return [e.value for e in enum_cls]


# ─────────────────────────────────────────────────────────────
# Base classes
# ─────────────────────────────────────────────────────────────


class Base(DeclarativeBase):
    pass


def _uuid7() -> uuid.UUID:
    """Generate a UUIDv7 — time-ordered, globally unique."""
    if hasattr(uuid, "uuid7"):
        return cast(uuid.UUID, uuid.uuid7())
    if uuid_extensions is not None:
        return cast(uuid.UUID, uuid_extensions.uuid7())
    return uuid.uuid4()


# ─────────────────────────────────────────────────────────────
# User
# ─────────────────────────────────────────────────────────────


class User(Base):
    """Internal user record."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid7
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    username: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    workspace_memberships: Mapped[list[WorkspaceMember]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    project_memberships: Mapped[list[ProjectMember]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


# ─────────────────────────────────────────────────────────────
# User Connection (friend/contact relationship)
# ─────────────────────────────────────────────────────────────


class UserConnection(Base):
    """Bidirectional user-to-user connection with canonical pair ordering.

    Design:
    - ``user_lo`` and ``user_hi`` form a canonical pair where user_lo < user_hi
      (lexicographic UUID comparison).  This means that regardless of which
      direction the request was sent, there is exactly one row per pair.
    - ``requester_id`` stores who initiated the request (must be one of the pair).
    - A UNIQUE(user_lo, user_hi) constraint prevents both duplicate directional
      and reciprocal requests at the database level, even under concurrent races.
    - A CHECK(user_lo < user_hi) constraint enforces canonical ordering so
      application bugs cannot insert (B, A) instead of (A, B).
    """

    __tablename__ = "user_connections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid7
    )
    user_lo: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_hi: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    requester_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[ConnectionStatus] = mapped_column(
        Enum(
            ConnectionStatus,
            name="connection_status",
            values_callable=_enum_values,
        ),
        nullable=False,
        default=ConnectionStatus.PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user_lo_rel: Mapped[User] = relationship("User", foreign_keys=[user_lo])
    user_hi_rel: Mapped[User] = relationship("User", foreign_keys=[user_hi])
    requester: Mapped[User] = relationship("User", foreign_keys=[requester_id])

    __table_args__ = (
        UniqueConstraint("user_lo", "user_hi", name="uq_user_connections_pair"),
        CheckConstraint("user_lo < user_hi", name="ck_user_connections_canonical"),
        CheckConstraint(
            "requester_id IN (user_lo, user_hi)",
            name="ck_user_connections_requester_in_pair",
        ),
        Index("idx_user_connections_user_lo", "user_lo"),
        Index("idx_user_connections_user_hi", "user_hi"),
        Index("idx_user_connections_status", "status"),
    )


# ─────────────────────────────────────────────────────────────
# Workspace
# ─────────────────────────────────────────────────────────────


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid7
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    owner: Mapped[User] = relationship("User", foreign_keys=[owner_id])
    members: Mapped[list[WorkspaceMember]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan"
    )
    projects: Mapped[list[Project]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan"
    )
    labels: Mapped[list[Label]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_workspaces_owner_id", "owner_id"),)


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid7
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[WorkspaceRole] = mapped_column(
        Enum(WorkspaceRole, name="workspace_role", values_callable=_enum_values),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    workspace: Mapped[Workspace] = relationship(back_populates="members")
    user: Mapped[User] = relationship(back_populates="workspace_memberships")

    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_members"),
        Index("idx_workspace_members_workspace_id", "workspace_id"),
        Index("idx_workspace_members_user_id", "user_id"),
    )


# ─────────────────────────────────────────────────────────────
# Project
# ─────────────────────────────────────────────────────────────


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid7
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    workspace: Mapped[Workspace] = relationship(back_populates="projects")
    members: Mapped[list[ProjectMember]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    tasks: Mapped[list[Task]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "slug", name="uq_project_workspace_slug"),
        Index("idx_projects_workspace_id", "workspace_id"),
    )


class ProjectMember(Base):
    __tablename__ = "project_members"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid7
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[ProjectRole] = mapped_column(
        Enum(ProjectRole, name="project_role", values_callable=_enum_values),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    project: Mapped[Project] = relationship(back_populates="members")
    user: Mapped[User] = relationship(back_populates="project_memberships")

    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_members"),
        Index("idx_project_members_project_id", "project_id"),
        Index("idx_project_members_user_id", "user_id"),
    )


# ─────────────────────────────────────────────────────────────
# Label
# ─────────────────────────────────────────────────────────────


class Label(Base):
    __tablename__ = "labels"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid7
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False, default="#6366f1")

    workspace: Mapped[Workspace] = relationship(back_populates="labels")
    task_labels: Mapped[list[TaskLabel]] = relationship(
        back_populates="label", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_label_workspace_name"),
        Index("idx_labels_workspace_id", "workspace_id"),
    )


# ─────────────────────────────────────────────────────────────
# Task
# ─────────────────────────────────────────────────────────────


class Task(Base):
    """Core task entity.

    version column implements optimistic concurrency control (OCC).
    Every successful UPDATE increments version atomically via:
        UPDATE tasks SET ..., version = version + 1
        WHERE id = ? AND version = <expected_version>
    If rowcount == 0, an OptimisticLockError is raised.
    """

    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid7
    )
    # Denormalized workspace_id for efficient workspace-scoped queries
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status", values_callable=_enum_values),
        nullable=False,
        default=TaskStatus.BACKLOG,
    )
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority, name="task_priority", values_callable=_enum_values),
        nullable=False,
        default=TaskPriority.MEDIUM,
    )
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # OCC version counter — starts at 0, incremented on every update
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    project: Mapped[Project] = relationship(back_populates="tasks")
    workspace: Mapped[Workspace] = relationship("Workspace")
    assignee: Mapped[User | None] = relationship("User", foreign_keys=[assignee_id])
    creator: Mapped[User] = relationship("User", foreign_keys=[creator_id])
    task_labels: Mapped[list[TaskLabel]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    labels: Mapped[list[Label]] = relationship(
        secondary="task_labels",
        primaryjoin="Task.id == TaskLabel.task_id",
        secondaryjoin="TaskLabel.label_id == Label.id",
        viewonly=True,
    )
    comments: Mapped[list[Comment]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    activity_logs: Mapped[list[ActivityLog]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # Access pattern: list tasks in project filtered by status
        Index("idx_tasks_project_status", "project_id", "status"),
        # Access pattern: list tasks in project filtered by priority
        Index("idx_tasks_project_priority", "project_id", "priority"),
        # Access pattern: list tasks assigned to a user within project
        Index("idx_tasks_project_assignee", "project_id", "assignee_id"),
        # Access pattern: workspace-level task views
        Index("idx_tasks_workspace_id", "workspace_id"),
        # Access pattern: sorting/filtering by due date
        Index("idx_tasks_due_date", "due_date"),
        # Access pattern: tasks created by a user
        Index("idx_tasks_creator_id", "creator_id"),
        # Access pattern: recently created tasks (default sort)
        Index("idx_tasks_project_created_at", "project_id", "created_at"),
    )


class TaskLabel(Base):
    """Many-to-many association between tasks and labels."""

    __tablename__ = "task_labels"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        primary_key=True,
    )
    label_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("labels.id", ondelete="CASCADE"),
        primary_key=True,
    )

    task: Mapped[Task] = relationship(back_populates="task_labels")
    label: Mapped[Label] = relationship(back_populates="task_labels")

    __table_args__ = (
        Index("idx_task_labels_task_id", "task_id"),
        Index("idx_task_labels_label_id", "label_id"),
    )


# ─────────────────────────────────────────────────────────────
# Comment
# ─────────────────────────────────────────────────────────────


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid7
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_edited: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    task: Mapped[Task] = relationship(back_populates="comments")
    author: Mapped[User] = relationship("User")

    __table_args__ = (
        # Access pattern: list comments for a task ordered by created_at
        Index("idx_comments_task_id_created_at", "task_id", "created_at"),
    )


# ─────────────────────────────────────────────────────────────
# Activity Log
# ─────────────────────────────────────────────────────────────


class ActivityLog(Base):
    """Append-only event log for task mutations.

    workspace_id and project_id are denormalized for efficient
    workspace/project-scoped activity feed queries.
    """

    __tablename__ = "activity_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid7
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    action: Mapped[ActivityAction] = mapped_column(
        Enum(ActivityAction, name="activity_action", values_callable=_enum_values),
        nullable=False,
    )
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    task: Mapped[Task] = relationship(back_populates="activity_logs")
    actor: Mapped[User] = relationship("User")

    __table_args__ = (
        Index("idx_activity_logs_task_id_created_at", "task_id", "created_at"),
        Index(
            "idx_activity_logs_workspace_id_created_at", "workspace_id", "created_at"
        ),
        Index("idx_activity_logs_project_id_created_at", "project_id", "created_at"),
    )
