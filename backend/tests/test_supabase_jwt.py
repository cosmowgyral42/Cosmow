from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from app.core import supabase_jwt


@pytest.fixture
def signing_keys():
    private_key = ec.generate_private_key(ec.SECP256R1())
    return private_key, private_key.public_key()


@pytest.fixture
def mock_jwks(monkeypatch, signing_keys):
    _, public_key = signing_keys

    class FakeJwksClient:
        def get_signing_key_from_jwt(self, token):
            return SimpleNamespace(key=public_key)

    monkeypatch.setattr(
        supabase_jwt,
        "_get_jwks_client",
        lambda: FakeJwksClient(),
    )


def make_token(private_key, **overrides):
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(uuid4()),
        "iss": f"{supabase_jwt.settings.supabase_url.rstrip('/')}/auth/v1",
        "aud": "authenticated",
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    claims.update(overrides)
    return jwt.encode(
        claims,
        private_key,
        algorithm="ES256",
        headers={"kid": "test-key"},
    )


def test_accepts_valid_supabase_token(signing_keys, mock_jwks):
    private_key, _ = signing_keys
    token = make_token(private_key)

    payload = supabase_jwt.decode_supabase_access_token(token)

    assert payload["aud"] == "authenticated"
    assert payload["sub"]


def test_rejects_expired_token(signing_keys, mock_jwks):
    private_key, _ = signing_keys
    token = make_token(
        private_key,
        exp=datetime.now(timezone.utc) - timedelta(minutes=1),
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        supabase_jwt.decode_supabase_access_token(token)


def test_rejects_wrong_issuer(signing_keys, mock_jwks):
    private_key, _ = signing_keys
    token = make_token(private_key, iss="https://wrong.example/auth/v1")

    with pytest.raises(jwt.InvalidIssuerError):
        supabase_jwt.decode_supabase_access_token(token)


def test_rejects_wrong_audience(signing_keys, mock_jwks):
    private_key, _ = signing_keys
    token = make_token(private_key, aud="other-service")

    with pytest.raises(jwt.InvalidAudienceError):
        supabase_jwt.decode_supabase_access_token(token)


def test_rejects_wrong_signature(signing_keys, mock_jwks):
    _, public_key = signing_keys
    other_private_key = ec.generate_private_key(ec.SECP256R1())
    token = make_token(other_private_key)

    class FakeJwksClient:
        def get_signing_key_from_jwt(self, token):
            return SimpleNamespace(key=public_key)

    with pytest.raises(jwt.InvalidSignatureError):
        supabase_jwt.decode_supabase_access_token(token)


def test_rejects_hs256_token(signing_keys, mock_jwks):
    private_key, _ = signing_keys
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "iss": f"{supabase_jwt.settings.supabase_url.rstrip('/')}/auth/v1",
            "aud": "authenticated",
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        "not-a-supabase-secret-that-is-at-least-32-bytes",
        algorithm="HS256",
        headers={"kid": "test-key"},
    )

    with pytest.raises(jwt.InvalidAlgorithmError):
        supabase_jwt.decode_supabase_access_token(token)
