from types import SimpleNamespace

import pytest

from app.services import retrieval_service


class FakeProvider:
    def embed(self, text, task_type):
        assert task_type == "RETRIEVAL_QUERY"
        return [1.0, 0.0, 0.0]


class FakeResult:
    def all(self):
        return [
            (SimpleNamespace(
                id=1, document_id=10, content="Unrelated content",
                embedding=[0.0, 1.0, 0.0],
            ), "Other"),
            (SimpleNamespace(
                id=2, document_id=11, content="Relevant content",
                embedding=[1.0, 0.0, 0.0],
            ), "Relevant"),
        ]


class FakeDB:
    def __init__(self):
        self.statement = None

    def execute(self, statement):
        self.statement = statement
        return FakeResult()


def test_retrieval_ranks_most_similar_chunk_first(monkeypatch):
    monkeypatch.setattr(
        retrieval_service.settings, "gemini_embedding_dimensions", 3
    )
    db = FakeDB()

    results = retrieval_service.retrieve_chunks(
        db,
        user_id=7,
        question="What is relevant?",
        limit=2,
        provider=FakeProvider(),
    )

    assert results[0]["content"] == "Relevant content"
    assert results[0]["similarity"] == pytest.approx(1.0)
    assert results[1]["content"] == "Unrelated content"


def test_retrieval_query_filters_by_document_owner(monkeypatch):
    monkeypatch.setattr(
        retrieval_service.settings, "gemini_embedding_dimensions", 3
    )
    db = FakeDB()

    retrieval_service.retrieve_chunks(
        db,
        user_id=42,
        question="Find my content",
        provider=FakeProvider(),
    )

    sql = str(db.statement.compile(compile_kwargs={"literal_binds": True}))
    assert "documents.user_id = 42" in sql
    assert "documents.status = 'indexed'" in sql


def test_retrieval_rejects_invalid_limit():
    with pytest.raises(ValueError):
        retrieval_service.retrieve_chunks(
            FakeDB(),
            user_id=1,
            question="Question",
            limit=11,
            provider=FakeProvider(),
        )
