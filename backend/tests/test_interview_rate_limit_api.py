"""Task 46 — per-client (IP-based) rate limiting on `POST /api/v1/interviews`
and `POST /api/v1/interviews/{session_id}/start`, the two endpoints that can
trigger expensive work (an LLM call, on `/start`) with no existing session
to scope a limit by and no authentication to identify a caller by. Mirrors
the existing answer-rate-limit tests in test_interview_api.py (same 429
contract, same Redis-outage contract) but keyed by client IP via
`TestClient(app, client=(...))` instead of by session_id."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_knowledge_retrieval_service, get_llm_provider
from app.db.base import Base
from app.db.session import get_db
from app.domain.enums import Difficulty, InterviewTopic, QuestionType
from app.main import app
from app.models.interview_session import InterviewSession
from app.redis.client import get_redis_client
from app.workflows.interview.models import AnswerAnalysis, GeneratedQuestion, NextAction
from tests.fakes import FailingAsyncRedis, FakeAsyncRedis, FakeLLMProvider


@compiles(UUID, "sqlite")
def _compile_uuid_sqlite(element, compiler, **kw):
    return "CHAR(32)"


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(element, compiler, **kw):
    return "JSON"


VALID_CREATE_PAYLOAD = {
    "role": "AI_ENGINEER",
    "difficulty": "MEDIUM",
    "topics": ["RAG", "AI_AGENTS"],
    "question_limit": 5,
}


def _fake_llm() -> FakeLLMProvider:
    return FakeLLMProvider(
        structured_responses={
            "GeneratedQuestion": GeneratedQuestion(
                question="Can you go deeper on that?",
                topic=InterviewTopic.RAG,
                difficulty=Difficulty.MEDIUM,
                question_type=QuestionType.FOLLOW_UP,
            ),
            "AnswerAnalysis": AnswerAnalysis(
                understanding="BASIC",
                correctness=0.6,
                depth=0.5,
                concepts_demonstrated=[],
                concepts_missing=[],
                reasoning_quality="MODERATE",
                needs_follow_up=True,
            ),
            "NextAction": NextAction(
                action="FOLLOW_UP",
                topic=InterviewTopic.RAG,
                difficulty=Difficulty.MEDIUM,
                rationale="Probe further.",
            ),
        }
    )


@pytest.fixture()
def fake_redis() -> FakeAsyncRedis:
    return FakeAsyncRedis()


@pytest.fixture()
def fake_llm() -> FakeLLMProvider:
    return _fake_llm()


@pytest.fixture()
def db_engine():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def app_overrides(db_engine, fake_redis: FakeAsyncRedis, fake_llm: FakeLLMProvider):
    """Wires the app's dependency_overrides once; both `client` and
    `other_client` below (different reported IPs, same app) share these —
    exactly what the "separate client identities" isolation tests need:
    the same fake Redis/DB/LLM behind two different caller identities."""
    testing_session_local = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    async def override_get_redis_client():
        return fake_redis

    def override_get_llm_provider():
        return fake_llm

    def override_get_knowledge_retrieval_service():
        return None

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis_client] = override_get_redis_client
    app.dependency_overrides[get_llm_provider] = override_get_llm_provider
    app.dependency_overrides[get_knowledge_retrieval_service] = override_get_knowledge_retrieval_service
    yield testing_session_local
    app.dependency_overrides.clear()


@pytest.fixture()
def client(app_overrides):
    with TestClient(app, client=("10.0.0.1", 12345)) as test_client:
        yield test_client


@pytest.fixture()
def other_client(app_overrides):
    """A second TestClient reporting a different IP against the exact same
    app/Redis/DB/LLM — the only thing that differs from `client` is the
    caller identity the rate limiter sees."""
    with TestClient(app, client=("10.0.0.2", 12345)) as test_client:
        yield test_client


def session_count(session_local) -> int:
    db = session_local()
    try:
        return db.query(InterviewSession).count()
    finally:
        db.close()


def create_interview(test_client: TestClient) -> dict:
    response = test_client.post("/api/v1/interviews", json=VALID_CREATE_PAYLOAD)
    assert response.status_code == 201
    return response.json()["data"]


# ---------------------------------------------------------------------------
# POST /api/v1/interviews — creation rate limit (10/60/client)
# ---------------------------------------------------------------------------


def test_first_ten_interview_creations_succeed(client: TestClient):
    for _ in range(10):
        response = client.post("/api/v1/interviews", json=VALID_CREATE_PAYLOAD)
        assert response.status_code == 201


def test_eleventh_interview_creation_is_rate_limited(client: TestClient):
    for _ in range(10):
        client.post("/api/v1/interviews", json=VALID_CREATE_PAYLOAD)

    response = client.post("/api/v1/interviews", json=VALID_CREATE_PAYLOAD)

    assert response.status_code == 429
    body = response.json()
    assert body["error"]["code"] == "RATE_LIMITED"
    assert "Retry-After" in response.headers
    assert int(response.headers["Retry-After"]) > 0


def test_rejected_interview_creation_does_not_create_a_session(client: TestClient, app_overrides):
    for _ in range(10):
        client.post("/api/v1/interviews", json=VALID_CREATE_PAYLOAD)
    count_before_rejection = session_count(app_overrides)

    response = client.post("/api/v1/interviews", json=VALID_CREATE_PAYLOAD)

    assert response.status_code == 429
    assert session_count(app_overrides) == count_before_rejection == 10


def test_interview_creation_buckets_are_isolated_per_client(client: TestClient, other_client: TestClient):
    for _ in range(10):
        response = client.post("/api/v1/interviews", json=VALID_CREATE_PAYLOAD)
        assert response.status_code == 201
    exhausted = client.post("/api/v1/interviews", json=VALID_CREATE_PAYLOAD)
    assert exhausted.status_code == 429

    # A different client identity has its own, untouched bucket.
    response = other_client.post("/api/v1/interviews", json=VALID_CREATE_PAYLOAD)
    assert response.status_code == 201


def test_interview_creation_redis_outage_returns_503_and_never_creates_a_session(app_overrides):
    app.dependency_overrides[get_redis_client] = lambda: FailingAsyncRedis()
    with TestClient(app, client=("10.0.0.3", 1)) as test_client:
        response = test_client.post("/api/v1/interviews", json=VALID_CREATE_PAYLOAD)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "REDIS_UNAVAILABLE"
    assert session_count(app_overrides) == 0


# ---------------------------------------------------------------------------
# POST /api/v1/interviews/{session_id}/start — start rate limit (5/60/client)
# ---------------------------------------------------------------------------


def test_first_five_interview_starts_succeed(client: TestClient):
    for _ in range(5):
        created = create_interview(client)
        response = client.post(f"/api/v1/interviews/{created['id']}/start")
        assert response.status_code == 200


def test_sixth_interview_start_is_rate_limited(client: TestClient):
    for _ in range(5):
        created = create_interview(client)
        client.post(f"/api/v1/interviews/{created['id']}/start")
    sixth_session = create_interview(client)

    response = client.post(f"/api/v1/interviews/{sixth_session['id']}/start")

    assert response.status_code == 429
    body = response.json()
    assert body["error"]["code"] == "RATE_LIMITED"
    assert "Retry-After" in response.headers
    assert int(response.headers["Retry-After"]) > 0


def test_rejected_interview_start_never_invokes_the_llm(client: TestClient, fake_llm: FakeLLMProvider):
    for _ in range(5):
        created = create_interview(client)
        client.post(f"/api/v1/interviews/{created['id']}/start")
    calls_before_rejection = len(fake_llm.calls)
    sixth_session = create_interview(client)

    response = client.post(f"/api/v1/interviews/{sixth_session['id']}/start")

    assert response.status_code == 429
    assert len(fake_llm.calls) == calls_before_rejection  # workflow/LLM never reached


def test_rejected_interview_start_does_not_mutate_session_state(client: TestClient):
    for _ in range(5):
        created = create_interview(client)
        client.post(f"/api/v1/interviews/{created['id']}/start")
    sixth_session = create_interview(client)

    rejected = client.post(f"/api/v1/interviews/{sixth_session['id']}/start")
    assert rejected.status_code == 429

    # The session must still be exactly as `create_interview` left it — CREATED, untouched.
    state = client.get(f"/api/v1/interviews/{sixth_session['id']}")
    assert state.json()["data"]["status"] == "CREATED"


def test_existing_already_started_state_validation_still_applies_within_the_limit(client: TestClient):
    created = create_interview(client)
    first = client.post(f"/api/v1/interviews/{created['id']}/start")
    assert first.status_code == 200

    second = client.post(f"/api/v1/interviews/{created['id']}/start")

    assert second.status_code == 409
    assert second.json()["error"]["code"] == "INVALID_INTERVIEW_STATE"


def test_interview_start_buckets_are_isolated_per_client(client: TestClient, other_client: TestClient):
    for _ in range(5):
        created = create_interview(client)
        response = client.post(f"/api/v1/interviews/{created['id']}/start")
        assert response.status_code == 200
    sixth_session = create_interview(client)
    exhausted = client.post(f"/api/v1/interviews/{sixth_session['id']}/start")
    assert exhausted.status_code == 429

    # A different client identity — separate session, separate bucket.
    other_session = create_interview(other_client)
    response = other_client.post(f"/api/v1/interviews/{other_session['id']}/start")
    assert response.status_code == 200


def test_interview_start_redis_outage_returns_503_and_never_invokes_the_llm(app_overrides, fake_llm: FakeLLMProvider):
    with TestClient(app, client=("10.0.0.4", 1)) as test_client:
        created = create_interview(test_client)
        app.dependency_overrides[get_redis_client] = lambda: FailingAsyncRedis()

        response = test_client.post(f"/api/v1/interviews/{created['id']}/start")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "REDIS_UNAVAILABLE"
    assert fake_llm.calls == []


# ---------------------------------------------------------------------------
# Cross-endpoint isolation — creation and start never share a bucket
# ---------------------------------------------------------------------------


def test_creation_and_start_do_not_share_a_bucket(client: TestClient):
    # Exhaust the (tighter) start limit first via 5 create+start pairs —
    # that's only 5 creations, well under the creation limit of 10 — then
    # confirm creation still has budget left even though start is now
    # exhausted for this same client.
    for _ in range(5):
        created = create_interview(client)
        client.post(f"/api/v1/interviews/{created['id']}/start")
    sixth = create_interview(client)
    assert client.post(f"/api/v1/interviews/{sixth['id']}/start").status_code == 429

    response = client.post("/api/v1/interviews", json=VALID_CREATE_PAYLOAD)
    assert response.status_code == 201
