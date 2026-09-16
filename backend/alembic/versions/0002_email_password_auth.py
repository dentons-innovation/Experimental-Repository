"""Add password_hash and drop clerk_id from users table.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-16
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add password_hash column
    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(255), nullable=False, server_default=""),
    )
    # Remove server_default so new rows must explicitly specify password_hash
    op.alter_column("users", "password_hash", server_default=None)

    # Drop clerk_id index and column
    op.drop_index("idx_users_clerk_id", table_name="users")
    op.drop_column("users", "clerk_id")


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column("clerk_id", sa.String(128), nullable=True),
    )
    op.create_index("idx_users_clerk_id", "users", ["clerk_id"], unique=True)
    op.drop_column("users", "password_hash")
