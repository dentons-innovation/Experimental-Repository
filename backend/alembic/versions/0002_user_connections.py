"""Add user connections table.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-17

Adds user_connections table with canonical pair uniqueness for
bidirectional connection requests. Prevents both directional and
reciprocal duplicates at the database level.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM, UUID


revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── Enum type ────────────────────────────────────────────
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'connection_status') THEN "
        "CREATE TYPE connection_status AS ENUM ('pending', 'accepted', 'rejected'); "
        "END IF; END $$;"
    )

    # ── user_connections ─────────────────────────────────────
    op.create_table(
        "user_connections",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_lo",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_hi",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "requester_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            ENUM(
                "pending",
                "accepted",
                "rejected",
                name="connection_status",
                create_type=False,
            ),
            nullable=False,
            server_default="pending",
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
        # Constraints
        sa.UniqueConstraint("user_lo", "user_hi", name="uq_user_connections_pair"),
        sa.CheckConstraint("user_lo < user_hi", name="ck_user_connections_canonical"),
        sa.CheckConstraint(
            "requester_id IN (user_lo, user_hi)",
            name="ck_user_connections_requester_in_pair",
        ),
    )

    # ── Indexes ──────────────────────────────────────────────
    op.create_index("idx_user_connections_user_lo", "user_connections", ["user_lo"])
    op.create_index("idx_user_connections_user_hi", "user_connections", ["user_hi"])
    op.create_index("idx_user_connections_status", "user_connections", ["status"])


def downgrade() -> None:
    op.drop_table("user_connections")
    op.execute("DROP TYPE IF EXISTS connection_status")
