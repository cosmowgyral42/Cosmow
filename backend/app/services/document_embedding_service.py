import math

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.embeddings import EmbeddingError, GeminiEmbeddingProvider
from app.core.config import settings
from app.models.document import Document
from app.models.document_chunk import DocumentChunk


class DocumentEmbeddingError(Exception):
    """Safe, user-facing document embedding failure."""


def embed_document(
    db: Session,
    *,
    user_id: int,
    document_id: int,
    provider: GeminiEmbeddingProvider | None = None,
) -> int:
    document = db.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == user_id,
        )
    )
    if document is None:
        raise LookupError("Document not found.")

    chunks = db.scalars(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
    ).all()

    if not chunks:
        raise DocumentEmbeddingError("Document has no chunks to embed.")

    embedding_provider = provider or GeminiEmbeddingProvider()
    owns_provider = provider is None

    try:
        vectors = [
            embedding_provider.embed(
                chunk.content,
                task_type="RETRIEVAL_DOCUMENT",
            )
            for chunk in chunks
        ]

        expected_dimensions = settings.gemini_embedding_dimensions
        if any(
            len(vector) != expected_dimensions
            or not all(math.isfinite(value) for value in vector)
            for vector in vectors
        ):
            raise DocumentEmbeddingError(
                "Embedding provider returned an invalid vector."
            )

        for chunk, vector in zip(chunks, vectors):
            chunk.embedding = vector

        document.status = "indexed"
        db.commit()
        return len(chunks)

    except (EmbeddingError, DocumentEmbeddingError):
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise DocumentEmbeddingError(
            "Document embedding failed. No vectors were saved."
        ) from exc
    finally:
        if owns_provider:
            embedding_provider.close()
