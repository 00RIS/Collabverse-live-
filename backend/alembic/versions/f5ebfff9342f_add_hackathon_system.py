"""add hackathon system

Revision ID: f5ebfff9342f
Revises: f489b6a4671a
Create Date: 2026-10-07 13:38:02.905542
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f5ebfff9342f"
down_revision: Union[str, None] = "f489b6a4671a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # =====================================================
    # HACKATHONS
    # =====================================================

    op.create_table(
        "hackathons",

        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "title",
            sa.String(length=255),
            nullable=False,
        ),

        sa.Column(
            "description",
            sa.Text(),
            nullable=False,
        ),

        sa.Column(
            "domain",
            sa.String(length=255),
            nullable=True,
        ),

        sa.Column(
            "organizer_name",
            sa.String(length=255),
            nullable=True,
        ),

        sa.Column(
            "created_by",
            sa.UUID(),
            nullable=True,
        ),

        sa.Column(
            "source_type",
            sa.Enum(
                "COLLABVERSE",
                "EXTERNAL",
                name="hackathon_source_type",
            ),
            nullable=False,
        ),

        sa.Column(
            "source_name",
            sa.String(length=255),
            nullable=True,
        ),

        sa.Column(
            "source_url",
            sa.String(length=1000),
            nullable=True,
        ),

        sa.Column(
            "external_id",
            sa.String(length=255),
            nullable=True,
        ),

        sa.Column(
            "last_synced_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "mode",
            sa.Enum(
                "ONLINE",
                "OFFLINE",
                "HYBRID",
                name="hackathon_mode",
            ),
            nullable=False,
        ),

        sa.Column(
            "difficulty",
            sa.Enum(
                "BEGINNER",
                "INTERMEDIATE",
                "ADVANCED",
                "OPEN",
                name="hackathon_difficulty",
            ),
            nullable=False,
        ),

        sa.Column(
            "status",
            sa.Enum(
                "DRAFT",
                "REGISTRATION_OPEN",
                "REGISTRATION_CLOSED",
                "ONGOING",
                "COMPLETED",
                "CANCELLED",
                name="hackathon_status",
            ),
            nullable=False,
        ),

        sa.Column(
            "location",
            sa.String(length=255),
            nullable=True,
        ),

        sa.Column(
            "min_team_size",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "max_team_size",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "registration_deadline",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "start_date",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "end_date",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "prize_details",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "registration_url",
            sa.String(length=1000),
            nullable=True,
        ),

        sa.Column(
            "banner_url",
            sa.String(length=1000),
            nullable=True,
        ),

        sa.Column(
            "is_verified",
            sa.Boolean(),
            nullable=False,
        ),

        sa.Column(
            "is_featured",
            sa.Boolean(),
            nullable=False,
        ),

        sa.Column(
            "is_active",
            sa.Boolean(),
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
            ["created_by"],
            ["users.id"],
            ondelete="SET NULL",
        ),

        sa.PrimaryKeyConstraint("id"),
    )

    # =====================================================
    # HACKATHON INDEXES
    # =====================================================

    op.create_index(
        op.f("ix_hackathons_created_by"),
        "hackathons",
        ["created_by"],
        unique=False,
    )

    op.create_index(
        op.f("ix_hackathons_difficulty"),
        "hackathons",
        ["difficulty"],
        unique=False,
    )

    op.create_index(
        op.f("ix_hackathons_domain"),
        "hackathons",
        ["domain"],
        unique=False,
    )

    op.create_index(
        op.f("ix_hackathons_external_id"),
        "hackathons",
        ["external_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_hackathons_is_active"),
        "hackathons",
        ["is_active"],
        unique=False,
    )

    op.create_index(
        op.f("ix_hackathons_is_featured"),
        "hackathons",
        ["is_featured"],
        unique=False,
    )

    op.create_index(
        op.f("ix_hackathons_is_verified"),
        "hackathons",
        ["is_verified"],
        unique=False,
    )

    op.create_index(
        op.f("ix_hackathons_location"),
        "hackathons",
        ["location"],
        unique=False,
    )

    op.create_index(
        op.f("ix_hackathons_mode"),
        "hackathons",
        ["mode"],
        unique=False,
    )

    op.create_index(
        op.f("ix_hackathons_organizer_name"),
        "hackathons",
        ["organizer_name"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_hackathons_registration_deadline"
        ),
        "hackathons",
        ["registration_deadline"],
        unique=False,
    )

    op.create_index(
        op.f("ix_hackathons_source_name"),
        "hackathons",
        ["source_name"],
        unique=False,
    )

    op.create_index(
        op.f("ix_hackathons_source_type"),
        "hackathons",
        ["source_type"],
        unique=False,
    )

    op.create_index(
        op.f("ix_hackathons_status"),
        "hackathons",
        ["status"],
        unique=False,
    )

    op.create_index(
        op.f("ix_hackathons_title"),
        "hackathons",
        ["title"],
        unique=False,
    )

    # =====================================================
    # HACKATHON PARTICIPANTS
    # =====================================================

    op.create_table(
        "hackathon_participants",

        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "hackathon_id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "user_id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "team_name",
            sa.String(length=255),
            nullable=True,
        ),

        sa.Column(
            "status",
            sa.Enum(
                "REGISTERED",
                "WITHDRAWN",
                "COMPLETED",
                name="hackathon_participant_status",
            ),
            nullable=False,
        ),

        sa.Column(
            "registered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),

        sa.ForeignKeyConstraint(
            ["hackathon_id"],
            ["hackathons.id"],
            ondelete="CASCADE",
        ),

        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),

        sa.PrimaryKeyConstraint("id"),

        sa.UniqueConstraint(
            "hackathon_id",
            "user_id",
            name=(
                "uq_hackathon_participant_user"
            ),
        ),
    )

    op.create_index(
        op.f(
            "ix_hackathon_participants_hackathon_id"
        ),
        "hackathon_participants",
        ["hackathon_id"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_hackathon_participants_status"
        ),
        "hackathon_participants",
        ["status"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_hackathon_participants_user_id"
        ),
        "hackathon_participants",
        ["user_id"],
        unique=False,
    )

    # =====================================================
    # HACKATHON SKILLS
    # =====================================================

    op.create_table(
        "hackathon_skills",

        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "hackathon_id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "skill_id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "required_level",
            sa.Integer(),
            nullable=True,
        ),

        sa.Column(
            "priority",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "mandatory",
            sa.Boolean(),
            nullable=False,
        ),

        sa.ForeignKeyConstraint(
            ["hackathon_id"],
            ["hackathons.id"],
            ondelete="CASCADE",
        ),

        sa.ForeignKeyConstraint(
            ["skill_id"],
            ["skills.id"],
            ondelete="CASCADE",
        ),

        sa.PrimaryKeyConstraint("id"),

        sa.UniqueConstraint(
            "hackathon_id",
            "skill_id",
            name="uq_hackathon_skill",
        ),
    )

    op.create_index(
        op.f(
            "ix_hackathon_skills_hackathon_id"
        ),
        "hackathon_skills",
        ["hackathon_id"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_hackathon_skills_skill_id"
        ),
        "hackathon_skills",
        ["skill_id"],
        unique=False,
    )


def downgrade() -> None:

    # =====================================================
    # HACKATHON SKILLS
    # =====================================================

    op.drop_index(
        op.f(
            "ix_hackathon_skills_skill_id"
        ),
        table_name="hackathon_skills",
    )

    op.drop_index(
        op.f(
            "ix_hackathon_skills_hackathon_id"
        ),
        table_name="hackathon_skills",
    )

    op.drop_table(
        "hackathon_skills"
    )

    # =====================================================
    # HACKATHON PARTICIPANTS
    # =====================================================

    op.drop_index(
        op.f(
            "ix_hackathon_participants_user_id"
        ),
        table_name="hackathon_participants",
    )

    op.drop_index(
        op.f(
            "ix_hackathon_participants_status"
        ),
        table_name="hackathon_participants",
    )

    op.drop_index(
        op.f(
            "ix_hackathon_participants_hackathon_id"
        ),
        table_name="hackathon_participants",
    )

    op.drop_table(
        "hackathon_participants"
    )

    # =====================================================
    # HACKATHONS
    # =====================================================

    op.drop_index(
        op.f("ix_hackathons_title"),
        table_name="hackathons",
    )

    op.drop_index(
        op.f("ix_hackathons_status"),
        table_name="hackathons",
    )

    op.drop_index(
        op.f("ix_hackathons_source_type"),
        table_name="hackathons",
    )

    op.drop_index(
        op.f("ix_hackathons_source_name"),
        table_name="hackathons",
    )

    op.drop_index(
        op.f(
            "ix_hackathons_registration_deadline"
        ),
        table_name="hackathons",
    )

    op.drop_index(
        op.f(
            "ix_hackathons_organizer_name"
        ),
        table_name="hackathons",
    )

    op.drop_index(
        op.f("ix_hackathons_mode"),
        table_name="hackathons",
    )

    op.drop_index(
        op.f("ix_hackathons_location"),
        table_name="hackathons",
    )

    op.drop_index(
        op.f("ix_hackathons_is_verified"),
        table_name="hackathons",
    )

    op.drop_index(
        op.f("ix_hackathons_is_featured"),
        table_name="hackathons",
    )

    op.drop_index(
        op.f("ix_hackathons_is_active"),
        table_name="hackathons",
    )

    op.drop_index(
        op.f("ix_hackathons_external_id"),
        table_name="hackathons",
    )

    op.drop_index(
        op.f("ix_hackathons_domain"),
        table_name="hackathons",
    )

    op.drop_index(
        op.f("ix_hackathons_difficulty"),
        table_name="hackathons",
    )

    op.drop_index(
        op.f("ix_hackathons_created_by"),
        table_name="hackathons",
    )

    op.drop_table(
        "hackathons"
    )