from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.ai.schemas import AIResponse
from app.api.auth_dependencies import get_current_user
from app.api.dependencies import get_db
from app.main import app
from app.services.ai_service import AIServiceError
from app.services import retrieval_service
from app.api import rag as rag_api


def setup_function():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=42)
    app.dependency_overrides[get_db] = lambda: object()


def teardown_function():
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)


def test_rag_returns_answer_and_sources(monkeypatch):
    def fake_retrieve(db, *, user_id, question, limit):
        assert user_id == 42
        return [{
            "document_id": 8,
            "chunk_id": 3,
            "title": "Study Notes",
            "content": "RAG retrieves relevant context.",
            "similarity": 0.95,
        }]

    def fake_generate(*, db, user, request):
        assert user.id == 42
        assert "RAG retrieves relevant context." in request.prompt
        return AIResponse(
            content="RAG retrieves relevant context.",
            model="fake-model",
            provider="fake",
        )

    monkeypatch.setattr(rag_api, "retrieve_chunks", fake_retrieve)
    monkeypatch.setattr(rag_api.ai_service, "generate", fake_generate)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/rag/ask",
            json={"question": "What does RAG do?"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "RAG retrieves relevant context."
    assert data["sources"][0]["document_id"] == 8
    assert data["sources"][0]["chunk_id"] == 3


def test_rag_returns_404_when_no_context(monkeypatch):
    monkeypatch.setattr(
        rag_api, "retrieve_chunks", lambda *args, **kwargs: []
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/rag/ask",
            json={"question": "Question with no documents"},
        )

    assert response.status_code == 404


def test_rag_maps_quota_error_to_429(monkeypatch):
    monkeypatch.setattr(
        rag_api,
        "retrieve_chunks",
        lambda *args, **kwargs: [{
            "document_id": 8,
            "chunk_id": 3,
            "title": "Notes",
            "content": "Context",
            "similarity": 0.8,
        }],
    )

    def fail_generate(**kwargs):
        raise AIServiceError("Daily AI request limit reached.")

    monkeypatch.setattr(rag_api.ai_service, "generate", fail_generate)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/rag/ask",
            json={"question": "Question"},
        )

    assert response.status_code == 429
