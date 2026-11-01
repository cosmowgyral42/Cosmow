from unittest.mock import patch
from uuid import uuid4

from app.ai.schemas import AIResponse
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import text
from app.api.dependencies import get_db
from app.core.database import SessionLocal


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


def test_stream_keeps_database_session_alive_until_response_finishes():
    token = register_and_login()
    session_states = {}

    def override_get_db():
        db = SessionLocal()
        state = {"closed": False}
        original_close = db.close

        def tracked_close():
            state["closed"] = True
            original_close()

        db.close = tracked_close
        session_states[id(db)] = state

        try:
            yield db
        finally:
            db.close()

    def fake_stream(db, user, request):
        state = session_states[id(db)]

        def chunks():
            assert state["closed"] is False
            assert db.execute(text("SELECT 1")).scalar_one() == 1
            yield "first "

            assert state["closed"] is False
            assert db.execute(text("SELECT 1")).scalar_one() == 1
            yield "second"

        return chunks()

    app.dependency_overrides[get_db] = override_get_db

    try:
        with patch("app.api.ai.ai_service.stream", side_effect=fake_stream):
            response = client.post(
                "/api/v1/ai/stream",
                headers={"Authorization": f"Bearer {token}"},
                json={"prompt": "Test streaming lifecycle"},
            )

        assert response.status_code == 200
        assert response.text == "first second"
        assert session_states
        assert all(state["closed"] for state in session_states.values())
    finally:
        app.dependency_overrides.pop(get_db, None)

def test_stream_http_response_finalizes_quota():
    token = register_and_login()
    from app.services import ai_service as service_module
    from app.api.ai import ai_service

    cleanup = {"finalized": 0, "released": 0}

    def provider_stream(request):
        yield "first"
        yield "second"

    def fake_finalize(db, user, reservation):
        cleanup["finalized"] += 1
        return True

    def fake_release(db, user, reservation):
        cleanup["released"] += 1
        return True

    with patch.object(
        service_module, "reserve_ai_call", return_value=object()
    ), patch.object(
        service_module, "finalize_ai_call", side_effect=fake_finalize
    ), patch.object(
        service_module, "release_ai_call", side_effect=fake_release
    ), patch.object(
        ai_service.provider, "stream", side_effect=provider_stream
    ):
        with client.stream(
            "POST",
            "/api/v1/ai/stream",
            headers={"Authorization": f"Bearer {token}"},
            json={"prompt": "Streaming lifecycle test"},
        ) as response:
            assert response.status_code == 200
            body = "".join(response.iter_text())

    assert body == "firstsecond"
    assert cleanup == {"finalized": 1, "released": 0}
