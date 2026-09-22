"""Task 50 — GET /ready: PostgreSQL + Redis readiness, distinct from the
existing liveness-only GET /health (tests/test_health.py — that file is
untouched and still passes; a quick confirmation of the same behavior is
repeated here only to prove this task didn't disturb it).

Reuses the exact get_db/get_redis_client override pattern already
established in tests/test_interview_api.py: a real in-memory SQLite
session (via the actual SQLAlchemy Session class the app uses everywhere
else) for the "database reachable" case, and the shared
FakeAsyncRedis/FailingAsyncRedis from tests/fakes.py for Redis. No real
Postgres/Redis server is required for any test in this file."""

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.session import get_db
from app.main import app
from app.redis.client import get_redis_client
from tests.fakes import FailingAsyncRedis, FakeAsyncRedis


class BrokenDbSession:
    """A minimal stand-in whose `.execute()` always fails — simulates
    PostgreSQL being unreachable without needing an actually-broken
    connection. `close()` is a no-op, same shape as a real Session's."""

    def execute(self, *args, **kwargs):
        raise SQLAlchemyError("simulated database outage")

    def close(self) -> None:
        pass


class HangingDbSession:
    """`.execute()` blocks (real thread-level sleep, since the readiness
    check runs it via asyncio.to_thread) well past the 0.1s timeout these
    tests configure — proves a hung dependency can't hang the endpoint.
    Deliberately a short 1s, not a large arbitrary duration: long enough
    to be unambiguously past the timeout, short enough that the orphaned
    background thread (see check_database's own docstring on this known
    limitation) can't meaningfully slow down or hang the test run."""

    def execute(self, *args, **kwargs):
        import time

        time.sleep(1)

    def close(self) -> None:
        pass


class HangingRedis:
    """`.ping()` sleeps past the configured timeout — the async
    equivalent of HangingDbSession above. Unlike the DB case, this
    coroutine's cancellation is genuinely clean (no orphaned thread) once
    asyncio.wait_for times out."""

    async def ping(self) -> bool:
        await asyncio.sleep(1)
        return True

    async def aclose(self) -> None:
        pass


@pytest.fixture()
def sqlite_session_factory():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    yield session_local
    engine.dispose()


def _use_db(override):
    app.dependency_overrides[get_db] = override


def _use_redis(override):
    app.dependency_overrides[get_redis_client] = override


def _healthy_db(session_local):
    def override():
        db = session_local()
        try:
            yield db
        finally:
            db.close()

    return override


def _broken_db():
    def override():
        yield BrokenDbSession()

    return override


def _hanging_db():
    def override():
        yield HangingDbSession()

    return override


def _healthy_redis(fake_redis):
    async def override():
        return fake_redis

    return override


def _broken_redis():
    async def override():
        return FailingAsyncRedis()

    return override


def _hanging_redis():
    async def override():
        return HangingRedis()

    return override


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


# ---------------------------------------------------------------------------
# /health is unaffected
# ---------------------------------------------------------------------------


def test_health_is_still_a_lightweight_liveness_endpoint(client: TestClient):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# /ready — success and failure combinations
# ---------------------------------------------------------------------------


def test_ready_returns_200_when_database_and_redis_are_both_reachable(client: TestClient, sqlite_session_factory):
    fake_redis = FakeAsyncRedis()
    _use_db(_healthy_db(sqlite_session_factory))
    _use_redis(_healthy_redis(fake_redis))

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "checks": {"database": "ok", "redis": "ok"}}


