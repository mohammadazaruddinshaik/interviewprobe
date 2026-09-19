import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.db.session import engine


def test_database_connection():
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            assert result.scalar() == 1
    except OperationalError as exc:
        pytest.skip(f"PostgreSQL is not reachable at the configured DATABASE_URL: {exc}")
