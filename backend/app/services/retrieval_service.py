import math

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.embeddings import EmbeddingError, GeminiEmbeddingProvider
from app.core.config import settings
from app.models.document import Document
from app.models.document_chunk import DocumentChunk


class RetrievalError(Exception):
    """Safe retrieval failure."""


def retrieve_chunks(
    db: Session,
    *,
    user_id: int,
    question: str,
    limit: int = 5,
    provider: GeminiEmbeddingProvider | None = None,
) -> list[dict]:
    if not question.strip():
        raise ValueError("Question cannot be empty.")
    if not 1 <= limit <= 10:
        raise ValueError("Limit must be between 1 and 10.")

    owns_provider = provider is None
    embedding_provider = provider or GeminiEmbeddingProvider()

    try:
        query_vector = embedding_provider.embed(
            question,
            task_type="RETRIEVAL_QUERY",
        )

        if (
            len(query_vector) != settings.gemini_embedding_dimensions
            or not all(math.isfinite(value) for value in query_vector)
        ):
            raise RetrievalError("Embedding provider returned an invalid vector.")

        query_norm = math.hypot(*query_vector)
        if not math.isfinite(query_norm) or query_norm == 0:
            raise RetrievalError("Query embedding is invalid.")

        cosine_distance = DocumentChunk.embedding_vector.cosine_distance(
            query_vector
        ).label("cosine_distance")

        rows = db.execute(
            select(DocumentChunk, Document.title, cosine_distance)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(
                Document.user_id == user_id,
                Document.status == "indexed",
                DocumentChunk.embedding_vector.is_not(None),
            )
            .order_by(cosine_distance)
            .limit(limit)
        ).all()

        results = []
        for chunk, title, distance in rows:
            if distance is None or not math.isfinite(distance):
                continue

            results.append({
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "title": title,
                "content": chunk.content,
                "similarity": 1.0 - distance,
            })

        return results

    except (EmbeddingError, RetrievalError):
        raise
    except Exception as exc:
        raise RetrievalError("Document retrieval failed.") from exc
    finally:
        if owns_provider:
            embedding_provider.close()
