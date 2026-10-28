def test_register(client, unique_email):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": unique_email,
            "password": "TestPassword123",
            "timezone": "Asia/Kolkata",
        },
    )

    assert response.status_code == 201


def test_duplicate_register(client, unique_email):
    payload = {
        "email": unique_email,
        "password": "TestPassword123",
        "timezone": "Asia/Kolkata",
    }

    first_response = client.post(
        "/api/v1/auth/register",
        json=payload,
    )

    second_response = client.post(
        "/api/v1/auth/register",
        json=payload,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_login(client, unique_email):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": unique_email,
            "password": "TestPassword123",
            "timezone": "Asia/Kolkata",
        },
    )

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": unique_email,
            "password": "TestPassword123",
        },
    )

    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


def test_login_wrong_password(client, unique_email):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": unique_email,
            "password": "TestPassword123",
            "timezone": "Asia/Kolkata",
        },
    )

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": unique_email,
            "password": "WrongPassword123",
        },
    )

    assert response.status_code == 401


def test_me_without_token(client):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_me_with_valid_token(client, unique_email):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": unique_email,
            "password": "TestPassword123",
            "timezone": "Asia/Kolkata",
        },
    )

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": unique_email,
            "password": "TestPassword123",
        },
    )

    token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == unique_email


def test_me_with_invalid_token(client):
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401



def test_local_jwt_requires_subject_and_expiry():
    import jwt
    import pytest

    from app.core import jwt as jwt_module
    from app.core.config import settings

    missing_subject = jwt.encode(
        {"exp": 4102444800},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    missing_expiry = jwt.encode(
        {"sub": "123"},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(jwt.MissingRequiredClaimError):
        jwt_module.decode_access_token(missing_subject)

    with pytest.raises(jwt.MissingRequiredClaimError):
        jwt_module.decode_access_token(missing_expiry)


def test_local_jwt_rejects_non_string_subject():
    import jwt
    import pytest

    from app.core import jwt as jwt_module
    from app.core.config import settings

    token = jwt.encode(
        {"sub": 123, "exp": 4102444800},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(jwt.exceptions.InvalidSubjectError):
        jwt_module.decode_access_token(token)
