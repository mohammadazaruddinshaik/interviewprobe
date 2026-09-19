"""Task 22 — `GET /api/v1/interviews/{session_id}/result` through the full
HTTP stack: state validation, data exposure, LLM-failure mapping,
idempotency, and concurrency.

Reuses `build_client` from tests/test_workflow_integration.py (Task 18's
FastAPI dependency-override harness) rather than duplicating it.
"""

import concurrent.futures
import uuid

import pytest
from sqlalchemy import select

from app.domain.enums import Difficulty, InterviewTopic, QuestionType
from app.evaluation.models import EvaluationResult
from app.llm.exceptions import LLMInvalidResponseError, LLMTimeoutError
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


def fake_llm_that_completes_and_evaluates(evaluation_result: EvaluationResult) -> FakeLLMProvider:
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
        response = submit_answer(client, created["id"], question_id, f"answer {i}", f"result-complete-{i}")
        data = response.json()["data"]
        if data["question"] is not None:
            question_id = data["question"]["id"]
    assert data["status"] == "COMPLETED"
    return created


# ---------------------------------------------------------------------------
# Endpoint behavior
# ---------------------------------------------------------------------------


def test_completed_interview_returns_200():
    fake_redis = FakeAsyncRedis()
    fake_llm = fake_llm_that_completes_and_evaluates(default_evaluation_result())

    with build_client(fake_redis, fake_llm) as (client, _):
        created = _complete_interview(client)

        response = client.get(f"/api/v1/interviews/{created['id']}/result")

        assert response.status_code == 200


def test_unknown_interview_returns_404():
    fake_redis = FakeAsyncRedis()
    fake_llm = fake_llm_that_completes_and_evaluates(default_evaluation_result())

    with build_client(fake_redis, fake_llm) as (client, _):
        response = client.get(f"/api/v1/interviews/{uuid.uuid4()}/result")

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "INTERVIEW_NOT_FOUND"


def test_created_interview_returns_409():
    fake_redis = FakeAsyncRedis()
    fake_llm = fake_llm_that_completes_and_evaluates(default_evaluation_result())

    with build_client(fake_redis, fake_llm) as (client, _):
        created = create_interview(client, role="BACKEND_DEVELOPER", topics=["DATABASES"])

        response = client.get(f"/api/v1/interviews/{created['id']}/result")

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "INVALID_INTERVIEW_STATE"


def test_in_progress_interview_returns_409():
    fake_redis = FakeAsyncRedis()
    fake_llm = fake_llm_that_completes_and_evaluates(default_evaluation_result())

    with build_client(fake_redis, fake_llm) as (client, _):
        created = create_interview(client, role="BACKEND_DEVELOPER", topics=["DATABASES"])
        start_interview(client, created["id"])

        response = client.get(f"/api/v1/interviews/{created['id']}/result")

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "INVALID_INTERVIEW_STATE"


# ---------------------------------------------------------------------------
# Result assembly / data exposure
# ---------------------------------------------------------------------------


def test_result_envelope_and_shape():
    fake_redis = FakeAsyncRedis()
    fake_llm = fake_llm_that_completes_and_evaluates(default_evaluation_result())

    with build_client(fake_redis, fake_llm) as (client, _):
        created = _complete_interview(client)

        response = client.get(f"/api/v1/interviews/{created['id']}/result")

        body = response.json()
        assert set(body.keys()) == {"data"}
        data = body["data"]
        assert set(data.keys()) == {"interview", "topics", "questions", "evaluation"}


def test_interview_metadata_fields():
    fake_redis = FakeAsyncRedis()
    fake_llm = fake_llm_that_completes_and_evaluates(default_evaluation_result())

    with build_client(fake_redis, fake_llm) as (client, _):
        created = _complete_interview(client, question_limit=3)

        data = client.get(f"/api/v1/interviews/{created['id']}/result").json()["data"]

        interview = data["interview"]
        assert interview["session_id"] == created["id"]
        assert interview["role"] == "BACKEND_DEVELOPER"
        assert interview["difficulty"] == "MEDIUM"
        assert interview["status"] == "COMPLETED"
        assert interview["question_limit"] == 3
        assert interview["started_at"] is not None
        assert interview["completed_at"] is not None
        assert interview["created_at"] is not None


