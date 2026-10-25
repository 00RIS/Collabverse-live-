
"""allow oauth users without passwords

Revision ID: 2482e018d3f1
Revises: f8fdf005f024
Create Date: 2026-10-09 12:51:11.307524
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2482e018d3f1"
down_revision: Union[str, None] = "f8fdf005f024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Allow OAuth-only users to have no local password.
    op.alter_column(
        "users",
        "hashed_password",
        existing_type=sa.VARCHAR(length=255),
        nullable=True,
    )


def downgrade() -> None:
    # Restoring NOT NULL requires every user to have a password.
    # Refuse to downgrade if passwordless accounts exist.
    connection = op.get_bind()

    passwordless_count = connection.execute(
        sa.text(
            "SELECT COUNT(*) FROM users "
            "WHERE hashed_password IS NULL"
        )
    ).scalar_one()

    if passwordless_count > 0:
        raise RuntimeError(
            "Cannot restore NOT NULL: OAuth-only users exist."
        )

    op.alter_column(
        "users",
        "hashed_password",
        existing_type=sa.VARCHAR(length=255),
        nullable=False,
    )
