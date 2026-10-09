"""add AI quota reservation counters

Revision ID: cdf92169874a
Revises: bd7f35a280ac
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "cdf92169874a"
down_revision: Union[str, Sequence[str], None] = "bd7f35a280ac"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ai_global_usage",
        sa.Column(
            "reserved_count",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.add_column(
        "ai_usage",
        sa.Column(
            "reserved_count",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.execute(
        "UPDATE ai_global_usage "
        "SET reserved_count = 0 "
        "WHERE reserved_count IS NULL"
    )

    op.execute(
        "UPDATE ai_usage "
        "SET reserved_count = 0 "
        "WHERE reserved_count IS NULL"
    )

    op.alter_column(
        "ai_global_usage",
        "reserved_count",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.alter_column(
        "ai_usage",
        "reserved_count",
        existing_type=sa.Integer(),
        nullable=False,
    )


def downgrade() -> None:
    op.drop_column("ai_global_usage", "reserved_count")
    op.drop_column("ai_usage", "reserved_count")
