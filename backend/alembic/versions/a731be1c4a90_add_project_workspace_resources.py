"""add project workspace resources

Revision ID: a731be1c4a90
Revises: 9c4f2d1a7b30
Create Date: 2026-10-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a731be1c4a90"
down_revision: Union[str, None] = "9c4f2d1a7b30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_resources",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("added_by", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("resource_type", sa.String(length=30), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("file_name", sa.String(length=255), nullable=True),
        sa.Column("content_type", sa.String(length=120), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["added_by"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_project_resources_project_id",
        "project_resources",
        ["project_id"],
    )
    op.create_index(
        "ix_project_resources_added_by",
        "project_resources",
        ["added_by"],
    )


def downgrade() -> None:
    op.drop_index("ix_project_resources_added_by", table_name="project_resources")
    op.drop_index("ix_project_resources_project_id", table_name="project_resources")
    op.drop_table("project_resources")
