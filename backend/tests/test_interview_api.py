import asyncio
import concurrent.futures
import uuid

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
from app.evaluation.models import EvaluationResult, EvidenceItem
from app.main import app
from app.redis.client import get_redis_client
from app.workflows.interview.models import AnswerAnalysis, GeneratedQuestion, NextAction
from tests.fakes import FailingAsyncRedis, FakeAsyncRedis, FakeLLMProvider

# Same sqlite-compatibility strategy as tests/test_interview_repository.py
# and tests/test_interview_service.py (Tasks 7-8): teach only the sqlite
# dialect how to render the PostgreSQL-only UUID/JSONB types used by the
# production models, without touching the models themselves.


@compiles(UUID, "sqlite")
def _compile_uuid_sqlite(element, compiler, **kw):
    return "CHAR(32)"


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(element, compiler, **kw):
    return "JSON"


@pytest.fixture()
def fake_redis() -> FakeAsyncRedis:
    return FakeAsyncRedis()


def default_fake_llm_provider() -> FakeLLMProvider:
    """Shared default for every API test that doesn't care about the
    adaptive decision itself: always proposes FOLLOW_UP on whatever the
    current topic is. The service never trusts `GeneratedQuestion.topic`/
    `.difficulty` for persistence (see `InterviewService`), so the exact
    topic/difficulty configured here doesn't need to track each test's
    session — only `.question`/analysis fields are actually used."""
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
                rationale="Probe the candidate's understanding further.",
            ),
            "EvaluationResult": EvaluationResult(
                technical_knowledge_score=7.5,
                reasoning_score=6.0,
                depth_score=5.5,
                communication_score=8.0,
                overall_score=1.0,  # deliberately wrong — backend must never trust this
                strengths=["Explained retrieval clearly."],
                weaknesses=["Limited depth on reranking."],
                evidence=[
                    EvidenceItem(
                        question_id=None,
                        topic=InterviewTopic.RAG,
                        claim="Understood the basics of retrieval.",
                        evidence="Described fetching relevant context before generation.",
                    )
                ],
            ),
        }
    )


@pytest.fixture()
def fake_llm() -> FakeLLMProvider:
    return default_fake_llm_provider()


@pytest.fixture()
def client(fake_redis: FakeAsyncRedis, fake_llm: FakeLLMProvider):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)

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
        # None: no knowledge layer configured. This must be overridden
        # explicitly rather than left to `get_knowledge_retrieval_service`'s
        # real fallback — a real `LLM_API_KEY` may be configured in this
        # environment's `.env` (for the real LLM provider), and the
        # embedding factory would otherwise reuse it, risking a real
        # OpenAI/Qdrant network call from these tests. `None` keeps
        # question generation ungrounded but fully functional (Task 20).
        return None

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis_client] = override_get_redis_client
    app.dependency_overrides[get_llm_provider] = override_get_llm_provider
    app.dependency_overrides[get_knowledge_retrieval_service] = override_get_knowledge_retrieval_service
    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    engine.dispose()


VALID_CREATE_PAYLOAD = {
    "role": "AI_ENGINEER",
    "difficulty": "MEDIUM",
    "topics": ["RAG", "AI_AGENTS"],
    "question_limit": 5,
}


def create_interview(client: TestClient, question_limit: int = 5) -> dict:
    payload = {**VALID_CREATE_PAYLOAD, "question_limit": question_limit}
    response = client.post("/api/v1/interviews", json=payload)
    assert response.status_code == 201
    return response.json()["data"]


def start_interview(client: TestClient, session_id: str) -> dict:
    response = client.post(f"/api/v1/interviews/{session_id}/start")
    assert response.status_code == 200
    return response.json()["data"]


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


