from app.core.rate_limit import check_rate_limit, reset_rate_limits


def test_login_rate_limit_blocks_request_after_limit():
    reset_rate_limits()
    key = "test-client-login"

    for _ in range(10):
        assert check_rate_limit(key, "/api/v1/auth/login") is None

    retry_after = check_rate_limit(key, "/api/v1/auth/login")
    assert retry_after is not None
    assert retry_after >= 1

    reset_rate_limits()


def test_rate_limits_are_separate_by_client():
    reset_rate_limits()

    for _ in range(10):
        check_rate_limit("client-a", "/api/v1/auth/login")

    assert check_rate_limit("client-a", "/api/v1/auth/login") is not None
    assert check_rate_limit("client-b", "/api/v1/auth/login") is None

    reset_rate_limits()


def test_unconfigured_path_is_not_rate_limited():
    reset_rate_limits()

    assert check_rate_limit("test-client", "/api/v1/auth/me") is None

    reset_rate_limits()

def test_middleware_returns_429_after_login_limit(client):
    reset_rate_limits()

    try:
        for _ in range(10):
            response = client.post("/api/v1/auth/login", json={})
            assert response.status_code != 429

        response = client.post("/api/v1/auth/login", json={})

        assert response.status_code == 429
        assert response.json()["detail"] == (
            "Too many requests. Please try again shortly."
        )
        assert int(response.headers["Retry-After"]) >= 1
        assert response.headers["X-Request-ID"]
        assert response.headers["X-Content-Type-Options"] == "nosniff"
    finally:
        reset_rate_limits()
