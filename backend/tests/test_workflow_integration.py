"""Task 18 — integration tests for the real LangGraph-driven interview
lifecycle: `/start` and `/answers` now run the actual adaptive workflow
(via a `FakeLLMProvider`, never a real provider) instead of the old
deterministic placeholder.

Each test builds its own `TestClient` (via `build_client`) so it can wire
in a `FakeLLMProvider` configured for that specific scenario — unlike
`tests/test_interview_api.py`'s shared `client` fixture, which uses one
fixed FOLLOW_UP-only fake across all of its (mostly lifecycle/Redis/
locking) tests.
"""

import asyncio
import concurrent.futures
import logging
import uuid
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_knowledge_retrieval_service, get_llm_provider
from app.db.base import Base
from app.db.session import get_db
from app.domain.enums import Difficulty, InterviewTopic, QuestionType, Role
from app.knowledge.retrieval_service import KnowledgeRetrievalService
from app.llm.exceptions import (
    LLMConfigurationError,
    LLMError,
    LLMInvalidResponseError,
    LLMProviderUnavailableError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from app.main import app
from app.models.interview_question import InterviewQuestion
from app.models.interview_session import InterviewSession
from app.redis.client import get_redis_client
from app.workflows.interview.models import AnswerAnalysis, GeneratedQuestion, NextAction
from tests.fakes import FakeAsyncRedis, FakeLLMProvider

# Same sqlite-compatibility strategy as tests/test_interview_api.py.


@compiles(UUID, "sqlite")
def _compile_uuid_sqlite(element, compiler, **kw):
    return "CHAR(32)"


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(element, compiler, **kw):
    return "JSON"


@contextmanager
def build_client(
    fake_redis: FakeAsyncRedis,
    llm_provider: FakeLLMProvider,
    knowledge_service: KnowledgeRetrievalService | None = None,
):
    """Like `test_interview_api.py`'s `client` fixture, but a plain context
    manager parameterized by the `FakeLLMProvider` this scenario needs, and
    also yields the raw sessionmaker so tests can inspect durable state
    (e.g. `completed_at`) that isn't exposed through any API response.

    `knowledge_service` defaults to `None` (no knowledge layer, ungrounded
    generation) — must be overridden explicitly rather than left to the
    real `get_knowledge_retrieval_service` fallback, since a real
    `LLM_API_KEY` may be configured in this environment's `.env` and the
    embedding factory would otherwise reuse it, risking a real OpenAI/
    Qdrant network call from these tests (Task 20 grounding tests pass a
    fake-backed `KnowledgeRetrievalService` here explicitly instead).
    """
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
        return llm_provider

    def override_get_knowledge_retrieval_service():
        return knowledge_service

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis_client] = override_get_redis_client
    app.dependency_overrides[get_llm_provider] = override_get_llm_provider
    app.dependency_overrides[get_knowledge_retrieval_service] = override_get_knowledge_retrieval_service
    try:
        with TestClient(app) as test_client:
            yield test_client, testing_session_local
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def create_interview(
    client: TestClient,
    role: str = "AI_ENGINEER",
    topics: list[str] | None = None,
    question_limit: int = 5,
    difficulty: str = "MEDIUM",
) -> dict:
    payload = {
        "role": role,
        "difficulty": difficulty,
        "topics": topics or ["RAG", "AI_AGENTS"],
        "question_limit": question_limit,
    }
    response = client.post("/api/v1/interviews", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["data"]


def start_interview(client: TestClient, session_id: str) -> dict:
    response = client.post(f"/api/v1/interviews/{session_id}/start")
    assert response.status_code == 200, response.text
    return response.json()["data"]


def submit_answer(client: TestClient, session_id: str, question_id: str, answer: str, key: str):
    return client.post(
        f"/api/v1/interviews/{session_id}/answers",
        json={"question_id": question_id, "answer": answer},
        headers={"Idempotency-Key": key},
    )


def initial_question(topic: InterviewTopic, text: str = "Tell me about it.") -> GeneratedQuestion:
    return GeneratedQuestion(question=text, topic=topic, difficulty=Difficulty.MEDIUM, question_type=QuestionType.INITIAL)


def analysis(needs_follow_up: bool = True) -> AnswerAnalysis:
    return AnswerAnalysis(
        understanding="GOOD",
        correctness=0.7,
        depth=0.6,
        concepts_demonstrated=["retrieval"],
        concepts_missing=["reranking"],
        reasoning_quality="STRONG",
        needs_follow_up=needs_follow_up,
    )


# ---------------------------------------------------------------------------
# Start — LangGraph generates the first question, per role
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "role,topics,first_topic",
    [
        ("FRONTEND_DEVELOPER", ["REACT", "JAVASCRIPT"], "REACT"),
        ("BACKEND_DEVELOPER", ["DATABASES", "REST_APIS"], "DATABASES"),
        ("AI_ENGINEER", ["RAG", "AI_AGENTS"], "RAG"),
    ],
)
def test_start_interview_uses_langgraph_generated_question(role, topics, first_topic):
    fake_redis = FakeAsyncRedis()
    fake_llm = FakeLLMProvider(
        structured_responses={"GeneratedQuestion": initial_question(InterviewTopic[first_topic], "Generated by the graph.")}
    )
    with build_client(fake_redis, fake_llm) as (client, _):
        created = create_interview(client, role=role, topics=topics)
        started = start_interview(client, created["id"])

        assert started["question"]["topic"] == first_topic
        assert started["question"]["type"] == "INITIAL"
        assert started["question"]["text"] == "Generated by the graph."
        # Exactly one structured call for the initial-question graph.
        assert [schema for schema, _ in fake_llm.calls] == ["GeneratedQuestion"]


