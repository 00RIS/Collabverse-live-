"""add connections

Revision ID: 358050211f77
Revises: 2a0355ecc774
Create Date: 2026-09-12 17:05:19.651304
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "358050211f77"
down_revision: Union[str, None] = "2a0355ecc774"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "connections",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("requester_id", sa.UUID(), nullable=False),
        sa.Column("recipient_id", sa.UUID(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "ACCEPTED",
                "REJECTED",
                name="connection_status",
            ),
            nullable=False,
        ),
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
        sa.ForeignKeyConstraint(
            ["recipient_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["requester_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "requester_id",
            "recipient_id",
            name="uq_connection_requester_recipient",
        ),
    )

    op.create_index(
        op.f("ix_connections_recipient_id"),
        "connections",
        ["recipient_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_connections_requester_id"),
        "connections",
        ["requester_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_connections_requester_id"),
        table_name="connections",
    )

    op.drop_index(
        op.f("ix_connections_recipient_id"),
        table_name="connections",
    )

    op.drop_table("connections")

    op.execute("DROP TYPE IF EXISTS connection_status")