def test_ready_returns_503_when_database_is_unavailable(client: TestClient):
    _use_db(_broken_db())
    _use_redis(_healthy_redis(FakeAsyncRedis()))

    response = client.get("/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["checks"]["database"] == "unavailable"
    assert body["checks"]["redis"] == "ok"


def test_ready_returns_503_when_redis_is_unavailable(client: TestClient, sqlite_session_factory):
    _use_db(_healthy_db(sqlite_session_factory))
    _use_redis(_broken_redis())

    response = client.get("/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["checks"]["database"] == "ok"
    assert body["checks"]["redis"] == "unavailable"


def test_ready_returns_503_when_both_are_unavailable(client: TestClient):
    _use_db(_broken_db())
    _use_redis(_broken_redis())

    response = client.get("/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["checks"] == {"database": "unavailable", "redis": "unavailable"}


# ---------------------------------------------------------------------------
# No internal details leaked
# ---------------------------------------------------------------------------


def test_ready_response_never_leaks_connection_details(client: TestClient):
    _use_db(_broken_db())
    _use_redis(_broken_redis())

    response = client.get("/ready")

    text = response.text.lower()
    assert "postgresql" not in text
    assert "psycopg" not in text
    assert "sqlite" not in text
    assert "outage" not in text  # the simulated exceptions' own message text
    assert "redis://" not in text
    assert "password" not in text
    assert settings.database_url.lower() not in text
    assert settings.redis_url.lower() not in text


# ---------------------------------------------------------------------------
# No application state is mutated
# ---------------------------------------------------------------------------


def test_ready_does_not_write_any_redis_key(client: TestClient, sqlite_session_factory):
    fake_redis = FakeAsyncRedis()
    _use_db(_healthy_db(sqlite_session_factory))
    _use_redis(_healthy_redis(fake_redis))

    client.get("/ready")

    assert fake_redis.store == {}


def test_ready_does_not_create_a_lock_ratelimit_or_idempotency_key(client: TestClient, sqlite_session_factory):
    # A more targeted restatement of the assertion above: PING is the only
    # Redis operation check_redis ever calls — confirmed by construction
    # (FakeAsyncRedis.ping() takes no key argument at all and never
    # touches .store), but re-asserted here explicitly per the task's own
    # "must not mutate application state" requirement.
    fake_redis = FakeAsyncRedis()
    _use_db(_healthy_db(sqlite_session_factory))
    _use_redis(_healthy_redis(fake_redis))

    response = client.get("/ready")

    assert response.status_code == 200
    assert fake_redis.store == {}
    assert fake_redis.ttls == {}


# ---------------------------------------------------------------------------
# Bounded / cannot hang
# ---------------------------------------------------------------------------


def test_a_hung_database_check_does_not_hang_the_endpoint(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "readiness_timeout_seconds", 0.1)
    _use_db(_hanging_db())
    _use_redis(_healthy_redis(FakeAsyncRedis()))

    import time

    started = time.monotonic()
    response = client.get("/ready")
    elapsed = time.monotonic() - started

    assert response.status_code == 503
    assert response.json()["checks"]["database"] == "unavailable"
    assert elapsed < 2.0  # bounded by the 0.1s timeout, not the 5s hang


def test_a_hung_redis_check_does_not_hang_the_endpoint(client: TestClient, monkeypatch, sqlite_session_factory):
    monkeypatch.setattr(settings, "readiness_timeout_seconds", 0.1)
    _use_db(_healthy_db(sqlite_session_factory))
    _use_redis(_hanging_redis())

    import time

    started = time.monotonic()
    response = client.get("/ready")
    elapsed = time.monotonic() - started

    assert response.status_code == 503
    assert response.json()["checks"]["redis"] == "unavailable"
    assert elapsed < 2.0


# ---------------------------------------------------------------------------
# Uses the existing DB/Redis infrastructure (not a second connection path)
# ---------------------------------------------------------------------------


def test_database_check_runs_a_real_query_through_the_existing_session(client: TestClient, sqlite_session_factory):
    # A genuine SQLAlchemy Session (the exact class app.db.session.get_db
    # yields in production) executing a real SELECT 1 — not a mock of
    # check_database itself. Proves the check goes through real
    # SQLAlchemy execution, not just returns a hardcoded True.
    _use_db(_healthy_db(sqlite_session_factory))
    _use_redis(_healthy_redis(FakeAsyncRedis()))

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json()["checks"]["database"] == "ok"


def test_redis_check_uses_the_same_client_shape_as_get_redis_client(client: TestClient, sqlite_session_factory):
    # FakeAsyncRedis is the same fake the rest of the suite uses for
    # get_redis_client overrides (locks/rate-limit/idempotency tests) —
    # using it here (rather than a bespoke double) is what "uses the
    # existing Redis infrastructure" means for a test double.
    _use_db(_healthy_db(sqlite_session_factory))
    _use_redis(_healthy_redis(FakeAsyncRedis()))

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json()["checks"]["redis"] == "ok"
