"""add daily assessment tracking

Revision ID: 22761354a64c
Revises: e602182067ad
Create Date: 2026-09-14 21:29:17.520253
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "22761354a64c"
down_revision: Union[str, None] = "e602182067ad"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "daily_assessments",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "student_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "attempt_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "assessment_date",
            sa.Date(),
            nullable=False,
        ),
        sa.Column(
            "question_count",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "completed",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["assessment_attempts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["student_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "student_id",
            "assessment_date",
            name="uq_daily_assessment_student_date",
        ),
    )

    op.create_index(
        op.f("ix_daily_assessments_assessment_date"),
        "daily_assessments",
        ["assessment_date"],
        unique=False,
    )

    op.create_index(
        op.f("ix_daily_assessments_attempt_id"),
        "daily_assessments",
        ["attempt_id"],
        unique=True,
    )

    op.create_index(
        op.f("ix_daily_assessments_student_id"),
        "daily_assessments",
        ["student_id"],
        unique=False,
    )

    op.create_table(
        "assessment_answers",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "attempt_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "question_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "selected_option_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "is_correct",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "answered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["assessment_attempts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["assessment_questions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["selected_option_id"],
            ["question_options.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "attempt_id",
            "question_id",
            name="uq_assessment_answer_attempt_question",
        ),
    )

    op.create_index(
        op.f("ix_assessment_answers_attempt_id"),
        "assessment_answers",
        ["attempt_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_assessment_answers_question_id"),
        "assessment_answers",
        ["question_id"],
        unique=False,
    )

    op.create_table(
        "daily_assessment_questions",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "daily_assessment_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "question_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "position",
            sa.Integer(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["daily_assessment_id"],
            ["daily_assessments.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["assessment_questions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "daily_assessment_id",
            "question_id",
            name="uq_daily_assessment_question",
        ),
    )

    op.create_index(
        op.f(
            "ix_daily_assessment_questions_daily_assessment_id"
        ),
        "daily_assessment_questions",
        ["daily_assessment_id"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_daily_assessment_questions_question_id"
        ),
        "daily_assessment_questions",
        ["question_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f(
            "ix_daily_assessment_questions_question_id"
        ),
        table_name="daily_assessment_questions",
    )

    op.drop_index(
        op.f(
            "ix_daily_assessment_questions_daily_assessment_id"
        ),
        table_name="daily_assessment_questions",
    )

    op.drop_table(
        "daily_assessment_questions"
    )

    op.drop_index(
        op.f(
            "ix_assessment_answers_question_id"
        ),
        table_name="assessment_answers",
    )

    op.drop_index(
        op.f(
            "ix_assessment_answers_attempt_id"
        ),
        table_name="assessment_answers",
    )

    op.drop_table(
        "assessment_answers"
    )

    op.drop_index(
        op.f(
            "ix_daily_assessments_student_id"
        ),
        table_name="daily_assessments",
    )

    op.drop_index(
        op.f(
            "ix_daily_assessments_attempt_id"
        ),
        table_name="daily_assessments",
    )

    op.drop_index(
        op.f(
            "ix_daily_assessments_assessment_date"
        ),
        table_name="daily_assessments",
    )

    op.drop_table(
        "daily_assessments"
    )