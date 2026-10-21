"""add supabase user id mapping

Revision ID: fdaa4ad5b70a
Revises: 8d41d59a1b26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "fdaa4ad5b70a"
down_revision: Union[str, Sequence[str], None] = "8d41d59a1b26"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("supabase_user_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        "ix_users_supabase_user_id",
        "users",
        ["supabase_user_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_users_supabase_user_id", table_name="users")
    op.drop_column("users", "supabase_user_id")
