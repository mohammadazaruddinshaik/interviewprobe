"""Task 21 — `GET /api/v1/interviews/{session_id}/evaluation` through the
full HTTP stack: LLM-failure -> stable API error mapping, and concurrent
evaluation requests producing exactly one persisted evaluation.

Reuses `build_client` from tests/test_workflow_integration.py (Task 18's
FastAPI dependency-override harness) rather than duplicating it.
"""

import concurrent.futures
import uuid

import pytest
from sqlalchemy import select

from app.domain.enums import Difficulty, InterviewTopic, QuestionType
from app.evaluation.models import EvaluationResult
from app.llm.exceptions import (
    LLMConfigurationError,
    LLMError,
    LLMInvalidResponseError,
    LLMProviderUnavailableError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from app.models.evaluation import Evaluation
from app.workflows.interview.models import AnswerAnalysis, GeneratedQuestion, NextAction
from tests.fakes import FakeAsyncRedis, FakeLLMProvider
from tests.test_workflow_integration import build_client, create_interview, start_interview, submit_answer


def default_evaluation_result() -> EvaluationResult:
    return EvaluationResult(
        technical_knowledge_score=7.0,
        reasoning_score=6.0,
        depth_score=5.0,
        communication_score=8.0,
        overall_score=1.0,
        strengths=["Explained retrieval clearly."],
        weaknesses=["Limited depth."],
        evidence=[],
    )


def _fake_llm_that_completes_and_evaluates(evaluation_result: EvaluationResult) -> FakeLLMProvider:
    """Drives an interview to COMPLETED (FOLLOW_UP throughout) and then
    serves `evaluation_result` for the evaluation call. For the LLM-
    failure tests below, a *separate* failing `FakeLLMProvider` (an
    `error=` makes every call raise, so it can't also drive completion)
    is swapped in only for the evaluation request itself, after the
    interview is already COMPLETED and persisted.
    """
    return FakeLLMProvider(
        structured_responses={
            "GeneratedQuestion": GeneratedQuestion(
                question="Tell me more.",
                topic=InterviewTopic.DATABASES,
                difficulty=Difficulty.MEDIUM,
                question_type=QuestionType.FOLLOW_UP,
            ),
            "AnswerAnalysis": AnswerAnalysis(
                understanding="BASIC", correctness=0.5, depth=0.4, concepts_demonstrated=[],
                concepts_missing=[], reasoning_quality="MODERATE", needs_follow_up=True,
            ),
            "NextAction": NextAction(
                action="FOLLOW_UP", topic=InterviewTopic.DATABASES, difficulty=Difficulty.MEDIUM, rationale="x"
            ),
            "EvaluationResult": evaluation_result,
        }
    )


def _complete_interview(client, question_limit: int = 3) -> dict:
    created = create_interview(client, role="BACKEND_DEVELOPER", topics=["DATABASES"], question_limit=question_limit)
    started = start_interview(client, created["id"])
    question_id = started["question"]["id"]
    data = None
    for i in range(question_limit):
        response = submit_answer(client, created["id"], question_id, f"answer {i}", f"eval-complete-{i}")
        data = response.json()["data"]
        if data["question"] is not None:
            question_id = data["question"]["id"]
    assert data["status"] == "COMPLETED"
    return created


@pytest.mark.parametrize(
    "error,expected_status,expected_code",
    [
        (LLMTimeoutError("simulated"), 504, "AI_SERVICE_TIMEOUT"),
        (LLMRateLimitError("simulated"), 429, "AI_SERVICE_RATE_LIMITED"),
        (LLMProviderUnavailableError("simulated"), 503, "AI_SERVICE_UNAVAILABLE"),
        (LLMInvalidResponseError("simulated"), 502, "AI_SERVICE_INVALID_RESPONSE"),
        (LLMConfigurationError("simulated"), 500, "AI_SERVICE_MISCONFIGURED"),
        # Task 29: the generic/catch-all LLMError mapping was previously
        # untested end-to-end anywhere in the suite — every LLMError
        # subclass not individually registered in main.py falls back to
        # this one (502, AI_SERVICE_ERROR).
        (LLMError("simulated"), 502, "AI_SERVICE_ERROR"),
    ],
)
def test_llm_failure_during_evaluation_maps_to_the_stable_api_error(error, expected_status, expected_code):
    fake_redis = FakeAsyncRedis()
    completing_llm = _fake_llm_that_completes_and_evaluates(default_evaluation_result())

    with build_client(fake_redis, completing_llm) as (client, session_factory):
        created = _complete_interview(client)

        # Swap in a failing provider only for the evaluation call itself —
        # the interview is already COMPLETED and persisted by this point.
        from app.api.deps import get_llm_provider
        from app.main import app

        app.dependency_overrides[get_llm_provider] = lambda: FakeLLMProvider(error=error)

        response = client.get(f"/api/v1/interviews/{created['id']}/evaluation")

        assert response.status_code == expected_status
        body = response.json()
        assert body["error"]["code"] == expected_code
        assert "simulated" not in body["error"]["message"]  # str(exc) never leaks

        # Nothing was persisted.
        db = session_factory()
        try:
            rows = db.execute(select(Evaluation).where(Evaluation.session_id == uuid.UUID(created["id"]))).scalars().all()
            assert rows == []
        finally:
            db.close()


def test_evaluation_success_response_never_exposes_internal_fields():
    fake_redis = FakeAsyncRedis()
    fake_llm = _fake_llm_that_completes_and_evaluates(default_evaluation_result())

    with build_client(fake_redis, fake_llm) as (client, _):
        created = _complete_interview(client)

        response = client.get(f"/api/v1/interviews/{created['id']}/evaluation")

        assert response.status_code == 200
        data = response.json()["data"]
        assert set(data.keys()) == {
            "session_id",
            "technical_knowledge_score",
            "reasoning_score",
            "depth_score",
            "communication_score",
            "overall_score",
            "strengths",
            "weaknesses",
            "evidence",
        }


# ---------------------------------------------------------------------------
# Concurrency — Task 53: at most one evaluation LLM call/row, the rest see
# a stable 409 EVALUATION_BUSY rather than silently duplicating the call
# ---------------------------------------------------------------------------


def test_concurrent_evaluation_requests_persist_exactly_one_evaluation():
    fake_redis = FakeAsyncRedis()
    fake_llm = _fake_llm_that_completes_and_evaluates(default_evaluation_result())

    with build_client(fake_redis, fake_llm) as (client, session_factory):
        created = _complete_interview(client)

        def request_evaluation():
            return client.get(f"/api/v1/interviews/{created['id']}/evaluation")

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(request_evaluation) for _ in range(4)]
            responses = [f.result() for f in futures]

        # Task 53: only the request that wins the evaluation-generation
        # lock gets a 200 on the first attempt — the rest see the stable
        # 409 EVALUATION_BUSY conflict response rather than blocking or
        # each independently paying for their own LLM call. At least one
        # request must still succeed (the lock winner).
        statuses = [r.status_code for r in responses]
        assert statuses.count(200) >= 1
        assert all(status in (200, 409) for status in statuses)
        for response in responses:
            if response.status_code == 409:
                assert response.json()["error"]["code"] == "EVALUATION_BUSY"

        bodies = [r.json()["data"] for r in responses if r.status_code == 200]
        # Every successful concurrent request observes the same, single
        # evaluation.
        session_ids = {b["session_id"] for b in bodies}
        overall_scores = {b["overall_score"] for b in bodies}
        assert len(session_ids) == 1
        assert len(overall_scores) == 1

        # The most important guarantee (Task 53): the expensive LLM call
        # itself happened exactly once for the evaluation, never once per
        # concurrent request — not merely that one row landed in the DB.
        evaluation_calls = [call for call in fake_llm.calls if call[0] == "EvaluationResult"]
        assert len(evaluation_calls) == 1

        db = session_factory()
        try:
            rows = (
                db.execute(select(Evaluation).where(Evaluation.session_id == uuid.UUID(created["id"])))
                .scalars()
                .all()
            )
            assert len(rows) == 1
        finally:
            db.close()


def test_a_losing_concurrent_request_can_retry_and_receive_the_evaluation():
    """A 409 EVALUATION_BUSY is not a dead end: once the winner's
    generation finishes (lock released, evaluation persisted), a retried
    request finds it via the plain, unlocked first check — no new LLM
    call, no busy error."""
    fake_redis = FakeAsyncRedis()
    fake_llm = _fake_llm_that_completes_and_evaluates(default_evaluation_result())

    with build_client(fake_redis, fake_llm) as (client, _):
        created = _complete_interview(client)

        first = client.get(f"/api/v1/interviews/{created['id']}/evaluation")
        assert first.status_code == 200

        retry = client.get(f"/api/v1/interviews/{created['id']}/evaluation")
        assert retry.status_code == 200
        assert retry.json()["data"] == first.json()["data"]

        evaluation_calls = [call for call in fake_llm.calls if call[0] == "EvaluationResult"]
        assert len(evaluation_calls) == 1
