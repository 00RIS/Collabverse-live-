"""add saved posts and post reports

Revision ID: b16e27c4a901
Revises: fc3d27d99723
Create Date: 2026-10-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b16e27c4a901"
down_revision: Union[str, None] = "fc3d27d99723"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "saved_posts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("post_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("post_id", "user_id", name="uq_saved_post_user_post"),
    )
    op.create_index(op.f("ix_saved_posts_post_id"), "saved_posts", ["post_id"], unique=False)
    op.create_index(op.f("ix_saved_posts_user_id"), "saved_posts", ["user_id"], unique=False)

    op.create_table(
        "post_reports",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("post_id", sa.UUID(), nullable=False),
        sa.Column("reporter_id", sa.UUID(), nullable=False),
        sa.Column("reason", sa.String(length=60), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reporter_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("post_id", "reporter_id", name="uq_post_report_reporter_post"),
    )
    op.create_index(op.f("ix_post_reports_post_id"), "post_reports", ["post_id"], unique=False)
    op.create_index(op.f("ix_post_reports_reporter_id"), "post_reports", ["reporter_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_post_reports_reporter_id"), table_name="post_reports")
    op.drop_index(op.f("ix_post_reports_post_id"), table_name="post_reports")
    op.drop_table("post_reports")
    op.drop_index(op.f("ix_saved_posts_user_id"), table_name="saved_posts")
    op.drop_index(op.f("ix_saved_posts_post_id"), table_name="saved_posts")
    op.drop_table("saved_posts")
