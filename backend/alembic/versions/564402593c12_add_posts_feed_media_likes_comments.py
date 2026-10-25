"""add posts feed media likes comments

Revision ID: 564402593c12
Revises: 358050211f77
Create Date: 2026-09-13 09:05:31.941963
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "564402593c12"
down_revision: Union[str, None] = "358050211f77"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------------------------------------------------------
    # POSTS
    # ---------------------------------------------------------

    op.create_table(
        "posts",

        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "author_id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "post_type",
            sa.Enum(
                "TEXT",
                "MEDIA",
                "PROJECT",
                name="post_type",
            ),
            nullable=False,
        ),

        sa.Column(
            "content",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "project_id",
            sa.UUID(),
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
            ["author_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),

        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="SET NULL",
        ),

        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_posts_author_id"),
        "posts",
        ["author_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_posts_project_id"),
        "posts",
        ["project_id"],
        unique=False,
    )

    # ---------------------------------------------------------
    # POST COMMENTS
    # ---------------------------------------------------------

    op.create_table(
        "post_comments",

        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "post_id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "user_id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "content",
            sa.Text(),
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
            ["post_id"],
            ["posts.id"],
            ondelete="CASCADE",
        ),

        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),

        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_post_comments_post_id"),
        "post_comments",
        ["post_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_post_comments_user_id"),
        "post_comments",
        ["user_id"],
        unique=False,
    )

    # ---------------------------------------------------------
    # POST LIKES
    # ---------------------------------------------------------

    op.create_table(
        "post_likes",

        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "post_id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "user_id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),

        sa.ForeignKeyConstraint(
            ["post_id"],
            ["posts.id"],
            ondelete="CASCADE",
        ),

        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),

        sa.PrimaryKeyConstraint("id"),

        sa.UniqueConstraint(
            "post_id",
            "user_id",
            name="uq_post_like",
        ),
    )

    op.create_index(
        op.f("ix_post_likes_post_id"),
        "post_likes",
        ["post_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_post_likes_user_id"),
        "post_likes",
        ["user_id"],
        unique=False,
    )

    # ---------------------------------------------------------
    # POST MEDIA
    # ---------------------------------------------------------

    op.create_table(
        "post_media",

        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "post_id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "media_type",
            sa.Enum(
                "IMAGE",
                "VIDEO",
                name="post_media_type",
            ),
            nullable=False,
        ),

        sa.Column(
            "media_url",
            sa.String(length=2000),
            nullable=False,
        ),

        sa.Column(
            "thumbnail_url",
            sa.String(length=2000),
            nullable=True,
        ),

        sa.Column(
            "position",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),

        sa.ForeignKeyConstraint(
            ["post_id"],
            ["posts.id"],
            ondelete="CASCADE",
        ),

        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_post_media_post_id"),
        "post_media",
        ["post_id"],
        unique=False,
    )


def downgrade() -> None:
    # ---------------------------------------------------------
    # POST MEDIA
    # ---------------------------------------------------------

    op.drop_index(
        op.f("ix_post_media_post_id"),
        table_name="post_media",
    )

    op.drop_table("post_media")

    # ---------------------------------------------------------
    # POST LIKES
    # ---------------------------------------------------------

    op.drop_index(
        op.f("ix_post_likes_user_id"),
        table_name="post_likes",
    )

    op.drop_index(
        op.f("ix_post_likes_post_id"),
        table_name="post_likes",
    )

    op.drop_table("post_likes")

    # ---------------------------------------------------------
    # POST COMMENTS
    # ---------------------------------------------------------

    op.drop_index(
        op.f("ix_post_comments_user_id"),
        table_name="post_comments",
    )

    op.drop_index(
        op.f("ix_post_comments_post_id"),
        table_name="post_comments",
    )

    op.drop_table("post_comments")

    # ---------------------------------------------------------
    # POSTS
    # ---------------------------------------------------------

    op.drop_index(
        op.f("ix_posts_project_id"),
        table_name="posts",
    )

    op.drop_index(
        op.f("ix_posts_author_id"),
        table_name="posts",
    )

    op.drop_table("posts")

    # PostgreSQL enum cleanup
    op.execute(
        "DROP TYPE IF EXISTS post_media_type"
    )

    op.execute(
        "DROP TYPE IF EXISTS post_type"
    )