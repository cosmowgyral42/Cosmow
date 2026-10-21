import os
import uuid

from sqlalchemy.engine import make_url

test_url = os.environ.get("TEST_DATABASE_URL")
if not test_url:
    raise RuntimeError("TEST_DATABASE_URL is required. Tests were stopped.")

url = make_url(test_url)
if (
    url.host not in ("localhost", "127.0.0.1", "::1")
    or url.database != "cosmow_test"
    or url.drivername != "postgresql+psycopg"
):
    raise RuntimeError("Unsafe test database target. Tests were stopped.")

os.environ["DATABASE_URL"] = test_url

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def unique_email():
    return f"test_{uuid.uuid4().hex}@example.com"
