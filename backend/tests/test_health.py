from fastapi.testclient import TestClient

from app.main import app
from app.api import health

client = TestClient(app)


def test_liveness_returns_alive():
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_readiness_returns_ready_when_database_works():
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_readiness_returns_503_when_database_fails(monkeypatch):
    def fail_connection():
        raise RuntimeError("simulated database failure")

    monkeypatch.setattr(health.engine, "connect", fail_connection)

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}
