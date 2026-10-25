"""add user preferences interests goals learning skills

Revision ID: e602182067ad
Revises: e55a3834e5c4
Create Date: 2026-09-14 20:39:13.602789
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# =========================================================
# REVISION IDENTIFIERS
# =========================================================

revision: str = "e602182067ad"

down_revision: Union[str, None] = "e55a3834e5c4"

branch_labels: Union[
    str,
    Sequence[str],
    None,
] = None

depends_on: Union[
    str,
    Sequence[str],
    None,
] = None


# =========================================================
# POSTGRES ENUM TYPES
# =========================================================

interest_category_enum = postgresql.ENUM(
    "TECHNOLOGY",
    "BUSINESS",
    "FINANCE",
    "MARKETING",
    "STARTUPS",
    "ECONOMY",
    "RESEARCH",
    "HEALTHCARE",
    "DESIGN",
    "LAW",
    "EDUCATION",
    "CYBERSECURITY",
    "DATA_SCIENCE",
    "ARTIFICIAL_INTELLIGENCE",
    "ENTREPRENEURSHIP",
    "OPERATIONS",
    "GLOBAL_AFFAIRS",
    "OTHER",
    name="interest_category",
    create_type=False,
)


goal_type_enum = postgresql.ENUM(
    "CAREER",
    "LEARNING",
    "PROJECT",
    "INTERNSHIP",
    "JOB",
    "RESEARCH",
    "STARTUP",
    "NETWORKING",
    "PERSONAL",
    "OTHER",
    name="goal_type",
    create_type=False,
)


goal_status_enum = postgresql.ENUM(
    "ACTIVE",
    "COMPLETED",
    "PAUSED",
    "CANCELLED",
    name="goal_status",
    create_type=False,
)


learning_priority_enum = postgresql.ENUM(
    "LOW",
    "MEDIUM",
    "HIGH",
    name="learning_priority",
    create_type=False,
)


# =========================================================
# UPGRADE
# =========================================================

def upgrade() -> None:
    bind = op.get_bind()

    # -----------------------------------------------------
    # CREATE ENUM TYPES
    # -----------------------------------------------------

    interest_category_enum.create(
        bind,
        checkfirst=True,
    )

    goal_type_enum.create(
        bind,
        checkfirst=True,
    )

    goal_status_enum.create(
        bind,
        checkfirst=True,
    )

    learning_priority_enum.create(
        bind,
        checkfirst=True,
    )

    # -----------------------------------------------------
    # USER INTERESTS
    # -----------------------------------------------------

    op.create_table(
        "user_interests",

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
            "name",
            sa.String(length=150),
            nullable=False,
        ),

        sa.Column(
            "category",
            interest_category_enum,
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

        sa.PrimaryKeyConstraint(
            "id",
        ),

        sa.UniqueConstraint(
            "user_id",
            "name",
            name="uq_user_interest_name",
        ),
    )

    op.create_index(
        op.f(
            "ix_user_interests_user_id"
        ),
        "user_interests",
        ["user_id"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_user_interests_name"
        ),
        "user_interests",
        ["name"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_user_interests_category"
        ),
        "user_interests",
        ["category"],
        unique=False,
    )

    # -----------------------------------------------------
    # USER GOALS
    # -----------------------------------------------------

    op.create_table(
        "user_goals",

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
            "title",
            sa.String(length=255),
            nullable=False,
        ),

        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "goal_type",
            goal_type_enum,
            nullable=False,
        ),

        sa.Column(
            "status",
            goal_status_enum,
            nullable=False,
        ),

        sa.Column(
            "target_date",
            sa.Date(),
            nullable=True,
        ),

        sa.Column(
            "priority",
            sa.Integer(),
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
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),

        sa.PrimaryKeyConstraint(
            "id",
        ),
    )

    op.create_index(
        op.f(
            "ix_user_goals_user_id"
        ),
        "user_goals",
        ["user_id"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_user_goals_title"
        ),
        "user_goals",
        ["title"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_user_goals_goal_type"
        ),
        "user_goals",
        ["goal_type"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_user_goals_status"
        ),
        "user_goals",
        ["status"],
        unique=False,
    )

    # -----------------------------------------------------
    # USER LEARNING SKILLS
    # -----------------------------------------------------

    op.create_table(
        "user_learning_skills",

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
            "skill_id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "target_level",
            sa.Integer(),
            nullable=True,
        ),

        sa.Column(
            "priority",
            learning_priority_enum,
            nullable=False,
        ),

        sa.Column(
            "reason",
            sa.String(length=500),
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
            ["skill_id"],
            ["skills.id"],
            ondelete="CASCADE",
        ),

        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),

        sa.PrimaryKeyConstraint(
            "id",
        ),

        sa.UniqueConstraint(
            "user_id",
            "skill_id",
            name="uq_user_learning_skill",
        ),
    )

    op.create_index(
        op.f(
            "ix_user_learning_skills_user_id"
        ),
        "user_learning_skills",
        ["user_id"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_user_learning_skills_skill_id"
        ),
        "user_learning_skills",
        ["skill_id"],
        unique=False,
    )

    # -----------------------------------------------------
    # USER PERSONALIZATION SETTINGS
    # -----------------------------------------------------

    op.create_table(
        "user_preferences",

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
            "personalized_news_enabled",
            sa.Boolean(),
            nullable=False,
        ),

        sa.Column(
            "news_categories",
            postgresql.ARRAY(
                sa.String()
            ),
            nullable=False,
        ),

        sa.Column(
            "daily_assessment_enabled",
            sa.Boolean(),
            nullable=False,
        ),

        sa.Column(
            "daily_assessment_question_count",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "project_recommendations_enabled",
            sa.Boolean(),
            nullable=False,
        ),

        sa.Column(
            "internship_recommendations_enabled",
            sa.Boolean(),
            nullable=False,
        ),

        sa.Column(
            "course_recommendations_enabled",
            sa.Boolean(),
            nullable=False,
        ),

        sa.Column(
            "mentor_recommendations_enabled",
            sa.Boolean(),
            nullable=False,
        ),

        sa.Column(
            "preferred_domains",
            postgresql.ARRAY(
                sa.String()
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
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),

        sa.PrimaryKeyConstraint(
            "id",
        ),

        sa.UniqueConstraint(
            "user_id",
        ),
    )

    op.create_index(
        op.f(
            "ix_user_preferences_user_id"
        ),
        "user_preferences",
        ["user_id"],
        unique=True,
    )


# =========================================================
# DOWNGRADE
# =========================================================

def downgrade() -> None:
    bind = op.get_bind()

    # -----------------------------------------------------
    # DROP TABLES
    # -----------------------------------------------------

    op.drop_index(
        op.f(
            "ix_user_preferences_user_id"
        ),
        table_name="user_preferences",
    )

    op.drop_table(
        "user_preferences"
    )

    op.drop_index(
        op.f(
            "ix_user_learning_skills_skill_id"
        ),
        table_name="user_learning_skills",
    )

    op.drop_index(
        op.f(
            "ix_user_learning_skills_user_id"
        ),
        table_name="user_learning_skills",
    )

    op.drop_table(
        "user_learning_skills"
    )

    op.drop_index(
        op.f(
            "ix_user_goals_status"
        ),
        table_name="user_goals",
    )

    op.drop_index(
        op.f(
            "ix_user_goals_goal_type"
        ),
        table_name="user_goals",
    )

    op.drop_index(
        op.f(
            "ix_user_goals_title"
        ),
        table_name="user_goals",
    )

    op.drop_index(
        op.f(
            "ix_user_goals_user_id"
        ),
        table_name="user_goals",
    )

    op.drop_table(
        "user_goals"
    )

    op.drop_index(
        op.f(
            "ix_user_interests_category"
        ),
        table_name="user_interests",
    )

    op.drop_index(
        op.f(
            "ix_user_interests_name"
        ),
        table_name="user_interests",
    )

    op.drop_index(
        op.f(
            "ix_user_interests_user_id"
        ),
        table_name="user_interests",
    )

    op.drop_table(
        "user_interests"
    )

    # -----------------------------------------------------
    # DROP ENUM TYPES
    # -----------------------------------------------------

    learning_priority_enum.drop(
        bind,
        checkfirst=True,
    )

    goal_status_enum.drop(
        bind,
        checkfirst=True,
    )

    goal_type_enum.drop(
        bind,
        checkfirst=True,
    )

    interest_category_enum.drop(
        bind,
        checkfirst=True,
    )