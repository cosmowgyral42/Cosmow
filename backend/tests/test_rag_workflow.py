from app.core.config import settings
from app.ai.schemas import AIResponse
from app.api import rag as rag_api
from app.services import document_embedding_service, retrieval_service


def test_upload_embed_retrieve_and_answer_end_to_end(
    client, unique_email, monkeypatch
):
    class FakeEmbeddingProvider:
        def embed(self, text, *, task_type):
            assert task_type in {"RETRIEVAL_DOCUMENT", "RETRIEVAL_QUERY"}
            return [1.0] + [0.0] * (settings.gemini_embedding_dimensions - 1)

        def close(self):
            pass

    class FakeAIProvider:
        def generate(self, request):
            assert "COSMOW integration evidence" in request.prompt
            return AIResponse(
                content="The uploaded document contains COSMOW integration evidence.",
                model="test-model",
                provider="test",
            )

    monkeypatch.setattr(
        document_embedding_service,
        "GeminiEmbeddingProvider",
        FakeEmbeddingProvider,
    )
    monkeypatch.setattr(
        retrieval_service,
        "GeminiEmbeddingProvider",
        FakeEmbeddingProvider,
    )
    monkeypatch.setattr(
        rag_api.ai_service.provider,
        "generate",
        FakeAIProvider().generate,
    )

    registration = client.post(
        "/api/v1/auth/register",
        json={
            "email": unique_email,
            "password": "TestPassword123",
            "timezone": "Asia/Kolkata",
        },
    )
    assert registration.status_code in {200, 201}

    login = client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": "TestPassword123"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    upload = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files={
            "file": (
                "integration.txt",
                b"COSMOW integration evidence",
                "text/plain",
            )
        },
    )
    assert upload.status_code == 201
    document_id = upload.json()["id"]

    embedding = client.post(
        f"/api/v1/documents/{document_id}/embed",
        headers=headers,
    )
    assert embedding.status_code == 200
    assert embedding.json()["status"] == "indexed"
    assert embedding.json()["chunks_embedded"] >= 1

    answer = client.post(
        "/api/v1/rag/ask",
        headers=headers,
        json={"question": "What evidence is in my document?"},
    )
    assert answer.status_code == 200
    result = answer.json()
    assert "COSMOW integration evidence" in result["answer"]
    assert any(source["document_id"] == document_id for source in result["sources"])
