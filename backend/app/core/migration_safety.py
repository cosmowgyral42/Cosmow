from sqlalchemy.engine import make_url


def validate_local_migration_target(database_url: str) -> None:
    """Allow migrations only against the explicitly designated local test DB."""
    url = make_url(database_url)

    if (
        url.drivername != "postgresql+psycopg"
        or url.host not in ("localhost", "127.0.0.1", "::1")
        or url.database != "cosmow_test"
    ):
        raise RuntimeError(
            "Unsafe migration target. Migrations are restricted to "
            "the local cosmow_test database."
        )
