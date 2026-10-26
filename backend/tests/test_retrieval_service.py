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
            (
                SimpleNamespace(
                    id=1,
                    document_id=10,
                    content="Unrelated content",
                    embedding_vector=[0.0, 1.0, 0.0],
                ),
                "Other",
                1.0,
            ),
            (
                SimpleNamespace(
                    id=2,
                    document_id=11,
                    content="Relevant content",
                    embedding_vector=[1.0, 0.0, 0.0],
                ),
                "Relevant",
                0.0,
            ),
        ]


class FakeDB:
    def __init__(self):
        self.statement = None

    def execute(self, statement):
        self.statement = statement
        rows = FakeResult().all()
        rows.sort(key=lambda row: row[2])
        limit_clause = statement._limit_clause
        if limit_clause is not None:
            rows = rows[: int(limit_clause.value)]

        class Result:
            def all(self):
                return rows

        return Result()


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

    compiled = db.statement.compile()
    sql = str(compiled)
    assert "documents.user_id" in sql
    assert "documents.status" in sql
    assert "embedding_vector" in sql
    assert 42 in compiled.params.values()


def test_retrieval_rejects_invalid_limit():
    with pytest.raises(ValueError):
        retrieval_service.retrieve_chunks(
            FakeDB(),
            user_id=1,
            question="Question",
            limit=11,
            provider=FakeProvider(),
        )


def test_retrieval_rejects_empty_question():
    with pytest.raises(ValueError):
        retrieval_service.retrieve_chunks(
            FakeDB(),
            user_id=1,
            question="   ",
            provider=FakeProvider(),
        )

class ConfigurableProvider:
    def __init__(self, vector):
        self.vector = vector

    def embed(self, text, task_type):
        return self.vector


@pytest.mark.parametrize(
    "vector",
    [
        [1.0, 2.0],                 # Wrong dimensions
        [float("nan"), 0.0, 1.0],  # NaN
        [float("inf"), 0.0, 1.0],  # Infinity
        [0.0, 0.0, 0.0],           # Zero vector
        [1.7e308, 1.7e308, 1.7e308],  # Non-finite norm
    ],
)
def test_retrieval_rejects_invalid_query_vectors(monkeypatch, vector):
    monkeypatch.setattr(
        retrieval_service.settings, "gemini_embedding_dimensions", 3
    )

    with pytest.raises(retrieval_service.RetrievalError):
        retrieval_service.retrieve_chunks(
            FakeDB(),
            user_id=7,
            question="Test invalid vector",
            provider=ConfigurableProvider(vector),
        )


def test_retrieval_skips_null_and_nonfinite_distances(monkeypatch):
    monkeypatch.setattr(
        retrieval_service.settings, "gemini_embedding_dimensions", 3
    )

    rows = [
        (
            SimpleNamespace(
                id=1, document_id=10, content="Undefined distance"
            ),
            "Undefined",
            None,
        ),
        (
            SimpleNamespace(
                id=2, document_id=11, content="Invalid distance"
            ),
            "Invalid",
            float("inf"),
        ),
        (
            SimpleNamespace(
                id=3, document_id=12, content="Valid result"
            ),
            "Valid",
            0.2,
        ),
    ]

    class DistanceDB:
        def execute(self, statement):
            class Result:
                def all(self):
                    return rows
            return Result()

    results = retrieval_service.retrieve_chunks(
        DistanceDB(),
        user_id=7,
        question="Find valid content",
        provider=FakeProvider(),
    )

    assert len(results) == 1
    assert results[0]["content"] == "Valid result"
    assert results[0]["similarity"] == pytest.approx(0.8)
