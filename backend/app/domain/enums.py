"""Domain enumerations.

Pure Python enums with no framework dependencies.
These are the source of truth for all status/priority/role values.
The frontend mirrors these constants (kept in sync via types/).
"""

from __future__ import annotations

import enum


class TaskStatus(str, enum.Enum):
    """Task workflow states in logical progression order."""

    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"


class TaskPriority(str, enum.Enum):
    """Task priority levels in ascending order of urgency."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WorkspaceRole(str, enum.Enum):
    """Roles a user can hold within a workspace."""

    OWNER = "owner"
    MEMBER = "member"


class ProjectRole(str, enum.Enum):
    """Roles a user can hold within a project."""

    ADMIN = "admin"
    MEMBER = "member"


class ActivityAction(str, enum.Enum):
    """Audit log action types for task activity."""

    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    STATUS_CHANGED = "status_changed"
    PRIORITY_CHANGED = "priority_changed"
    ASSIGNED = "assigned"
    UNASSIGNED = "unassigned"
    LABEL_ADDED = "label_added"
    LABEL_REMOVED = "label_removed"
    DUE_DATE_SET = "due_date_set"
    DUE_DATE_CLEARED = "due_date_cleared"
    COMMENT_ADDED = "comment_added"
    COMMENT_EDITED = "comment_edited"
    COMMENT_DELETED = "comment_deleted"
    TITLE_CHANGED = "title_changed"
    DESCRIPTION_CHANGED = "description_changed"
