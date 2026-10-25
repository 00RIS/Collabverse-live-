
"""add messaging tables

Revision ID: 9eeec4b061fd
Revises: 08601fec4a97
Create Date: 2026-10-09 10:42:28.484403
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "9eeec4b061fd"
down_revision: Union[str, None] = "08601fec4a97"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


conversation_type_enum = postgresql.ENUM(
    "DIRECT",
    "MENTORSHIP",
    "PROJECT",
    "GROUP",
    name="conversation_type",
    create_type=False,
)


def upgrade() -> None:

    # --------------------------------------------------------
    # CREATE POSTGRESQL ENUM
    # --------------------------------------------------------

    conversation_type_enum.create(
        op.get_bind(),
        checkfirst=True,
    )

    # --------------------------------------------------------
    # CONVERSATIONS
    # --------------------------------------------------------

    op.create_table(
        "conversations",

        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "conversation_type",
            conversation_type_enum,
            nullable=False,
        ),

        sa.Column(
            "title",
            sa.String(length=255),
            nullable=True,
        ),

        sa.Column(
            "mentorship_id",
            sa.UUID(),
            nullable=True,
        ),

        sa.Column(
            "project_id",
            sa.UUID(),
            nullable=True,
        ),

        sa.Column(
            "created_by",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
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

        sa.CheckConstraint(
            "conversation_type != 'MENTORSHIP' "
            "OR mentorship_id IS NOT NULL",
            name="ck_mentorship_conversation_has_mentorship",
        ),

        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            ondelete="RESTRICT",
        ),

        sa.ForeignKeyConstraint(
            ["mentorship_id"],
            ["mentorships.id"],
            ondelete="SET NULL",
        ),

        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="SET NULL",
        ),

        sa.PrimaryKeyConstraint("id"),

        sa.UniqueConstraint("mentorship_id"),
    )

    op.create_index(
        "ix_conversations_conversation_type",
        "conversations",
        ["conversation_type"],
        unique=False,
    )

    # --------------------------------------------------------
    # CONVERSATION PARTICIPANTS
    # --------------------------------------------------------

    op.create_table(
        "conversation_participants",

        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "conversation_id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "user_id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),

        sa.Column(
            "last_read_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "is_muted",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),

        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            ondelete="CASCADE",
        ),

        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),

        sa.PrimaryKeyConstraint("id"),

        sa.UniqueConstraint(
            "conversation_id",
            "user_id",
            name="uq_conversation_participant",
        ),
    )

    op.create_index(
        "ix_conversation_participants_conversation_id",
        "conversation_participants",
        ["conversation_id"],
        unique=False,
    )

    op.create_index(
        "ix_conversation_participants_user_id",
        "conversation_participants",
        ["user_id"],
        unique=False,
    )

    # --------------------------------------------------------
    # MESSAGES
    # --------------------------------------------------------

    op.create_table(
        "messages",

        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "conversation_id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "sender_id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "content",
            sa.Text(),
            nullable=False,
        ),

        sa.Column(
            "is_edited",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),

        sa.Column(
            "is_deleted",
            sa.Boolean(),
            server_default=sa.text("false"),
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
            ["conversation_id"],
            ["conversations.id"],
            ondelete="CASCADE",
        ),

        sa.ForeignKeyConstraint(
            ["sender_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),

        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_messages_conversation_created",
        "messages",
        ["conversation_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:

    # --------------------------------------------------------
    # DROP MESSAGES
    # --------------------------------------------------------

    op.drop_index(
        "ix_messages_conversation_created",
        table_name="messages",
    )

    op.drop_table("messages")

    # --------------------------------------------------------
    # DROP PARTICIPANTS
    # --------------------------------------------------------

    op.drop_index(
        "ix_conversation_participants_user_id",
        table_name="conversation_participants",
    )

    op.drop_index(
        "ix_conversation_participants_conversation_id",
        table_name="conversation_participants",
    )

    op.drop_table("conversation_participants")

    # --------------------------------------------------------
    # DROP CONVERSATIONS
    # --------------------------------------------------------

    op.drop_index(
        "ix_conversations_conversation_type",
        table_name="conversations",
    )

    op.drop_table("conversations")

    # --------------------------------------------------------
    # DROP ENUM
    # --------------------------------------------------------

    conversation_type_enum.drop(
        op.get_bind(),
        checkfirst=True,
    )