# ---------------------------------------------------------------------------
# Adaptive FOLLOW_UP
# ---------------------------------------------------------------------------


def test_follow_up_keeps_topic_in_progress_and_persists_everything():
    fake_redis = FakeAsyncRedis()
    fake_llm = FakeLLMProvider(
        structured_responses={
            "GeneratedQuestion": initial_question(InterviewTopic.RAG),
            "AnswerAnalysis": analysis(needs_follow_up=True),
            "NextAction": NextAction(
                action="FOLLOW_UP", topic=InterviewTopic.RAG, difficulty=Difficulty.MEDIUM, rationale="Probe deeper."
            ),
        }
    )
    with build_client(fake_redis, fake_llm) as (client, _):
        created = create_interview(client, topics=["RAG", "AI_AGENTS"])
        started = start_interview(client, created["id"])

        response = submit_answer(
            client, created["id"], started["question"]["id"], "RAG retrieves relevant context.", "k-follow-up"
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["action"] == "FOLLOW_UP"
        assert data["question"]["topic"] == "RAG"
        assert data["question"]["type"] == "FOLLOW_UP"
        assert data["question"]["id"] != started["question"]["id"]

        state = client.get(f"/api/v1/interviews/{created['id']}").json()["data"]
        assert state["questions_answered"] == 1
        assert state["current_question_number"] == 2
        topics_by_name = {t["topic"]: t["status"] for t in state["topics"]}
        assert topics_by_name["RAG"] == "IN_PROGRESS"
        assert topics_by_name["AI_AGENTS"] == "PENDING"

        # LangGraph is not re-invoked for the GET read.
        key = f"interview:{created['id']}:state"
        assert f'"current_question_id":"{data["question"]["id"]}"' in fake_redis.store[key]
        assert '"question_number":2' in fake_redis.store[key]


# ---------------------------------------------------------------------------
# CLARIFY
# ---------------------------------------------------------------------------


def test_clarify_stays_on_topic_and_sets_clarification_question_type():
    fake_redis = FakeAsyncRedis()
    fake_llm = FakeLLMProvider(
        structured_responses={
            "GeneratedQuestion": initial_question(InterviewTopic.RAG),
            "AnswerAnalysis": analysis(needs_follow_up=True),
            "NextAction": NextAction(
                action="CLARIFY", topic=InterviewTopic.RAG, difficulty=Difficulty.MEDIUM, rationale="Ambiguous answer."
            ),
        }
    )
    with build_client(fake_redis, fake_llm) as (client, _):
        created = create_interview(client, topics=["RAG", "AI_AGENTS"])
        started = start_interview(client, created["id"])

        response = submit_answer(
            client, created["id"], started["question"]["id"], "Embeddings sort of store meaning I guess.", "k-clarify"
        )

        assert response.status_code == 200
        data = response.json()["data"]
        # `SubmitAnswerResponse.action` mirrors the persisted question's
        # type (see `interviews.py`), not the graph's raw action string —
        # CLARIFY maps to the CLARIFICATION question type.
        assert data["action"] == "CLARIFICATION"
        assert data["question"]["topic"] == "RAG"
        assert data["question"]["type"] == "CLARIFICATION"

        state = client.get(f"/api/v1/interviews/{created['id']}").json()["data"]
        topics_by_name = {t["topic"]: t["status"] for t in state["topics"]}
        assert topics_by_name["RAG"] == "IN_PROGRESS"


# ---------------------------------------------------------------------------
# NEW_TOPIC
# ---------------------------------------------------------------------------


def test_new_topic_completes_old_topic_and_activates_the_next_selected_topic():
    fake_redis = FakeAsyncRedis()
    fake_llm = FakeLLMProvider(
        structured_responses={
            "GeneratedQuestion": initial_question(InterviewTopic.RAG),
            "AnswerAnalysis": analysis(needs_follow_up=False),
            "NextAction": NextAction(
                action="NEW_TOPIC",
                topic=InterviewTopic.AI_AGENTS,
                difficulty=Difficulty.MEDIUM,
                rationale="RAG sufficiently covered.",
            ),
        }
    )
    with build_client(fake_redis, fake_llm) as (client, _):
        created = create_interview(client, topics=["RAG", "AI_AGENTS"])
        started = start_interview(client, created["id"])

        response = submit_answer(
            client, created["id"], started["question"]["id"], "RAG retrieves relevant context.", "k-new-topic"
        )

        assert response.status_code == 200
        data = response.json()["data"]
        # `SubmitAnswerResponse.action` mirrors the persisted question's
        # type — NEW_TOPIC maps to the TOPIC_TRANSITION question type.
        assert data["action"] == "TOPIC_TRANSITION"
        assert data["question"]["topic"] == "AI_AGENTS"
        assert data["question"]["type"] == "TOPIC_TRANSITION"

        state = client.get(f"/api/v1/interviews/{created['id']}").json()["data"]
        topics_by_name = {t["topic"]: t["status"] for t in state["topics"]}
        assert topics_by_name["RAG"] == "COMPLETED"
        assert topics_by_name["AI_AGENTS"] == "IN_PROGRESS"
        assert state["current_topic"] == "AI_AGENTS"


# ---------------------------------------------------------------------------
# END
# ---------------------------------------------------------------------------


def test_end_action_completes_the_interview_without_a_next_question():
    fake_redis = FakeAsyncRedis()
    fake_llm = FakeLLMProvider(
        structured_responses={
            "GeneratedQuestion": initial_question(InterviewTopic.RAG),
            "AnswerAnalysis": analysis(needs_follow_up=False),
            "NextAction": NextAction(action="END", topic=None, difficulty=Difficulty.MEDIUM, rationale="Coverage sufficient."),
        }
    )
    with build_client(fake_redis, fake_llm) as (client, session_factory):
        created = create_interview(client, topics=["RAG"], question_limit=5)
        started = start_interview(client, created["id"])

        response = submit_answer(client, created["id"], started["question"]["id"], "A complete answer.", "k-end")

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["action"] == "END"
        assert data["question"] is None
        assert data["status"] == "COMPLETED"
        assert data["evaluation_status"] == "NOT_STARTED"

        state = client.get(f"/api/v1/interviews/{created['id']}").json()["data"]
        assert state["status"] == "COMPLETED"

        db = session_factory()
        try:
            persisted = db.get(InterviewSession, uuid.UUID(created["id"]))
            assert persisted.completed_at is not None
        finally:
            db.close()

        key = f"interview:{created['id']}:state"
        assert '"status":"COMPLETED"' in fake_redis.store[key]
        assert '"current_node":"COMPLETED"' in fake_redis.store[key]


# ---------------------------------------------------------------------------
# Question limit overrides the graph's proposal
# ---------------------------------------------------------------------------


def test_question_limit_forces_completion_even_when_llm_proposes_follow_up():
    fake_redis = FakeAsyncRedis()
    fake_llm = FakeLLMProvider(
        structured_responses={
            "GeneratedQuestion": initial_question(InterviewTopic.RAG),
            "AnswerAnalysis": analysis(needs_follow_up=True),
            # Always proposes FOLLOW_UP, even at the last question.
            "NextAction": NextAction(
                action="FOLLOW_UP", topic=InterviewTopic.RAG, difficulty=Difficulty.MEDIUM, rationale="Keep probing."
            ),
        }
    )
    with build_client(fake_redis, fake_llm) as (client, _):
        created = create_interview(client, topics=["RAG"], question_limit=3)
        started = start_interview(client, created["id"])
        question_id = started["question"]["id"]

        data = None
        for i in range(3):
            response = submit_answer(client, created["id"], question_id, f"answer {i}", f"k-limit-{i}")
            assert response.status_code == 200
            data = response.json()["data"]
            if data["question"] is not None:
                question_id = data["question"]["id"]

        assert data["status"] == "COMPLETED"
        assert data["action"] == "END"
        assert data["question"] is None


# ---------------------------------------------------------------------------
# Invalid decision -> Task 15 fallback still applies after integration
# ---------------------------------------------------------------------------


def test_unselected_new_topic_proposal_falls_back_to_follow_up():
    fake_redis = FakeAsyncRedis()
    fake_llm = FakeLLMProvider(
        structured_responses={
            "GeneratedQuestion": initial_question(InterviewTopic.RAG),
            "AnswerAnalysis": analysis(needs_follow_up=False),
            # EMBEDDINGS_VECTOR_DB was never selected for this session.
            "NextAction": NextAction(
                action="NEW_TOPIC",
                topic=InterviewTopic.EMBEDDINGS_VECTOR_DB,
                difficulty=Difficulty.MEDIUM,
                rationale="Move on.",
            ),
        }
    )
    with build_client(fake_redis, fake_llm) as (client, _):
        created = create_interview(client, topics=["RAG", "AI_AGENTS"])
        started = start_interview(client, created["id"])

        response = submit_answer(
            client, created["id"], started["question"]["id"], "RAG retrieves relevant context.", "k-invalid-topic"
        )

        assert response.status_code == 200
        data = response.json()["data"]
        # Falls back to FOLLOW_UP on the current topic rather than honoring
        # the invalid proposal.
        assert data["action"] == "FOLLOW_UP"
        assert data["question"]["topic"] == "RAG"

        state = client.get(f"/api/v1/interviews/{created['id']}").json()["data"]
        topics_by_name = {t["topic"]: t["status"] for t in state["topics"]}
        assert topics_by_name["RAG"] == "IN_PROGRESS"
        assert topics_by_name["AI_AGENTS"] == "PENDING"


# ---------------------------------------------------------------------------
# LLM / workflow failure
# ---------------------------------------------------------------------------


class _FailsAnalysisOnce(FakeLLMProvider):
    """Fails the first `AnswerAnalysis` call, then behaves normally — models
    a transient provider failure, letting one test cover both "no partial
    mutation on failure" and "the interview is recoverable afterwards"."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fail_next_analysis = True

    async def generate_structured(self, messages, output_schema):
        if output_schema.__name__ == "AnswerAnalysis" and self._fail_next_analysis:
            self._fail_next_analysis = False
            raise LLMTimeoutError("simulated analysis timeout")
        return await super().generate_structured(messages, output_schema)


def test_llm_failure_does_not_partially_mutate_and_interview_stays_recoverable():
    fake_redis = FakeAsyncRedis()
    fake_llm = _FailsAnalysisOnce(
        structured_responses={
            "GeneratedQuestion": initial_question(InterviewTopic.RAG),
            "AnswerAnalysis": analysis(needs_follow_up=True),
            "NextAction": NextAction(
                action="FOLLOW_UP", topic=InterviewTopic.RAG, difficulty=Difficulty.MEDIUM, rationale="Keep going."
            ),
        }
    )
    with build_client(fake_redis, fake_llm) as (client, _):
        created = create_interview(client, topics=["RAG", "AI_AGENTS"], question_limit=5)
        started = start_interview(client, created["id"])
        key_for_state = f"interview:{created['id']}:state"
        state_before_failure = fake_redis.store[key_for_state]

        failing_response = submit_answer(
            client, created["id"], started["question"]["id"], "An answer.", "k-fail-1"
        )

        assert failing_response.status_code == 504
        body = failing_response.json()
        assert body["error"]["code"] == "AI_SERVICE_TIMEOUT"
        assert "timeout" not in body["error"]["message"].lower() or "simulated" not in body["error"]["message"]

        # No partial mutation: no candidate message, question number
        # unchanged, Redis state untouched.
        state = client.get(f"/api/v1/interviews/{created['id']}").json()["data"]
        assert state["status"] == "IN_PROGRESS"
        assert state["questions_answered"] == 0
        assert state["current_question_number"] == 1
        assert fake_redis.store[key_for_state] == state_before_failure

        # Recoverable: retrying (the fake now succeeds) completes normally.
        retry_response = submit_answer(
            client, created["id"], started["question"]["id"], "An answer.", "k-fail-2"
        )
        assert retry_response.status_code == 200
        data = retry_response.json()["data"]
        assert data["action"] == "FOLLOW_UP"

        state_after = client.get(f"/api/v1/interviews/{created['id']}").json()["data"]
        assert state_after["questions_answered"] == 1
        assert state_after["current_question_number"] == 2


# ---------------------------------------------------------------------------
# LLM / workflow failure — full status/code matrix (Task 29)
#
# The scenario above proves one failure mode (timeout during an answer
# turn) in detail, including recovery. These two parametrized tests fill
# the gap of proving *every* registered LLMError subclass maps to its own
# stable status/code with no partial mutation, for both `/start` (fails
# before the session ever leaves CREATED) and `/answers` (fails before the
# candidate's turn is recorded) — this matrix previously existed only for
# `/evaluation` and `/result` (see test_evaluation_api.py), never for the
# interview lifecycle endpoints themselves.
# ---------------------------------------------------------------------------


class _FailsAnalysisWith(FakeLLMProvider):
    """Fails the first `AnswerAnalysis` call with a specific error, then
    behaves normally — lets a parametrized test drive `start` successfully
    before failing only the answer turn's analysis step.

    Deliberately named `_pending_analysis_error`, not `_error`: the base
    `FakeLLMProvider` already uses `self._error` to mean "fail every call
    unconditionally" (checked before it even looks at the schema name), so
    reusing that name here would fail `start`'s `GeneratedQuestion` call
    too, not just the targeted `AnswerAnalysis` one.
    """

    def __init__(self, error: Exception, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pending_analysis_error = error

    async def generate_structured(self, messages, output_schema):
        if output_schema.__name__ == "AnswerAnalysis" and self._pending_analysis_error is not None:
            error, self._pending_analysis_error = self._pending_analysis_error, None
            raise error
        return await super().generate_structured(messages, output_schema)


_LLM_FAILURE_CASES = [
    (LLMTimeoutError("simulated"), 504, "AI_SERVICE_TIMEOUT"),
    (LLMRateLimitError("simulated"), 429, "AI_SERVICE_RATE_LIMITED"),
    (LLMProviderUnavailableError("simulated"), 503, "AI_SERVICE_UNAVAILABLE"),
    (LLMInvalidResponseError("simulated"), 502, "AI_SERVICE_INVALID_RESPONSE"),
    (LLMConfigurationError("simulated"), 500, "AI_SERVICE_MISCONFIGURED"),
    (LLMError("simulated"), 502, "AI_SERVICE_ERROR"),
]


@pytest.mark.parametrize("error,expected_status,expected_code", _LLM_FAILURE_CASES)
def test_llm_failure_during_start_maps_to_stable_error_and_session_stays_created(
    error, expected_status, expected_code
):
    fake_redis = FakeAsyncRedis()
    failing_llm = FakeLLMProvider(error=error)

    with build_client(fake_redis, failing_llm) as (client, session_factory):
        created = create_interview(client, topics=["RAG", "AI_AGENTS"])

        response = client.post(f"/api/v1/interviews/{created['id']}/start")

        assert response.status_code == expected_status
        body = response.json()
        assert body["error"]["code"] == expected_code
        assert "simulated" not in body["error"]["message"]
        assert "data" not in body

        # The session never left CREATED, and no question was persisted —
        # a failed pre-mutation LLM call must not advance the lifecycle.
        state = client.get(f"/api/v1/interviews/{created['id']}").json()["data"]
        assert state["status"] == "CREATED"
        assert state["current_question_number"] == 0

        db = session_factory()
        try:
            rows = db.execute(
                select(InterviewQuestion).where(InterviewQuestion.session_id == uuid.UUID(created["id"]))
            ).scalars().all()
            assert rows == []
        finally:
            db.close()


@pytest.mark.parametrize("error,expected_status,expected_code", _LLM_FAILURE_CASES)
def test_llm_failure_during_answer_maps_to_stable_error_and_does_not_mutate(
    error, expected_status, expected_code
):
    fake_redis = FakeAsyncRedis()
    fake_llm = _FailsAnalysisWith(
        error,
        structured_responses={
            "GeneratedQuestion": initial_question(InterviewTopic.RAG),
            "AnswerAnalysis": analysis(needs_follow_up=True),
            "NextAction": NextAction(
                action="FOLLOW_UP", topic=InterviewTopic.RAG, difficulty=Difficulty.MEDIUM, rationale="Keep going."
            ),
        },
    )

    with build_client(fake_redis, fake_llm) as (client, session_factory):
        created = create_interview(client, topics=["RAG", "AI_AGENTS"])
        started = start_interview(client, created["id"])

        response = submit_answer(
            client, created["id"], started["question"]["id"], "An answer.", f"fail-key-{expected_code}"
        )

        assert response.status_code == expected_status
        body = response.json()
        assert body["error"]["code"] == expected_code
        assert "simulated" not in body["error"]["message"]
        assert "data" not in body

        # No partial mutation: still IN_PROGRESS on question 1, no
        # candidate message recorded, no second question created.
        state = client.get(f"/api/v1/interviews/{created['id']}").json()["data"]
        assert state["status"] == "IN_PROGRESS"
        assert state["questions_answered"] == 0
        assert state["current_question_number"] == 1

        db = session_factory()
        try:
            rows = db.execute(
                select(InterviewQuestion).where(InterviewQuestion.session_id == uuid.UUID(created["id"]))
            ).scalars().all()
            assert len(rows) == 1
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Idempotency — no second adaptive turn
# ---------------------------------------------------------------------------


def test_idempotent_replay_does_not_invoke_the_workflow_again():
    fake_redis = FakeAsyncRedis()
    fake_llm = FakeLLMProvider(
        structured_responses={
            "GeneratedQuestion": initial_question(InterviewTopic.RAG),
            "AnswerAnalysis": analysis(needs_follow_up=True),
            "NextAction": NextAction(
                action="FOLLOW_UP", topic=InterviewTopic.RAG, difficulty=Difficulty.MEDIUM, rationale="Keep going."
            ),
        }
    )
    with build_client(fake_redis, fake_llm) as (client, _):
        created = create_interview(client, topics=["RAG", "AI_AGENTS"])
        started = start_interview(client, created["id"])

        first = submit_answer(client, created["id"], started["question"]["id"], "Answer A", "idem-key-1")
        assert first.status_code == 200
        calls_after_first = len(fake_llm.calls)
        assert calls_after_first > 1  # start (1) + a full answer turn (analysis, decision, question)

        second = submit_answer(client, created["id"], started["question"]["id"], "Answer A", "idem-key-1")

        assert second.status_code == 200
        assert second.json() == first.json()
        assert len(fake_llm.calls) == calls_after_first  # no second adaptive turn was executed

        state = client.get(f"/api/v1/interviews/{created['id']}").json()["data"]
        assert state["questions_answered"] == 1
        assert state["current_question_number"] == 2


# ---------------------------------------------------------------------------
# Concurrency — the lock still prevents double advancement
# ---------------------------------------------------------------------------


def test_concurrent_answers_run_the_workflow_at_most_once():
    fake_redis = FakeAsyncRedis()
    fake_llm = FakeLLMProvider(
        structured_responses={
            "GeneratedQuestion": initial_question(InterviewTopic.RAG),
            "AnswerAnalysis": analysis(needs_follow_up=True),
            "NextAction": NextAction(
                action="FOLLOW_UP", topic=InterviewTopic.RAG, difficulty=Difficulty.MEDIUM, rationale="Keep going."
            ),
        }
    )
    with build_client(fake_redis, fake_llm) as (client, _):
        created = create_interview(client, topics=["RAG", "AI_AGENTS"])
        started = start_interview(client, created["id"])
        calls_after_start = len(fake_llm.calls)

        def submit():
            return submit_answer(client, created["id"], started["question"]["id"], "Same answer", "concurrent-key")

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_a = executor.submit(submit)
            future_b = executor.submit(submit)
            response_a = future_a.result()
            response_b = future_b.result()

        statuses = {response_a.status_code, response_b.status_code}
        assert statuses <= {200, 409}
        assert 200 in statuses

        # Exactly one answer turn's worth of LLM calls happened — the
        # losing request was blocked by the lock before ever reaching the
        # workflow, not raced through it.
        assert len(fake_llm.calls) - calls_after_start == 3

        state = client.get(f"/api/v1/interviews/{created['id']}").json()["data"]
        assert state["questions_answered"] == 1
        assert state["current_question_number"] == 2


# ---------------------------------------------------------------------------
# Sensitive data must never reach logs
# ---------------------------------------------------------------------------


def test_candidate_answer_and_rationale_never_appear_in_logs(caplog):
    fake_redis = FakeAsyncRedis()
    secret_answer = "MySecretAnswerToken12345"
    secret_rationale = "InternalRationaleTextThatMustStayHidden"
    fake_llm = FakeLLMProvider(
        structured_responses={
            "GeneratedQuestion": initial_question(InterviewTopic.RAG),
            "AnswerAnalysis": analysis(needs_follow_up=True),
            "NextAction": NextAction(
                action="FOLLOW_UP", topic=InterviewTopic.RAG, difficulty=Difficulty.MEDIUM, rationale=secret_rationale
            ),
        }
    )
    with build_client(fake_redis, fake_llm) as (client, _):
        created = create_interview(client, topics=["RAG", "AI_AGENTS"])
        started = start_interview(client, created["id"])

        with caplog.at_level(logging.DEBUG):
            response = submit_answer(client, created["id"], started["question"]["id"], secret_answer, "k-sensitive")

        assert response.status_code == 200
        full_log_text = "\n".join(record.getMessage() for record in caplog.records)
        assert secret_answer not in full_log_text
        assert secret_rationale not in full_log_text


# ---------------------------------------------------------------------------
# Architecture: LangGraph nodes never touch Redis or commit directly
# ---------------------------------------------------------------------------


def test_workflow_nodes_source_never_references_redis_or_commit():
    import inspect

    from app.workflows.interview import decision_validator, graph, nodes, routing

    for module in (nodes, graph, routing, decision_validator):
        source = inspect.getsource(module)
        # Checks for actual Redis usage (an import or a call through
        # `app.redis.*`), not just the word "redis" — several of these
        # modules' docstrings/comments *describe* the "no Redis" invariant
        # in prose, which would otherwise false-positive here.
        assert "import redis" not in source and "app.redis" not in source, (
            f"{module.__name__} must never import or reference the Redis layer directly"
        )
        assert ".commit(" not in source, f"{module.__name__} must never commit a transaction directly"


def test_interview_service_is_the_sole_owner_of_commits():
    import inspect

    from app.services import interview_service

    source = inspect.getsource(interview_service)
    # Every public lifecycle method commits exactly once on its success
    # path — the workflow itself performs zero commits (see the test
    # above), so this is where durable mutation is actually applied.
    assert source.count("self._db.commit()") >= 4


# ---------------------------------------------------------------------------
# Task 20 — RAG grounding through the full HTTP stack
# ---------------------------------------------------------------------------


def test_start_interview_end_to_end_is_grounded_with_retrieved_knowledge():
    from app.knowledge.models import KnowledgeChunk
    from app.knowledge.retrieval_service import KnowledgeRetrievalService
    from tests.fakes import FakeEmbeddingProvider, FakeKnowledgeStore

    fake_redis = FakeAsyncRedis()
    fake_llm = FakeLLMProvider(
        structured_responses={"GeneratedQuestion": initial_question(InterviewTopic.RAG, "Generated by the graph.")}
    )
    embedding_provider = FakeEmbeddingProvider(dimension=8)
    store = FakeKnowledgeStore()
    chunk = KnowledgeChunk(
        role=Role.AI_ENGINEER,
        topic=InterviewTopic.RAG,
        concept="retrieval",
        content="RAG fetches relevant context before generation.",
    )
    knowledge_service = KnowledgeRetrievalService(embedding_provider=embedding_provider, store=store)

    async def _seed():
        vector = await embedding_provider.embed(chunk.content)
        await store.upsert([chunk], [vector])

    asyncio.run(_seed())

    with build_client(fake_redis, fake_llm, knowledge_service) as (client, _):
        created = create_interview(client, topics=["RAG", "AI_AGENTS"])
        started = start_interview(client, created["id"])

        assert started["question"]["topic"] == "RAG"
        # The retrieved chunk actually reached the question-generation prompt.
        schema, messages = fake_llm.calls[-1]
        assert schema == "GeneratedQuestion"
        prompt = " ".join(m.content for m in messages)
        assert chunk.content in prompt


def test_answer_endpoint_never_exposes_knowledge_store_failure_details():
    from app.knowledge.exceptions import KnowledgeStoreUnavailableError
    from app.knowledge.retrieval_service import KnowledgeRetrievalService
    from tests.fakes import FakeEmbeddingProvider, FakeKnowledgeStore

    fake_redis = FakeAsyncRedis()
    fake_llm = FakeLLMProvider(
        structured_responses={
            "GeneratedQuestion": initial_question(InterviewTopic.RAG),
            "AnswerAnalysis": analysis(needs_follow_up=True),
            "NextAction": NextAction(
                action="FOLLOW_UP", topic=InterviewTopic.RAG, difficulty=Difficulty.MEDIUM, rationale="Keep going."
            ),
        }
    )
    failing_store = FakeKnowledgeStore(error=KnowledgeStoreUnavailableError("simulated Qdrant outage detail"))
    knowledge_service = KnowledgeRetrievalService(embedding_provider=FakeEmbeddingProvider(), store=failing_store)

    with build_client(fake_redis, fake_llm, knowledge_service) as (client, _):
        created = create_interview(client, topics=["RAG", "AI_AGENTS"])
        started = start_interview(client, created["id"])

        response = submit_answer(
            client, created["id"], started["question"]["id"], "An answer.", "grounded-fallback-key"
        )

        # The knowledge-store outage degrades to ungrounded generation —
        # the request still succeeds, and no infrastructure detail leaks.
        assert response.status_code == 200
        assert "qdrant" not in response.text.lower()
        assert "outage" not in response.text.lower()
