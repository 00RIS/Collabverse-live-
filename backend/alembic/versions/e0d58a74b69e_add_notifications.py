"""add notifications

Revision ID: e0d58a74b69e
Revises: 564402593c12
Create Date: 2026-09-13 12:28:43.726975
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e0d58a74b69e"
down_revision: Union[str, None] = "564402593c12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "actor_id",
            sa.UUID(),
            nullable=True,
        ),
        sa.Column(
            "notification_type",
            sa.Enum(
                "CONNECTION_REQUEST",
                "CONNECTION_ACCEPTED",
                "POST_LIKE",
                "POST_COMMENT",
                "MENTOR_REQUEST",
                "MENTOR_ACCEPTED",
                "PROJECT_INVITE",
                "PROJECT_UPDATE",
                "APPLICATION_UPDATE",
                "SYSTEM",
                name="notification_type",
            ),
            nullable=False,
        ),
        sa.Column(
            "title",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "message",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "entity_id",
            sa.UUID(),
            nullable=True,
        ),
        sa.Column(
            "entity_type",
            sa.String(length=50),
            nullable=True,
        ),
        sa.Column(
            "is_read",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_notifications_actor_id"),
        "notifications",
        ["actor_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_notifications_created_at"),
        "notifications",
        ["created_at"],
        unique=False,
    )

    op.create_index(
        op.f("ix_notifications_entity_id"),
        "notifications",
        ["entity_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_notifications_is_read"),
        "notifications",
        ["is_read"],
        unique=False,
    )

    op.create_index(
        op.f("ix_notifications_notification_type"),
        "notifications",
        ["notification_type"],
        unique=False,
    )

    op.create_index(
        op.f("ix_notifications_user_id"),
        "notifications",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_notifications_user_id"),
        table_name="notifications",
    )

    op.drop_index(
        op.f("ix_notifications_notification_type"),
        table_name="notifications",
    )

    op.drop_index(
        op.f("ix_notifications_is_read"),
        table_name="notifications",
    )

    op.drop_index(
        op.f("ix_notifications_entity_id"),
        table_name="notifications",
    )

    op.drop_index(
        op.f("ix_notifications_created_at"),
        table_name="notifications",
    )

    op.drop_index(
        op.f("ix_notifications_actor_id"),
        table_name="notifications",
    )

    op.drop_table("notifications")

    op.execute(
        "DROP TYPE IF EXISTS notification_type"
    )