def test_create_interview_valid_returns_201(client: TestClient):
    response = client.post("/api/v1/interviews", json=VALID_CREATE_PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    assert "data" in body
    data = body["data"]
    assert data["role"] == "AI_ENGINEER"
    assert data["difficulty"] == "MEDIUM"
    assert data["topics"] == ["RAG", "AI_AGENTS"]
    assert data["question_limit"] == 5
    assert data["status"] == "CREATED"
    uuid.UUID(data["id"])  # does not raise


def test_create_interview_invalid_role_returns_422(client: TestClient):
    payload = {**VALID_CREATE_PAYLOAD, "role": "NOT_A_ROLE"}
    response = client.post("/api/v1/interviews", json=payload)

    assert response.status_code == 422


def test_create_interview_invalid_difficulty_returns_422(client: TestClient):
    payload = {**VALID_CREATE_PAYLOAD, "difficulty": "IMPOSSIBLE"}
    response = client.post("/api/v1/interviews", json=payload)

    assert response.status_code == 422


def test_create_interview_invalid_topics_returns_422(client: TestClient):
    payload = {**VALID_CREATE_PAYLOAD, "topics": ["NOT_A_TOPIC"]}
    response = client.post("/api/v1/interviews", json=payload)

    assert response.status_code == 422


def test_create_interview_invalid_question_limit_returns_422(client: TestClient):
    payload = {**VALID_CREATE_PAYLOAD, "question_limit": 1}
    response = client.post("/api/v1/interviews", json=payload)

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Create — Task 17 role/topic domain validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "role,topics",
    [
        ("AI_ENGINEER", ["RAG", "AI_AGENTS"]),
        ("FRONTEND_DEVELOPER", ["JAVASCRIPT", "REACT"]),
        ("BACKEND_DEVELOPER", ["REST_APIS", "DATABASES"]),
        ("JAVA_DEVELOPER", ["CORE_JAVA", "COLLECTIONS"]),
    ],
)
def test_create_interview_accepts_role_appropriate_topics(
    client: TestClient, role: str, topics: list[str]
):
    payload = {**VALID_CREATE_PAYLOAD, "role": role, "topics": topics}
    response = client.post("/api/v1/interviews", json=payload)

    assert response.status_code == 201
    assert response.json()["data"]["topics"] == topics


@pytest.mark.parametrize(
    "role,topics",
    [
        ("BACKEND_DEVELOPER", ["REACT"]),
        ("FRONTEND_DEVELOPER", ["DATABASES"]),
        ("JAVA_DEVELOPER", ["RAG"]),
    ],
)
def test_create_interview_rejects_role_inappropriate_topics(
    client: TestClient, role: str, topics: list[str]
):
    payload = {**VALID_CREATE_PAYLOAD, "role": role, "topics": topics}
    response = client.post("/api/v1/interviews", json=payload)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "INVALID_ROLE_TOPIC"
    assert "message" in error


def test_create_interview_invalid_role_topic_does_not_persist_a_session(client: TestClient):
    payload = {**VALID_CREATE_PAYLOAD, "role": "BACKEND_DEVELOPER", "topics": ["REACT"]}
    response = client.post("/api/v1/interviews", json=payload)
    assert response.status_code == 422

    # No session id was ever returned, and there is no list endpoint to
    # probe with — instead confirm a request for a random id behaves
    # exactly like "never existed" (404, not some other state), which is
    # the observable behavior consistent with nothing having persisted.
    response_body = response.json()
    assert "data" not in response_body


def test_create_interview_topics_preserve_candidate_selected_order(client: TestClient):
    payload = {
        **VALID_CREATE_PAYLOAD,
        "role": "BACKEND_DEVELOPER",
        "topics": ["DATABASES", "REST_APIS", "CACHING"],
    }
    response = client.post("/api/v1/interviews", json=payload)

    assert response.status_code == 201
    assert response.json()["data"]["topics"] == ["DATABASES", "REST_APIS", "CACHING"]


# ---------------------------------------------------------------------------
# Start
# ---------------------------------------------------------------------------


def test_start_interview_valid_returns_200_with_question(client: TestClient):
    created = create_interview(client)

    data = start_interview(client, created["id"])

    assert data["session_id"] == created["id"]
    assert data["status"] == "IN_PROGRESS"
    question = data["question"]
    assert question["sequence"] == 1
    assert question["type"] == "INITIAL"
    # Task 17: topic comes from the first selected topic (VALID_CREATE_PAYLOAD
    # lists RAG first), not a hardcoded constant.
    assert question["topic"] == "RAG"
    assert question["difficulty"] == "MEDIUM"
    assert question["text"]


