"""Add pgvector embedding storage.

Revision ID: a31c9e7f42bd
Revises: fdaa4ad5b70a
"""

from alembic import op

revision = "a31c9e7f42bd"
down_revision = "fdaa4ad5b70a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        "ALTER TABLE document_chunks "
        "ADD COLUMN embedding_vector vector(768)"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE document_chunks "
        "DROP COLUMN embedding_vector"
    )
