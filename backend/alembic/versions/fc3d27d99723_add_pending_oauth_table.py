
"""add pending oauth table

Revision ID: fc3d27d99723
Revises: 2482e018d3f1
Create Date: 2026-10-09 23:58:03.188888
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "fc3d27d99723"
down_revision: Union[str, None] = "2482e018d3f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pending_oauth",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "code_hash",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "provider",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "provider_user_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "provider_email",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "display_name",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "user_id",
            sa.UUID(),
            nullable=True,
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_pending_oauth_code_hash",
        "pending_oauth",
        ["code_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pending_oauth_code_hash",
        table_name="pending_oauth",
    )

    op.drop_table("pending_oauth")