def test_topics_and_questions_are_in_persisted_sequence_order():
    fake_redis = FakeAsyncRedis()
    fake_llm = fake_llm_that_completes_and_evaluates(default_evaluation_result())

    with build_client(fake_redis, fake_llm) as (client, _):
        created = _complete_interview(client, question_limit=3)

        data = client.get(f"/api/v1/interviews/{created['id']}/result").json()["data"]

        assert [t["sequence_number"] for t in data["topics"]] == list(range(1, len(data["topics"]) + 1))
        assert [q["sequence"] for q in data["questions"]] == [1, 2, 3]
        assert [q["candidate_answer"] for q in data["questions"]] == ["answer 0", "answer 1", "answer 2"]


def test_missing_answer_is_represented_as_null():
    fake_redis = FakeAsyncRedis()
    fake_llm = fake_llm_that_completes_and_evaluates(default_evaluation_result())

    with build_client(fake_redis, fake_llm) as (client, _):
        created = create_interview(client, role="BACKEND_DEVELOPER", topics=["DATABASES"])
        start_interview(client, created["id"])
        client.post(f"/api/v1/interviews/{created['id']}/complete")  # completed without answering

        data = client.get(f"/api/v1/interviews/{created['id']}/result").json()["data"]

        assert len(data["questions"]) == 1
        assert data["questions"][0]["candidate_answer"] is None


def test_question_fields_present_and_agent_reason_never_exposed():
    fake_redis = FakeAsyncRedis()
    fake_llm = fake_llm_that_completes_and_evaluates(default_evaluation_result())

    with build_client(fake_redis, fake_llm) as (client, _):
        created = _complete_interview(client)

        response = client.get(f"/api/v1/interviews/{created['id']}/result")
        data = response.json()["data"]

        for question in data["questions"]:
            assert set(question.keys()) == {"id", "sequence", "text", "topic", "difficulty", "type", "candidate_answer"}
        assert "agent_reason" not in response.text


def test_evaluation_fields_and_evidence_returned():
    fake_redis = FakeAsyncRedis()
    evaluation_result_with_evidence = EvaluationResult(
        technical_knowledge_score=7.0, reasoning_score=6.0, depth_score=5.0, communication_score=8.0,
        overall_score=1.0, strengths=["s1"], weaknesses=["w1"],
        evidence=[{"claim": "c1", "evidence": "e1"}],
    )
    fake_llm = fake_llm_that_completes_and_evaluates(evaluation_result_with_evidence)

    with build_client(fake_redis, fake_llm) as (client, _):
        created = _complete_interview(client)

        data = client.get(f"/api/v1/interviews/{created['id']}/result").json()["data"]

        evaluation = data["evaluation"]
        for field in (
            "technical_knowledge_score", "reasoning_score", "depth_score", "communication_score", "overall_score",
        ):
            assert 0.0 <= evaluation[field] <= 10.0
        assert evaluation["strengths"] == ["s1"]
        assert evaluation["weaknesses"] == ["w1"]
        assert evaluation["evidence"] == [{"claim": "c1", "evidence": "e1"}]
        # overall_score is backend-computed, never the LLM's 1.0.
        assert evaluation["overall_score"] == 6.5


def test_no_sensitive_internal_data_in_response():
    fake_redis = FakeAsyncRedis()
    fake_llm = fake_llm_that_completes_and_evaluates(default_evaluation_result())

    with build_client(fake_redis, fake_llm) as (client, _):
        created = _complete_interview(client)

        response = client.get(f"/api/v1/interviews/{created['id']}/result")

        for forbidden in ("api_key", "prompt", "rationale", "redis", "lock", "idempotency", "qdrant", "embedding"):
            assert forbidden not in response.text.lower()


# ---------------------------------------------------------------------------
# Evaluation integration / idempotency
# ---------------------------------------------------------------------------


def test_result_triggers_exactly_one_evaluation_generation():
    fake_redis = FakeAsyncRedis()
    fake_llm = fake_llm_that_completes_and_evaluates(default_evaluation_result())

    with build_client(fake_redis, fake_llm) as (client, _):
        created = _complete_interview(client)

        client.get(f"/api/v1/interviews/{created['id']}/result")

        assert len([c for c in fake_llm.calls if c[0] == "EvaluationResult"]) == 1


