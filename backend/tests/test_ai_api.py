from unittest.mock import patch
from uuid import uuid4

from app.ai.schemas import AIResponse
from app.main import app
from fastapi.testclient import TestClient


client = TestClient(app)


def register_and_login():
    password = "StrongPassword123!"
    email = f"ai_endpoint_{uuid4().hex}@example.com"

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
        },
    )

    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert login_response.status_code == 200

    return login_response.json()["access_token"]


def test_generate_requires_authentication():
    response = client.post(
        "/api/v1/ai/generate",
        json={
            "prompt": "Hello COSMOW",
        },
    )

    assert response.status_code == 401


def test_generate_returns_ai_response():
    token = register_and_login()

    mock_response = AIResponse(
        content="COSMOW response",
        model="test-model",
        provider="mock",
    )

    with patch(
        "app.api.ai.ai_service.generate",
        return_value=mock_response,
    ) as generate:

        response = client.post(
            "/api/v1/ai/generate",
            headers={
                "Authorization": f"Bearer {token}",
            },
            json={
                "prompt": "Hello COSMOW",
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "content": "COSMOW response",
        "model": "test-model",
        "provider": "mock",
    }

    generate.assert_called_once()


def test_generate_rejects_invalid_prompt():
    token = register_and_login()

    response = client.post(
        "/api/v1/ai/generate",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "prompt": "",
        },
    )

    assert response.status_code == 422


def test_generate_returns_service_unavailable_on_provider_failure():
    token = register_and_login()

    from app.services.ai_service import AIServiceError

    with patch(
        "app.api.ai.ai_service.generate",
        side_effect=AIServiceError(
            "AI service is temporarily unavailable."
        ),
    ):

        response = client.post(
            "/api/v1/ai/generate",
            headers={
                "Authorization": f"Bearer {token}",
            },
            json={
                "prompt": "Hello COSMOW",
            },
        )

    assert response.status_code == 503
