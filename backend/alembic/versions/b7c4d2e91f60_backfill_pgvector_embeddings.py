"""Backfill native pgvector embeddings from legacy JSON.

Revision ID: b7c4d2e91f60
Revises: a31c9e7f42bd
"""

from alembic import op

revision = "b7c4d2e91f60"
down_revision = "a31c9e7f42bd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE document_chunks
        SET embedding_vector = embedding::text::vector
        WHERE embedding_vector IS NULL
          AND CASE
              WHEN json_typeof(embedding) = 'array'
              THEN json_array_length(embedding) = 768
              ELSE FALSE
          END
        """
    )


def downgrade() -> None:
    # Keep vectors: they may contain embeddings created after backfilling.
    pass
