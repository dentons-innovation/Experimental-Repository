"""Unit tests verifying SQLAlchemy Enum columns and PostgreSQL compatibility."""

from __future__ import annotations

from sqlalchemy import Enum
from sqlalchemy.dialects import postgresql

from app.domain.enums import (
    ActivityAction,
    ProjectRole,
    TaskPriority,
    TaskStatus,
    WorkspaceRole,
)
from app.domain.models import ActivityLog, ProjectMember, Task, WorkspaceMember


class TestEnumPostgresCompatibility:
    """Ensure all SQLAlchemy Enum columns bind lowercase values matching PostgreSQL ENUM types."""

    def test_workspace_role_enum_values(self):
        col_type = WorkspaceMember.__table__.c.role.type
        assert isinstance(col_type, Enum)
        assert col_type.enums == ["owner", "member"]

        bind_fn = col_type.bind_processor(postgresql.dialect())
        assert bind_fn is not None
        assert bind_fn(WorkspaceRole.OWNER) == "owner"
        assert bind_fn(WorkspaceRole.MEMBER) == "member"

        result_fn = col_type.result_processor(postgresql.dialect(), None)
        assert result_fn is not None
        assert result_fn("owner") is WorkspaceRole.OWNER
        assert result_fn("member") is WorkspaceRole.MEMBER

    def test_project_role_enum_values(self):
        col_type = ProjectMember.__table__.c.role.type
        assert isinstance(col_type, Enum)
        assert col_type.enums == ["admin", "member"]

        bind_fn = col_type.bind_processor(postgresql.dialect())
        assert bind_fn is not None
        assert bind_fn(ProjectRole.ADMIN) == "admin"
        assert bind_fn(ProjectRole.MEMBER) == "member"

        result_fn = col_type.result_processor(postgresql.dialect(), None)
        assert result_fn is not None
        assert result_fn("admin") is ProjectRole.ADMIN
        assert result_fn("member") is ProjectRole.MEMBER

    def test_task_status_enum_values(self):
        col_type = Task.__table__.c.status.type
        assert isinstance(col_type, Enum)
        expected = ["backlog", "todo", "in_progress", "in_review", "done"]
        assert col_type.enums == expected

        bind_fn = col_type.bind_processor(postgresql.dialect())
        assert bind_fn is not None
        for status in TaskStatus:
            assert bind_fn(status) == status.value

    def test_task_priority_enum_values(self):
        col_type = Task.__table__.c.priority.type
        assert isinstance(col_type, Enum)
        expected = ["low", "medium", "high", "critical"]
        assert col_type.enums == expected

        bind_fn = col_type.bind_processor(postgresql.dialect())
        assert bind_fn is not None
        for priority in TaskPriority:
            assert bind_fn(priority) == priority.value

    def test_activity_action_enum_values(self):
        col_type = ActivityLog.__table__.c.action.type
        assert isinstance(col_type, Enum)

        bind_fn = col_type.bind_processor(postgresql.dialect())
        assert bind_fn is not None
        for action in ActivityAction:
            assert bind_fn(action) == action.value
