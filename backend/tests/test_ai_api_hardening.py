from unittest.mock import patch
from uuid import uuid4

from app.main import app
from fastapi.testclient import TestClient
from app.services.ai_service import AIServiceError


client = TestClient(app)


def get_token():
    email = f"hardening_{uuid4().hex}@example.com"
    password = "StrongPassword123!"

    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
        },
    )

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 200

    return response.json()["access_token"]


def test_ai_quota_error_maps_to_429():
    token = get_token()

    with patch(
        "app.api.ai.ai_service.generate",
        side_effect=AIServiceError(
            "Daily AI request limit reached."
        ),
    ):
        response = client.post(
            "/api/v1/ai/generate",
            headers={
                "Authorization": f"Bearer {token}",
            },
            json={
                "prompt": "Hello",
            },
        )

    assert response.status_code == 429


def test_ai_provider_failure_maps_to_503():
    token = get_token()

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
                "prompt": "Hello",
            },
        )

    assert response.status_code == 503


def test_ai_error_does_not_leak_provider_details():
    token = get_token()

    with patch(
        "app.api.ai.ai_service.generate",
        side_effect=AIServiceError(
            "OpenRouter API key sk-secret-123 failed."
        ),
    ):
        response = client.post(
            "/api/v1/ai/generate",
            headers={
                "Authorization": f"Bearer {token}",
            },
            json={
                "prompt": "Hello",
            },
        )

    assert response.status_code == 503
    assert "sk-secret-123" not in response.text
