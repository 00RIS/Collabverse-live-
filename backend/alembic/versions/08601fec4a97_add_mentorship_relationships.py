"""add mentorship relationships

Revision ID: 08601fec4a97
Revises: f5ebfff9342f
Create Date: 2026-10-08 19:24:29.279449
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "08601fec4a97"
down_revision: Union[str, None] = "f5ebfff9342f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mentorships",

        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "mentor_profile_id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "mentee_user_id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "request_message",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "goals",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "ACCEPTED",
                "REJECTED",
                "CANCELLED",
                "COMPLETED",
                name="mentorship_status",
            ),
            nullable=False,
        ),

        sa.Column(
            "response_message",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "completion_note",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "cancellation_reason",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),

        sa.Column(
            "responded_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "cancelled_at",
            sa.DateTime(timezone=True),
            nullable=True,
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
            ["mentee_user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),

        sa.ForeignKeyConstraint(
            ["mentor_profile_id"],
            ["mentor_profiles.id"],
            ondelete="CASCADE",
        ),

        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_mentorships_mentee_user_id"),
        "mentorships",
        ["mentee_user_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_mentorships_mentor_profile_id"),
        "mentorships",
        ["mentor_profile_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_mentorships_requested_at"),
        "mentorships",
        ["requested_at"],
        unique=False,
    )

    op.create_index(
        op.f("ix_mentorships_status"),
        "mentorships",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_mentorships_status"),
        table_name="mentorships",
    )

    op.drop_index(
        op.f("ix_mentorships_requested_at"),
        table_name="mentorships",
    )

    op.drop_index(
        op.f("ix_mentorships_mentor_profile_id"),
        table_name="mentorships",
    )

    op.drop_index(
        op.f("ix_mentorships_mentee_user_id"),
        table_name="mentorships",
    )

    op.drop_table("mentorships")

    # PostgreSQL keeps enum types after the table is dropped,
    # so remove it explicitly during downgrade.
    sa.Enum(
        name="mentorship_status",
    ).drop(
        op.get_bind(),
        checkfirst=True,
    )