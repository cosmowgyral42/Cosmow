import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def unique_email():
    return f"test_{uuid.uuid4().hex}@example.com"
