
"""add oauth accounts

Revision ID: f8fdf005f024
Revises: 9eeec4b061fd
Create Date: 2026-10-09 12:43:15.398853
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f8fdf005f024"
down_revision: Union[str, None] = "9eeec4b061fd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_oauth_accounts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("provider_user_id", sa.String(length=255), nullable=False),
        sa.Column("provider_email", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "provider IN ('google', 'microsoft', 'linkedin')",
            name="ck_oauth_supported_provider",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider",
            "provider_user_id",
            name="uq_oauth_provider_identity",
        ),
        sa.UniqueConstraint(
            "user_id",
            "provider",
            name="uq_oauth_user_provider",
        ),
    )

    op.create_index(
        "ix_user_oauth_accounts_user_id",
        "user_oauth_accounts",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_user_oauth_accounts_user_id",
        table_name="user_oauth_accounts",
    )

    op.drop_table("user_oauth_accounts")