def test_start_interview_nonexistent_session_returns_404(client: TestClient):
    response = client.post(f"/api/v1/interviews/{uuid.uuid4()}/start")

    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "INTERVIEW_NOT_FOUND"
    assert "message" in error


def test_start_interview_already_started_returns_409(client: TestClient):
    created = create_interview(client)
    start_interview(client, created["id"])

    response = client.post(f"/api/v1/interviews/{created['id']}/start")

    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "INVALID_INTERVIEW_STATE"


# ---------------------------------------------------------------------------
# Answer
# ---------------------------------------------------------------------------


def test_submit_answer_valid_returns_200_with_next_question(client: TestClient):
    created = create_interview(client, question_limit=3)
    started = start_interview(client, created["id"])
    question_id = started["question"]["id"]

    response = client.post(
        f"/api/v1/interviews/{created['id']}/answers",
        json={"question_id": question_id, "answer": "RAG retrieves relevant context."},
        headers={"Idempotency-Key": "key-1"},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "IN_PROGRESS"
    assert data["action"] == "FOLLOW_UP"
    assert data["question"]["sequence"] == 2
    assert data["question"]["type"] == "FOLLOW_UP"


def test_submit_answer_persists_candidate_message(client: TestClient):
    created = create_interview(client, question_limit=3)
    started = start_interview(client, created["id"])
    question_id = started["question"]["id"]

    client.post(
        f"/api/v1/interviews/{created['id']}/answers",
        json={"question_id": question_id, "answer": "An answer."},
        headers={"Idempotency-Key": "key-2"},
    )

    get_response = client.get(f"/api/v1/interviews/{created['id']}")
    assert get_response.json()["data"]["questions_answered"] == 1


def test_submit_answer_missing_idempotency_key_returns_400(client: TestClient):
    created = create_interview(client, question_limit=3)
    started = start_interview(client, created["id"])
    question_id = started["question"]["id"]

    response = client.post(
        f"/api/v1/interviews/{created['id']}/answers",
        json={"question_id": question_id, "answer": "An answer."},
    )

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "MISSING_IDEMPOTENCY_KEY"


def test_submit_answer_invalid_question_id_returns_409(client: TestClient):
    created = create_interview(client, question_limit=3)
    start_interview(client, created["id"])

    response = client.post(
        f"/api/v1/interviews/{created['id']}/answers",
        json={"question_id": str(uuid.uuid4()), "answer": "An answer."},
        headers={"Idempotency-Key": "key-3"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_QUESTION"


def test_submit_answer_wrong_session_question_returns_409(client: TestClient):
    created_a = create_interview(client, question_limit=3)
    started_a = start_interview(client, created_a["id"])
    question_a_id = started_a["question"]["id"]

    created_b = create_interview(client, question_limit=3)
    start_interview(client, created_b["id"])

    response = client.post(
        f"/api/v1/interviews/{created_b['id']}/answers",
        json={"question_id": question_a_id, "answer": "An answer."},
        headers={"Idempotency-Key": "key-4"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_QUESTION"


def test_submit_answer_after_completion_returns_409(client: TestClient):
    created = create_interview(client, question_limit=3)
    started = start_interview(client, created["id"])
    question_id = started["question"]["id"]

    for i in range(3):
        response = client.post(
            f"/api/v1/interviews/{created['id']}/answers",
            json={"question_id": question_id, "answer": f"answer {i}"},
            headers={"Idempotency-Key": f"key-loop-{i}"},
        )
        data = response.json()["data"]
        if data["question"] is not None:
            question_id = data["question"]["id"]

    assert data["status"] == "COMPLETED"
    assert data["action"] == "END"
    assert data["question"] is None
    assert data["evaluation_status"] == "NOT_STARTED"

    final_response = client.post(
        f"/api/v1/interviews/{created['id']}/answers",
        json={"question_id": question_id, "answer": "too late"},
        headers={"Idempotency-Key": "key-final"},
    )
    assert final_response.status_code == 409
    assert final_response.json()["error"]["code"] == "INVALID_INTERVIEW_STATE"


# ---------------------------------------------------------------------------
# Completion
# ---------------------------------------------------------------------------


def test_complete_interview_explicit_returns_200(client: TestClient):
    created = create_interview(client)
    start_interview(client, created["id"])

    response = client.post(f"/api/v1/interviews/{created['id']}/complete")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "COMPLETED"
    assert data["evaluation_status"] == "NOT_STARTED"


def test_complete_interview_already_completed_returns_409(client: TestClient):
    created = create_interview(client)
    start_interview(client, created["id"])
    client.post(f"/api/v1/interviews/{created['id']}/complete")

    response = client.post(f"/api/v1/interviews/{created['id']}/complete")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_INTERVIEW_STATE"


# ---------------------------------------------------------------------------
# Get interview
# ---------------------------------------------------------------------------


def test_get_interview_existing_returns_200(client: TestClient):
    created = create_interview(client)
    start_interview(client, created["id"])

    response = client.get(f"/api/v1/interviews/{created['id']}")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["session_id"] == created["id"]
    assert data["status"] == "IN_PROGRESS"
    # Task 17: topic comes from the first selected topic (RAG), not a
    # hardcoded constant.
    assert data["current_topic"] == "RAG"
    assert data["current_question_number"] == 1
    assert data["questions_answered"] == 0


def test_get_interview_returns_persisted_topics_in_sequence_order(client: TestClient):
    created = create_interview(client)

    response = client.get(f"/api/v1/interviews/{created['id']}")

    assert response.status_code == 200
    topics = response.json()["data"]["topics"]
    assert topics == [
        {"topic": "RAG", "sequence_number": 1, "status": "PENDING"},
        {"topic": "AI_AGENTS", "sequence_number": 2, "status": "PENDING"},
    ]


def test_get_interview_nonexistent_returns_404(client: TestClient):
    response = client.get(f"/api/v1/interviews/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "INTERVIEW_NOT_FOUND"


# ---------------------------------------------------------------------------
# Current question restoration on GET (Task 27)
#
# `GET /interviews/{id}` must let a refreshed IN_PROGRESS interview restore
# its in-flight question instead of calling `start` again (which the
# backend would reject — CREATED-only) or the frontend showing "resume
# unsupported". See InterviewService.get_interview_state for how this is
# derived from PostgreSQL alone.
# ---------------------------------------------------------------------------


def test_get_interview_created_has_no_current_question(client: TestClient):
    created = create_interview(client)

    response = client.get(f"/api/v1/interviews/{created['id']}")

    assert response.status_code == 200
    assert response.json()["data"]["current_question"] is None


def test_get_interview_in_progress_returns_current_unanswered_question(client: TestClient):
    created = create_interview(client)
    started = start_interview(client, created["id"])

    response = client.get(f"/api/v1/interviews/{created['id']}")

    assert response.status_code == 200
    data = response.json()["data"]
    # Same shape/values as the question `start` handed back — a refresh
    # must restore the exact same question, not a new or different one.
    assert data["current_question"] == started["question"]


def test_get_interview_after_answering_returns_the_new_unanswered_question(client: TestClient):
    created = create_interview(client, question_limit=5)
    started = start_interview(client, created["id"])
    first_question_id = started["question"]["id"]

    answer_response = client.post(
        f"/api/v1/interviews/{created['id']}/answers",
        json={"question_id": first_question_id, "answer": "An answer to the first question."},
        headers={"Idempotency-Key": "get-after-answer-key"},
    )
    second_question = answer_response.json()["data"]["question"]

    response = client.get(f"/api/v1/interviews/{created['id']}")

    data = response.json()["data"]
    assert data["current_question"] == second_question
    assert data["current_question"]["id"] != first_question_id
    assert data["current_question"]["sequence"] == 2


def test_get_interview_completed_has_no_current_question(client: TestClient):
    created = create_interview(client, question_limit=3)
    started = start_interview(client, created["id"])
    question_id = started["question"]["id"]

    # Answer all 3 questions to reach COMPLETED (the fixture's fake LLM
    # always proposes FOLLOW_UP; the question_limit is what ends it).
    for i, key in enumerate(["complete-key-1", "complete-key-2", "complete-key-3"]):
        answer_response = client.post(
            f"/api/v1/interviews/{created['id']}/answers",
            json={"question_id": question_id, "answer": f"Answer {i + 1}."},
            headers={"Idempotency-Key": key},
        )
        next_question = answer_response.json()["data"]["question"]
        if next_question is not None:
            question_id = next_question["id"]

    response = client.get(f"/api/v1/interviews/{created['id']}")

    data = response.json()["data"]
    assert data["status"] == "COMPLETED"
    assert data["current_question"] is None


def test_get_interview_current_question_survives_redis_outage(client: TestClient):
    """The current question is reconstructed from PostgreSQL alone —
    `get_interview` never depends on Redis at all — so it must keep
    working even while Redis is completely unreachable."""
    created = create_interview(client)
    started = start_interview(client, created["id"])

    app.dependency_overrides[get_redis_client] = lambda: FailingAsyncRedis()
    response = client.get(f"/api/v1/interviews/{created['id']}")

    assert response.status_code == 200
    assert response.json()["data"]["current_question"] == started["question"]


def test_get_interview_after_answering_returns_the_new_question_not_the_stale_one_during_redis_outage(
    client: TestClient,
):
    """Task 29: the single-question case above could in principle pass by
    accident if the read path secretly favored "the first question ever
    created". Answering once first, so a *second* question also exists,
    proves the read path picks the genuinely current (unanswered) one —
    never the stale, already-answered first question — even while Redis is
    completely unreachable."""
    created = create_interview(client, question_limit=5)
    started = start_interview(client, created["id"])
    first_question_id = started["question"]["id"]

    answer_response = client.post(
        f"/api/v1/interviews/{created['id']}/answers",
        json={"question_id": first_question_id, "answer": "An answer to the first question."},
        headers={"Idempotency-Key": "redis-outage-after-answer-key"},
    )
    second_question = answer_response.json()["data"]["question"]
    assert second_question is not None

    app.dependency_overrides[get_redis_client] = lambda: FailingAsyncRedis()
    response = client.get(f"/api/v1/interviews/{created['id']}")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["current_question"] == second_question
    assert data["current_question"]["id"] != first_question_id
    assert data["current_question_number"] == 2


def test_get_interview_existing_fields_remain_intact_alongside_current_question(client: TestClient):
    created = create_interview(client)
    start_interview(client, created["id"])

    response = client.get(f"/api/v1/interviews/{created['id']}")

    data = response.json()["data"]
    assert set(data.keys()) == {
        "session_id",
        "role",
        "difficulty",
        "status",
        "question_limit",
        "current_topic",
        "current_question_number",
        "questions_answered",
        "topics",
        "current_question",
    }
    assert data["current_topic"] == "RAG"
    assert data["current_question_number"] == 1
    assert data["questions_answered"] == 0


# ---------------------------------------------------------------------------
# Evaluation (Task 21)
# ---------------------------------------------------------------------------


def complete_a_full_interview(client: TestClient, question_limit: int = 3) -> dict:
    """Drives an interview all the way to COMPLETED via the shared
    `fake_llm` fixture (always FOLLOW_UP until the question limit is
    reached), returning the created interview's summary dict."""
    created = create_interview(client, question_limit=question_limit)
    started = start_interview(client, created["id"])
    question_id = started["question"]["id"]
    for i in range(question_limit):
        response = client.post(
            f"/api/v1/interviews/{created['id']}/answers",
            json={"question_id": question_id, "answer": f"answer {i}"},
            headers={"Idempotency-Key": f"complete-key-{i}"},
        )
        data = response.json()["data"]
        if data["question"] is not None:
            question_id = data["question"]["id"]
    assert data["status"] == "COMPLETED"
    return created


def test_get_evaluation_for_created_interview_returns_409(client: TestClient):
    created = create_interview(client)

    response = client.get(f"/api/v1/interviews/{created['id']}/evaluation")

    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "INVALID_INTERVIEW_STATE"
    assert "message" in error


def test_get_evaluation_for_in_progress_interview_returns_409(client: TestClient):
    created = create_interview(client)
    start_interview(client, created["id"])

    response = client.get(f"/api/v1/interviews/{created['id']}/evaluation")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_INTERVIEW_STATE"


def test_get_evaluation_for_nonexistent_session_returns_404(client: TestClient):
    response = client.get(f"/api/v1/interviews/{uuid.uuid4()}/evaluation")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "INTERVIEW_NOT_FOUND"


def test_get_evaluation_for_completed_interview_returns_200_with_full_evaluation(client: TestClient):
    created = complete_a_full_interview(client)

    response = client.get(f"/api/v1/interviews/{created['id']}/evaluation")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["session_id"] == created["id"]
    for field in (
        "technical_knowledge_score",
        "reasoning_score",
        "depth_score",
        "communication_score",
        "overall_score",
    ):
        assert 0.0 <= data[field] <= 10.0
    assert data["strengths"] == ["Explained retrieval clearly."]
    assert data["weaknesses"] == ["Limited depth on reranking."]
    assert len(data["evidence"]) == 1
    assert data["evidence"][0]["claim"] == "Understood the basics of retrieval."


def test_evaluation_overall_score_is_backend_computed_not_the_llms_value(client: TestClient):
    # The shared `fake_llm` fixture deliberately configures an absurd
    # overall_score (1.0) alongside much higher component scores — the
    # persisted overall_score must be the backend's average of the four
    # components, never that value.
    created = complete_a_full_interview(client)

    response = client.get(f"/api/v1/interviews/{created['id']}/evaluation")

    data = response.json()["data"]
    expected = round(
        (data["technical_knowledge_score"] + data["reasoning_score"] + data["depth_score"] + data["communication_score"])
        / 4,
        2,
    )
    assert data["overall_score"] == expected
    assert data["overall_score"] != 1.0


def test_evaluation_is_idempotent_and_does_not_call_the_llm_again(client: TestClient, fake_llm: FakeLLMProvider):
    created = complete_a_full_interview(client)

    first = client.get(f"/api/v1/interviews/{created['id']}/evaluation")
    assert first.status_code == 200
    calls_after_first = len([c for c in fake_llm.calls if c[0] == "EvaluationResult"])
    assert calls_after_first == 1

    second = client.get(f"/api/v1/interviews/{created['id']}/evaluation")
    third = client.get(f"/api/v1/interviews/{created['id']}/evaluation")

    assert second.status_code == 200
    assert third.status_code == 200
    assert second.json() == first.json() == third.json()
    assert len([c for c in fake_llm.calls if c[0] == "EvaluationResult"]) == calls_after_first


def test_evaluation_does_not_change_interview_lifecycle_state(client: TestClient):
    created = complete_a_full_interview(client)

    client.get(f"/api/v1/interviews/{created['id']}/evaluation")

    state = client.get(f"/api/v1/interviews/{created['id']}").json()["data"]
    assert state["status"] == "COMPLETED"
    assert state["current_question_number"] == 3
    assert state["questions_answered"] == 3


# ---------------------------------------------------------------------------
# Response envelope
# ---------------------------------------------------------------------------


def test_success_responses_use_data_envelope(client: TestClient):
    response = client.post("/api/v1/interviews", json=VALID_CREATE_PAYLOAD)

    body = response.json()
    assert set(body.keys()) == {"data"}


def test_error_responses_use_error_envelope(client: TestClient):
    response = client.get(f"/api/v1/interviews/{uuid.uuid4()}")

    body = response.json()
    assert set(body.keys()) == {"error"}
    assert set(body["error"].keys()) == {"code", "message"}


# ---------------------------------------------------------------------------
# Redis runtime-state lifecycle integration (Task 11)
#
# These use the `fake_redis` in-memory double injected via dependency
# override so the "Redis mirroring succeeds" path is actually exercised
# (a real, unavailable local Redis would otherwise always hit the
# documented failure-tolerance path — see test_interview_service.py's
# note and the Task 11 report for a dedicated test of that path too).
# API responses never expose Redis details; these tests reach into
# `fake_redis` directly, not through any HTTP response.
# ---------------------------------------------------------------------------


def test_start_interview_creates_redis_runtime_state(client: TestClient, fake_redis: FakeAsyncRedis):
    created = create_interview(client, question_limit=3)

    started = start_interview(client, created["id"])

    key = f"interview:{created['id']}:state"
    assert key in fake_redis.store
    state = fake_redis.store[key]
    assert '"status":"IN_PROGRESS"' in state
    assert '"current_node":"WAITING_FOR_ANSWER"' in state
    assert f'"current_question_id":"{started["question"]["id"]}"' in state
    assert fake_redis.ttls[key] > 0


def test_start_interview_redis_state_reflects_the_actual_first_selected_topic(
    client: TestClient, fake_redis: FakeAsyncRedis
):
    # Task 17: a Frontend interview's mirrored runtime state must carry
    # the real first selected topic (REACT here), not the AI Engineer
    # placeholder this same fixture used to hardcode.
    payload = {
        **VALID_CREATE_PAYLOAD,
        "role": "FRONTEND_DEVELOPER",
        "topics": ["REACT", "JAVASCRIPT"],
    }
    created = client.post("/api/v1/interviews", json=payload).json()["data"]

    start_interview(client, created["id"])

    key = f"interview:{created['id']}:state"
    state = fake_redis.store[key]
    assert '"current_topic":"REACT"' in state


def test_submit_answer_updates_redis_runtime_state(client: TestClient, fake_redis: FakeAsyncRedis):
    created = create_interview(client, question_limit=3)
    started = start_interview(client, created["id"])
    key = f"interview:{created['id']}:state"

    response = client.post(
        f"/api/v1/interviews/{created['id']}/answers",
        json={"question_id": started["question"]["id"], "answer": "An answer."},
        headers={"Idempotency-Key": "redis-lifecycle-key"},
    )
    next_question_id = response.json()["data"]["question"]["id"]

    state = fake_redis.store[key]
    assert f'"current_question_id":"{next_question_id}"' in state
    assert '"question_number":2' in state
    assert next_question_id != started["question"]["id"]


def test_complete_interview_marks_redis_state_completed(client: TestClient, fake_redis: FakeAsyncRedis):
    created = create_interview(client, question_limit=3)
    started = start_interview(client, created["id"])
    key = f"interview:{created['id']}:state"

    client.post(f"/api/v1/interviews/{created['id']}/complete")

    state = fake_redis.store[key]
    assert '"status":"COMPLETED"' in state
    assert '"current_node":"COMPLETED"' in state
    # current_question_id still reflects the last/current question rather
    # than being forced to null — consistent with what a Redis-miss rebuild
    # of this same session would independently reconstruct via
    # InterviewRepository.get_current_question (see RuntimeStateService.build_state).
    assert f'"current_question_id":"{started["question"]["id"]}"' in state


# ---------------------------------------------------------------------------
# Locking, rate limiting, idempotency (Task 12)
# ---------------------------------------------------------------------------


def test_answer_lock_returns_409_when_already_busy(client: TestClient, fake_redis: FakeAsyncRedis):
    created = create_interview(client, question_limit=3)
    started = start_interview(client, created["id"])
    question_id = started["question"]["id"]

    # Simulate another in-flight request already holding the lock.
    lock_key = f"interview:{created['id']}:lock"

    asyncio.run(fake_redis.set(lock_key, "someone-elses-token", nx=True, ex=30))

    response = client.post(
        f"/api/v1/interviews/{created['id']}/answers",
        json={"question_id": question_id, "answer": "answer"},
        headers={"Idempotency-Key": "busy-key"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INTERVIEW_BUSY"


def test_start_lock_returns_409_when_already_busy(client: TestClient, fake_redis: FakeAsyncRedis):
    created = create_interview(client)
    lock_key = f"interview:{created['id']}:lock"

    asyncio.run(fake_redis.set(lock_key, "someone-elses-token", nx=True, ex=30))

    response = client.post(f"/api/v1/interviews/{created['id']}/start")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INTERVIEW_BUSY"


def test_answer_rate_limit_returns_429_after_limit(client: TestClient):
    created = create_interview(client, question_limit=10)
    started = start_interview(client, created["id"])
    question_id = started["question"]["id"]

    statuses = []
    for i in range(11):
        response = client.post(
            f"/api/v1/interviews/{created['id']}/answers",
            json={"question_id": question_id, "answer": f"answer {i}"},
            headers={"Idempotency-Key": f"rate-limit-key-{i}"},
        )
        statuses.append(response)

    codes = [r.status_code for r in statuses]
    assert codes[:10].count(429) == 0
    assert codes[10] == 429

    final = statuses[10]
    body = final.json()
    assert body["error"]["code"] == "RATE_LIMITED"
    assert "Retry-After" in final.headers
    assert int(final.headers["Retry-After"]) > 0


def test_idempotent_retry_returns_same_response_with_no_second_mutation(client: TestClient):
    created = create_interview(client, question_limit=3)
    started = start_interview(client, created["id"])
    question_id = started["question"]["id"]
    headers = {"Idempotency-Key": "retry-key-1"}
    payload = {"question_id": question_id, "answer": "Answer A"}

    first = client.post(f"/api/v1/interviews/{created['id']}/answers", json=payload, headers=headers)
    assert first.status_code == 200

    second = client.post(f"/api/v1/interviews/{created['id']}/answers", json=payload, headers=headers)

    assert second.status_code == 200
    assert second.json() == first.json()

    state = client.get(f"/api/v1/interviews/{created['id']}").json()["data"]
    assert state["questions_answered"] == 1
    assert state["current_question_number"] == 2


def test_idempotency_key_reused_with_different_payload_returns_409(client: TestClient):
    created = create_interview(client, question_limit=3)
    started = start_interview(client, created["id"])
    question_id = started["question"]["id"]
    headers = {"Idempotency-Key": "conflict-key"}

    first = client.post(
        f"/api/v1/interviews/{created['id']}/answers",
        json={"question_id": question_id, "answer": "Answer A"},
        headers=headers,
    )
    assert first.status_code == 200

    second = client.post(
        f"/api/v1/interviews/{created['id']}/answers",
        json={"question_id": question_id, "answer": "A completely different answer"},
        headers=headers,
    )

    assert second.status_code == 409
    assert second.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_invalid_idempotency_key_length_returns_400(client: TestClient):
    created = create_interview(client, question_limit=3)
    started = start_interview(client, created["id"])
    question_id = started["question"]["id"]

    response = client.post(
        f"/api/v1/interviews/{created['id']}/answers",
        json={"question_id": question_id, "answer": "answer"},
        headers={"Idempotency-Key": "x" * 129},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_IDEMPOTENCY_KEY"


def test_concurrent_identical_answer_requests_produce_exactly_one_mutation(client: TestClient):
    created = create_interview(client, question_limit=3)
    started = start_interview(client, created["id"])
    question_id = started["question"]["id"]

    def submit():
        return client.post(
            f"/api/v1/interviews/{created['id']}/answers",
            json={"question_id": question_id, "answer": "Same answer"},
            headers={"Idempotency-Key": "concurrent-key"},
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_a = executor.submit(submit)
        future_b = executor.submit(submit)
        response_a = future_a.result()
        response_b = future_b.result()

    statuses = {response_a.status_code, response_b.status_code}
    assert statuses <= {200, 409}
    assert 200 in statuses

    state = client.get(f"/api/v1/interviews/{created['id']}").json()["data"]
    assert state["questions_answered"] == 1


def test_concurrent_complete_and_answer_do_not_corrupt_state(client: TestClient):
    created = create_interview(client, question_limit=3)
    started = start_interview(client, created["id"])
    question_id = started["question"]["id"]

    def do_answer():
        return client.post(
            f"/api/v1/interviews/{created['id']}/answers",
            json={"question_id": question_id, "answer": "answer"},
            headers={"Idempotency-Key": "race-answer-key"},
        )

    def do_complete():
        return client.post(f"/api/v1/interviews/{created['id']}/complete")

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_answer = executor.submit(do_answer)
        future_complete = executor.submit(do_complete)
        answer_response = future_answer.result()
        complete_response = future_complete.result()

    for response in (answer_response, complete_response):
        assert response.status_code in (200, 409)

    final = client.get(f"/api/v1/interviews/{created['id']}")
    assert final.status_code == 200
    data = final.json()["data"]
    assert data["status"] in ("IN_PROGRESS", "COMPLETED")
    assert data["questions_answered"] in (0, 1)
