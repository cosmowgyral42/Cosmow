from functools import lru_cache
from urllib.parse import urlparse

import httpx
import jwt
from jwt import PyJWKClient

from app.core.config import settings


@lru_cache(maxsize=1)
def _get_jwks_client() -> PyJWKClient:
    parsed = urlparse(settings.supabase_url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "cuozhqperbnvdwojurqp.supabase.co"
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Invalid Supabase project URL")

    return PyJWKClient(
        f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json",
        cache_keys=True,
        timeout=settings.supabase_jwks_timeout_seconds,
    )


def decode_supabase_access_token(token: str) -> dict:
    signing_key = _get_jwks_client().get_signing_key_from_jwt(token).key

    payload = jwt.decode(
        token,
        signing_key,
        algorithms=["ES256"],
        audience="authenticated",
        issuer=f"{settings.supabase_url.rstrip('/')}/auth/v1",
        options={"require": ["exp", "iat", "sub", "iss", "aud"]},
    )

    if not isinstance(payload.get("sub"), str):
        raise ValueError("Invalid Supabase user subject")

    return payload
