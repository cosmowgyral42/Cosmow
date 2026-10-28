from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_api_response_includes_security_headers_and_request_id():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.headers["X-Request-ID"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["Permissions-Policy"] == (
        "camera=(), microphone=(), geolocation=()"
    )
