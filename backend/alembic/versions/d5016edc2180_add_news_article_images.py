"""add news article images

Revision ID: d5016edc2180
Revises: c42a1804f9d1
Create Date: 2026-10-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d5016edc2180"
down_revision: Union[str, None] = "c42a1804f9d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("news_articles", sa.Column("image_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("news_articles", "image_url")