def test_repeated_result_requests_are_deterministic_and_do_not_call_the_llm_again():
    fake_redis = FakeAsyncRedis()
    fake_llm = fake_llm_that_completes_and_evaluates(default_evaluation_result())

    with build_client(fake_redis, fake_llm) as (client, _):
        created = _complete_interview(client)

        first = client.get(f"/api/v1/interviews/{created['id']}/result")
        second = client.get(f"/api/v1/interviews/{created['id']}/result")
        third = client.get(f"/api/v1/interviews/{created['id']}/result")

        assert first.json() == second.json() == third.json()
        assert len([c for c in fake_llm.calls if c[0] == "EvaluationResult"]) == 1


def test_result_does_not_change_interview_status_or_topics():
    fake_redis = FakeAsyncRedis()
    fake_llm = fake_llm_that_completes_and_evaluates(default_evaluation_result())

    with build_client(fake_redis, fake_llm) as (client, _):
        created = _complete_interview(client)
        topics_before = client.get(f"/api/v1/interviews/{created['id']}").json()["data"]["topics"]

        client.get(f"/api/v1/interviews/{created['id']}/result")

        state = client.get(f"/api/v1/interviews/{created['id']}").json()["data"]
        assert state["status"] == "COMPLETED"
        assert state["topics"] == topics_before


# ---------------------------------------------------------------------------
# Error handling — LLM failures never leak raw exception text or produce a
# partial result
# ---------------------------------------------------------------------------


def test_llm_timeout_during_result_maps_to_stable_error_and_persists_nothing():
    fake_redis = FakeAsyncRedis()
    completing_llm = fake_llm_that_completes_and_evaluates(default_evaluation_result())

    with build_client(fake_redis, completing_llm) as (client, session_factory):
        created = _complete_interview(client)

        from app.api.deps import get_llm_provider
        from app.main import app

        app.dependency_overrides[get_llm_provider] = lambda: FakeLLMProvider(error=LLMTimeoutError("simulated"))

        response = client.get(f"/api/v1/interviews/{created['id']}/result")

        assert response.status_code == 504
        body = response.json()
        assert body["error"]["code"] == "AI_SERVICE_TIMEOUT"
        assert "simulated" not in body["error"]["message"]
        assert "data" not in body  # never a partial result alongside an error

        db = session_factory()
        try:
            rows = db.execute(select(Evaluation).where(Evaluation.session_id == uuid.UUID(created["id"]))).scalars().all()
            assert rows == []
        finally:
            db.close()


def test_malformed_evaluation_output_does_not_produce_a_partial_result():
    fake_redis = FakeAsyncRedis()
    completing_llm = fake_llm_that_completes_and_evaluates(default_evaluation_result())

    with build_client(fake_redis, completing_llm) as (client, session_factory):
        created = _complete_interview(client)

        bad_result = EvaluationResult.model_construct(
            technical_knowledge_score=999.0,
            reasoning_score=5.0,
            depth_score=5.0,
            communication_score=5.0,
            overall_score=5.0,
            strengths=[],
            weaknesses=[],
            evidence=[],
        )
        from app.api.deps import get_llm_provider
        from app.main import app

        app.dependency_overrides[get_llm_provider] = lambda: FakeLLMProvider(
            structured_responses={"EvaluationResult": bad_result}
        )

        response = client.get(f"/api/v1/interviews/{created['id']}/result")

        assert response.status_code == 502
        assert response.json()["error"]["code"] == "AI_SERVICE_INVALID_RESPONSE"

        db = session_factory()
        try:
            rows = db.execute(select(Evaluation).where(Evaluation.session_id == uuid.UUID(created["id"]))).scalars().all()
            assert rows == []
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------


def test_concurrent_result_requests_persist_exactly_one_evaluation():
    fake_redis = FakeAsyncRedis()
    fake_llm = fake_llm_that_completes_and_evaluates(default_evaluation_result())

    with build_client(fake_redis, fake_llm) as (client, session_factory):
        created = _complete_interview(client)

        def request_result():
            return client.get(f"/api/v1/interviews/{created['id']}/result")

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(request_result) for _ in range(4)]
            responses = [f.result() for f in futures]

        assert all(r.status_code == 200 for r in responses)
        overall_scores = {r.json()["data"]["evaluation"]["overall_score"] for r in responses}
        assert len(overall_scores) == 1

        db = session_factory()
        try:
            rows = db.execute(select(Evaluation).where(Evaluation.session_id == uuid.UUID(created["id"]))).scalars().all()
            assert len(rows) == 1
        finally:
            db.close()
