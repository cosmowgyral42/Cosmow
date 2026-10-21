from unittest.mock import patch
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient

from app.core import supabase_jwt
from app.main import app


client = TestClient(app)


def make_supabase_token_with_test_key():
    # This token is intentionally signed with a key that Supabase does not own.
    # It must never be accepted unless verification is incorrectly bypassed.
    from cryptography.hazmat.primitives.asymmetric import ec

    private_key = ec.generate_private_key(ec.SECP256R1())
    now = 2_000_000_000

    return jwt.encode(
        {
            "sub": str(uuid4()),
            "iss": f"{supabase_jwt.settings.supabase_url.rstrip('/')}/auth/v1",
            "aud": "authenticated",
            "iat": now,
            "exp": now + 300,
            "email": f"{uuid4().hex}@example.com",
        },
        private_key,
        algorithm="ES256",
        headers={"kid": "untrusted-test-key"},
    )


def test_invalid_supabase_signature_is_rejected():
    token = make_supabase_token_with_test_key()

    with patch.object(
        supabase_jwt,
        "_get_jwks_client",
        side_effect=RuntimeError("simulated JWKS outage"),
    ):
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Authentication service temporarily unavailable"
    )


def test_document_upload_requires_authentication():
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("notes.txt", b"test", "text/plain")},
    )

    assert response.status_code == 401


def test_ai_generation_requires_authentication():
    response = client.post(
        "/api/v1/ai/generate",
        json={"prompt": "This must not reach an AI provider"},
    )

    assert response.status_code == 401


def test_rag_ask_requires_authentication():
    response = client.post(
        "/api/v1/rag/ask",
        json={"question": "This must not reach an AI provider"},
    )

    assert response.status_code == 401

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric import ec
import jwt

from app.core import supabase_jwt


def _make_test_supabase_token(private_key, email):
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(uuid4()),
            "iss": f"{supabase_jwt.settings.supabase_url.rstrip('/')}/auth/v1",
            "aud": "authenticated",
            "iat": now,
            "exp": now + timedelta(minutes=5),
            "email": email,
        },
        private_key,
        algorithm="ES256",
        headers={"kid": "test-key"},
    )


def test_valid_supabase_token_authenticates_and_provisions_user(monkeypatch):
    private_key = ec.generate_private_key(ec.SECP256R1())
    email = f"{uuid4().hex}@example.com"
    token = _make_test_supabase_token(private_key, email)

    class FakeJwksClient:
        def get_signing_key_from_jwt(self, token):
            return SimpleNamespace(key=private_key.public_key())

    monkeypatch.setattr(
        supabase_jwt,
        "_get_jwks_client",
        lambda: FakeJwksClient(),
    )

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == email


def test_supabase_token_with_wrong_signature_returns_401(monkeypatch):
    trusted_key = ec.generate_private_key(ec.SECP256R1())
    attacker_key = ec.generate_private_key(ec.SECP256R1())
    token = _make_test_supabase_token(
        attacker_key,
        f"{uuid4().hex}@example.com",
    )

    class FakeJwksClient:
        def get_signing_key_from_jwt(self, token):
            return SimpleNamespace(key=trusted_key.public_key())

    monkeypatch.setattr(
        supabase_jwt,
        "_get_jwks_client",
        lambda: FakeJwksClient(),
    )

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
