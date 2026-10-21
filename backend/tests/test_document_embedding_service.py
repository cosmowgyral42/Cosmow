import pytest
from sqlalchemy import select

from app.ai.embeddings import EmbeddingError
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.user import User
from app.services.document_embedding_service import (
    DocumentEmbeddingError,
    embed_document,
)


class FakeEmbeddingProvider:
    def __init__(self, vectors=None, fail_at=None):
        self.vectors = vectors or []
        self.fail_at = fail_at
        self.calls = 0

    def embed(self, text, *, task_type="RETRIEVAL_DOCUMENT"):
        self.calls += 1
        if self.fail_at == self.calls:
            raise EmbeddingError("Gemini quota unavailable.")
        return self.vectors[self.calls - 1]

    def close(self):
        pass


def create_document_with_chunks(db, email, chunk_texts):
    user = User(
        email=email,
        password_hash="test-hash",
        is_active=True,
        timezone="Asia/Kolkata",
    )
    db.add(user)
    db.flush()

    document = Document(
        user_id=user.id,
        title="Embedding test",
        original_filename="embedding.txt",
        content_type="text/plain",
        file_size_bytes=sum(len(text) for text in chunk_texts),
        status="uploaded",
    )
    db.add(document)
    db.flush()

    chunks = [
        DocumentChunk(
            document_id=document.id,
            chunk_index=index,
            content=text,
            char_count=len(text),
        )
        for index, text in enumerate(chunk_texts)
    ]
    db.add_all(chunks)
    db.commit()
    return user, document, chunks


def test_embed_document_persists_vectors(monkeypatch, unique_email):
    monkeypatch.setattr(settings, "gemini_embedding_dimensions", 3)
    db = SessionLocal()
    try:
        user, document, chunks = create_document_with_chunks(
            db, unique_email, ["first chunk", "second chunk"]
        )
        provider = FakeEmbeddingProvider(
            vectors=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        )

        count = embed_document(
            db,
            user_id=user.id,
            document_id=document.id,
            provider=provider,
        )

        assert count == 2
        db.refresh(document)
        assert document.status == "indexed"

        saved = db.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document.id)
            .order_by(DocumentChunk.chunk_index)
        ).all()
        assert [chunk.embedding for chunk in saved] == [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
        ]
        assert provider.calls == 2
    finally:
        db.rollback()
        db.close()


def test_embed_document_hides_other_users_documents(unique_email):
    db = SessionLocal()
    try:
        _, document, _ = create_document_with_chunks(
            db, unique_email, ["private chunk"]
        )

        with pytest.raises(LookupError, match="not found"):
            embed_document(
                db,
                user_id=-999,
                document_id=document.id,
                provider=FakeEmbeddingProvider(vectors=[[0.1] * 3]),
            )
    finally:
        db.rollback()
        db.close()


def test_embedding_failure_saves_no_partial_vectors(
    monkeypatch, unique_email
):
    monkeypatch.setattr(settings, "gemini_embedding_dimensions", 3)
    db = SessionLocal()
    try:
        user, document, _ = create_document_with_chunks(
            db, unique_email, ["first chunk", "second chunk"]
        )
        provider = FakeEmbeddingProvider(
            vectors=[[0.1, 0.2, 0.3]],
            fail_at=2,
        )

        with pytest.raises(EmbeddingError):
            embed_document(
                db,
                user_id=user.id,
                document_id=document.id,
                provider=provider,
            )

        db.expire_all()
        saved = db.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document.id)
            .order_by(DocumentChunk.chunk_index)
        ).all()
        assert all(chunk.embedding is None for chunk in saved)
        assert db.get(Document, document.id).status == "uploaded"
    finally:
        db.rollback()
        db.close()


def test_invalid_vector_dimensions_are_rejected(monkeypatch, unique_email):
    monkeypatch.setattr(settings, "gemini_embedding_dimensions", 3)
    db = SessionLocal()
    try:
        user, document, _ = create_document_with_chunks(
            db, unique_email, ["first chunk"]
        )
        provider = FakeEmbeddingProvider(vectors=[[0.1, 0.2]])

        with pytest.raises(DocumentEmbeddingError, match="invalid vector"):
            embed_document(
                db,
                user_id=user.id,
                document_id=document.id,
                provider=provider,
            )

        db.expire_all()
        chunk = db.scalar(
            select(DocumentChunk).where(
                DocumentChunk.document_id == document.id
            )
        )
        assert chunk.embedding is None
        assert db.get(Document, document.id).status == "uploaded"
    finally:
        db.rollback()
        db.close()


def test_document_without_chunks_fails_safely(unique_email):
    db = SessionLocal()
    try:
        user, document, _ = create_document_with_chunks(db, unique_email, [])

        with pytest.raises(DocumentEmbeddingError, match="no chunks"):
            embed_document(
                db,
                user_id=user.id,
                document_id=document.id,
                provider=FakeEmbeddingProvider(),
            )
    finally:
        db.rollback()
        db.close()
