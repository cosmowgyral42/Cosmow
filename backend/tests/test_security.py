from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_missing_authentication_returns_403():
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_invalid_bearer_token_returns_401():
    response = client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": "Bearer definitely-invalid-token",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


def test_invalid_login_returns_401(unique_email):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": unique_email,
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"
