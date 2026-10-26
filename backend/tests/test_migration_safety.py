import pytest

from app.core.migration_safety import validate_local_migration_target


@pytest.mark.parametrize(
    "host",
    ["localhost", "127.0.0.1", "::1"],
)
def test_allows_local_test_database(host):
    url_host = f"[{host}]" if ":" in host else host
    url = f"postgresql+psycopg://user:password@{url_host}:5432/cosmow_test"
    validate_local_migration_target(url)


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg://user:password@aws-0.example.com:5432/postgres",
        "postgresql+psycopg://user:password@localhost:5432/postgres",
        "postgresql://user:password@localhost:5432/cosmow_test",
    ],
)
def test_rejects_unsafe_migration_targets(url):
    with pytest.raises(RuntimeError, match="Unsafe migration target"):
        validate_local_migration_target(url)
