from sqlalchemy import delete, select

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.user import User
from app.services.document_embedding_service import embed_document
from app.services.retrieval_service import retrieve_chunks


DIMENSIONS = 768


class FakeEmbeddingProvider:
    def embed(self, text, *, task_type):
        if task_type == "RETRIEVAL_QUERY":
            return [1.0] + [0.0] * (DIMENSIONS - 1)

        vectors = {
            "Relevant chunk about planetary orbits":
                [1.0] + [0.0] * (DIMENSIONS - 1),
            "Unrelated chunk about cooking":
                [0.0, 1.0] + [0.0] * (DIMENSIONS - 2),
            "Private matching chunk":
                [1.0] + [0.0] * (DIMENSIONS - 1),
        }
        return vectors[text]

    def close(self):
        pass


def test_real_pgvector_retrieval_and_user_isolation(
    monkeypatch, unique_email
):
    monkeypatch.setattr(settings, "gemini_embedding_dimensions", DIMENSIONS)
    db = SessionLocal()
    emails = [unique_email, f"private_{unique_email}"]

    try:
        users = [
            User(
                email=email,
                password_hash="integration-test-hash",
                is_active=True,
                timezone="Asia/Kolkata",
            )
            for email in emails
        ]
        db.add_all(users)
        db.flush()

        documents = [
            Document(
                user_id=users[0].id,
                title="Astronomy notes",
                original_filename="astronomy.txt",
                content_type="text/plain",
                file_size_bytes=80,
                status="uploaded",
            ),
            Document(
                user_id=users[1].id,
                title="Private notes",
                original_filename="private.txt",
                content_type="text/plain",
                file_size_bytes=30,
                status="uploaded",
            ),
        ]
        db.add_all(documents)
        db.flush()

        chunks = [
            DocumentChunk(
                document_id=documents[0].id,
                chunk_index=0,
                content="Relevant chunk about planetary orbits",
                char_count=39,
            ),
            DocumentChunk(
                document_id=documents[0].id,
                chunk_index=1,
                content="Unrelated chunk about cooking",
                char_count=31,
            ),
            DocumentChunk(
                document_id=documents[1].id,
                chunk_index=0,
                content="Private matching chunk",
                char_count=23,
            ),
        ]
        db.add_all(chunks)
        db.commit()

        provider = FakeEmbeddingProvider()

        assert embed_document(
            db,
            user_id=users[0].id,
            document_id=documents[0].id,
            provider=provider,
        ) == 2

        assert embed_document(
            db,
            user_id=users[1].id,
            document_id=documents[1].id,
            provider=provider,
        ) == 1

        db.refresh(documents[0])
        assert documents[0].status == "indexed"

        saved_vectors = db.scalars(
            select(DocumentChunk.embedding_vector).where(
                DocumentChunk.document_id == documents[0].id
            )
        ).all()
        assert len(saved_vectors) == 2
        assert all(len(vector) == DIMENSIONS for vector in saved_vectors)

        results = retrieve_chunks(
            db,
            user_id=users[0].id,
            question="Find planetary orbit information",
            limit=5,
            provider=provider,
        )

        assert results
        assert results[0]["content"] == (
            "Relevant chunk about planetary orbits"
        )
        assert results[0]["similarity"] > 0.99
        assert all(
            result["title"] != "Private notes"
            for result in results
        )
        assert all(
            result["content"] != "Private matching chunk"
            for result in results
        )

    finally:
        db.rollback()
        user_ids = db.scalars(
            select(User.id).where(User.email.in_(emails))
        ).all()

        if user_ids:
            document_ids = db.scalars(
                select(Document.id).where(
                    Document.user_id.in_(user_ids)
                )
            ).all()

            if document_ids:
                db.execute(
                    delete(DocumentChunk).where(
                        DocumentChunk.document_id.in_(document_ids)
                    )
                )
                db.execute(
                    delete(Document).where(
                        Document.id.in_(document_ids)
                    )
                )

            db.execute(delete(User).where(User.id.in_(user_ids)))
            db.commit()

        db.close()
