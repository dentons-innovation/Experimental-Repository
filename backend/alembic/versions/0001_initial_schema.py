"""Initial database schema.

Revision ID: 0001
Revises:
Create Date: 2026-09-15

Creates all tables, indexes, constraints, and enum types.
Hand-written for clarity; subsequent migrations will use autogenerate.

Design notes:
- UUIDv7 primary keys (stored as PostgreSQL UUID type) for time-ordering
  and efficient B-tree indexing.
- Composite indexes designed from actual access patterns (see docs/database.md).
- Cascade deletes are used only where the child has no independent lifecycle.
- workspace_id denormalized onto tasks and activity_logs for workspace-scoped
  queries without joining through projects.
- Task.version enables optimistic concurrency control.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enum types ───────────────────────────────────────────
    op.execute(
        "CREATE TYPE workspace_role AS ENUM ('owner', 'member')"
    )
    op.execute(
        "CREATE TYPE project_role AS ENUM ('admin', 'member')"
    )
    op.execute(
        "CREATE TYPE task_status AS ENUM "
        "('backlog', 'todo', 'in_progress', 'in_review', 'done')"
    )
    op.execute(
        "CREATE TYPE task_priority AS ENUM "
        "('low', 'medium', 'high', 'critical')"
    )
    op.execute(
        "CREATE TYPE activity_action AS ENUM ("
        "'task_created', 'task_updated', 'status_changed', "
        "'priority_changed', 'assigned', 'unassigned', "
        "'label_added', 'label_removed', "
        "'due_date_set', 'due_date_cleared', "
        "'comment_added', 'comment_edited', 'comment_deleted', "
        "'title_changed', 'description_changed')"
    )

    # ── users ────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("clerk_id", sa.String(128), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("avatar_url", sa.String(2048), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_users_clerk_id", "users", ["clerk_id"], unique=True)
    op.create_index("idx_users_email", "users", ["email"], unique=True)
    op.create_index("idx_users_username", "users", ["username"], unique=True)

    # ── workspaces ───────────────────────────────────────────
    op.create_table(
        "workspaces",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "owner_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_workspaces_slug", "workspaces", ["slug"], unique=True)
    op.create_index("idx_workspaces_owner_id", "workspaces", ["owner_id"])

    # ── workspace_members ────────────────────────────────────
    op.create_table(
        "workspace_members",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.Enum("owner", "member", name="workspace_role", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_members"),
    )
    op.create_index(
        "idx_workspace_members_workspace_id", "workspace_members", ["workspace_id"]
    )
    op.create_index(
        "idx_workspace_members_user_id", "workspace_members", ["user_id"]
    )

    # ── projects ─────────────────────────────────────────────
    op.create_table(
        "projects",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "workspace_id", "slug", name="uq_project_workspace_slug"
        ),
    )
    op.create_index("idx_projects_workspace_id", "projects", ["workspace_id"])

    # ── project_members ──────────────────────────────────────
    op.create_table(
        "project_members",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.Enum("admin", "member", name="project_role", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_members"),
    )
    op.create_index("idx_project_members_project_id", "project_members", ["project_id"])
    op.create_index("idx_project_members_user_id", "project_members", ["user_id"])

    # ── labels ───────────────────────────────────────────────
    op.create_table(
        "labels",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("color", sa.String(7), nullable=False, server_default="#6366f1"),
        sa.UniqueConstraint(
            "workspace_id", "name", name="uq_label_workspace_name"
        ),
    )
    op.create_index("idx_labels_workspace_id", "labels", ["workspace_id"])

    # ── tasks ────────────────────────────────────────────────
    op.create_table(
        "tasks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "backlog", "todo", "in_progress", "in_review", "done",
                name="task_status",
                create_type=False,
            ),
            nullable=False,
            server_default="backlog",
        ),
        sa.Column(
            "priority",
            sa.Enum(
                "low", "medium", "high", "critical",
                name="task_priority",
                create_type=False,
            ),
            nullable=False,
            server_default="medium",
        ),
        sa.Column(
            "assignee_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "creator_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("due_date", sa.Date, nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    # Composite indexes from access patterns
    op.create_index("idx_tasks_project_status", "tasks", ["project_id", "status"])
    op.create_index("idx_tasks_project_priority", "tasks", ["project_id", "priority"])
    op.create_index("idx_tasks_project_assignee", "tasks", ["project_id", "assignee_id"])
    op.create_index("idx_tasks_workspace_id", "tasks", ["workspace_id"])
    op.create_index("idx_tasks_due_date", "tasks", ["due_date"])
    op.create_index("idx_tasks_creator_id", "tasks", ["creator_id"])
    op.create_index("idx_tasks_project_created_at", "tasks", ["project_id", "created_at"])

    # ── task_labels ──────────────────────────────────────────
    op.create_table(
        "task_labels",
        sa.Column(
            "task_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "label_id",
            UUID(as_uuid=True),
            sa.ForeignKey("labels.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_index("idx_task_labels_task_id", "task_labels", ["task_id"])
    op.create_index("idx_task_labels_label_id", "task_labels", ["label_id"])

    # ── comments ─────────────────────────────────────────────
    op.create_table(
        "comments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "task_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "author_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=False,
        ),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("is_edited", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_comments_task_id_created_at", "comments", ["task_id", "created_at"]
    )

    # ── activity_logs ────────────────────────────────────────
    op.create_table(
        "activity_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "task_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "actor_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "action",
            sa.Enum(
                "task_created", "task_updated", "status_changed",
                "priority_changed", "assigned", "unassigned",
                "label_added", "label_removed",
                "due_date_set", "due_date_cleared",
                "comment_added", "comment_edited", "comment_deleted",
                "title_changed", "description_changed",
                name="activity_action",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("old_value", sa.Text, nullable=True),
        sa.Column("new_value", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_activity_logs_task_id_created_at",
        "activity_logs",
        ["task_id", "created_at"],
    )
    op.create_index(
        "idx_activity_logs_workspace_id_created_at",
        "activity_logs",
        ["workspace_id", "created_at"],
    )
    op.create_index(
        "idx_activity_logs_project_id_created_at",
        "activity_logs",
        ["project_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("activity_logs")
    op.drop_table("comments")
    op.drop_table("task_labels")
    op.drop_table("tasks")
    op.drop_table("labels")
    op.drop_table("project_members")
    op.drop_table("projects")
    op.drop_table("workspace_members")
    op.drop_table("workspaces")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS activity_action")
    op.execute("DROP TYPE IF EXISTS task_priority")
    op.execute("DROP TYPE IF EXISTS task_status")
    op.execute("DROP TYPE IF EXISTS project_role")
    op.execute("DROP TYPE IF EXISTS workspace_role")
