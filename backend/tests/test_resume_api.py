"""`POST /api/v1/interviews/{session_id}/resume` through the full HTTP
stack — reuses `build_client`/`create_interview` from
tests/test_workflow_integration.py (Task 18's FastAPI dependency-override
harness), the same pattern tests/test_evaluation_api.py uses.
"""

import uuid

from app.core.config import settings
from app.domain.enums import Difficulty, InterviewTopic, QuestionType
from app.models.interview_resume import InterviewResume
from app.resume.models import ResumeCandidateInfo, ResumeProfile
from app.workflows.interview.models import AnswerAnalysis, GeneratedQuestion, NextAction
from tests.fakes import FakeAsyncRedis, FakeLLMProvider, make_test_docx_bytes, make_test_pdf_bytes
from tests.test_workflow_integration import build_client, create_interview, start_interview, submit_answer


def _default_resume_profile() -> ResumeProfile:
    return ResumeProfile(candidate=ResumeCandidateInfo(name="Jane Doe"), skills=["Python"])


def _llm_with_resume_profile(profile: ResumeProfile | None = None) -> FakeLLMProvider:
    """For tests that only ever call the resume endpoint — never
    start/answers, so no interview-workflow structured responses are
    configured."""
    return FakeLLMProvider(structured_responses={"ResumeProfile": profile or _default_resume_profile()})


def _llm_full(profile: ResumeProfile | None = None) -> FakeLLMProvider:
    """For tests that both progress the interview (start/submit, which
    need GeneratedQuestion/AnswerAnalysis/NextAction) AND upload a resume
    — mirrors test_interview_api.py's default_fake_llm_provider, plus a
    configured ResumeProfile."""
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
            "ResumeProfile": profile or _default_resume_profile(),
        }
    )


def upload_pdf(client, session_id: str, data: bytes | None = None, filename: str = "resume.pdf"):
    return client.post(
        f"/api/v1/interviews/{session_id}/resume",
        files={"resume": (filename, data or make_test_pdf_bytes("Jane Doe, Senior Engineer"), "application/pdf")},
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_uploading_a_valid_pdf_returns_ready_status_and_safe_metadata():
    with build_client(FakeAsyncRedis(), _llm_with_resume_profile()) as (client, _):
        created = create_interview(client)

        response = upload_pdf(client, created["id"])

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["status"] == "READY"
        assert data["original_filename"] == "resume.pdf"
        assert data["content_type"] == "application/pdf"
        assert data["file_size"] > 0
        assert data["extraction_error"] is None


def test_uploading_a_valid_docx_returns_ready_status():
    with build_client(FakeAsyncRedis(), _llm_with_resume_profile()) as (client, _):
        created = create_interview(client)

        response = client.post(
            f"/api/v1/interviews/{created['id']}/resume",
            files={
                "resume": (
                    "resume.docx",
                    make_test_docx_bytes("Jane Doe, Senior Engineer"),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )

        assert response.status_code == 200
        assert response.json()["data"]["status"] == "READY"


def test_success_response_never_exposes_extracted_text_or_structured_profile():
    with build_client(FakeAsyncRedis(), _llm_with_resume_profile()) as (client, _):
        created = create_interview(client)

        response = upload_pdf(client, created["id"])

        data = response.json()["data"]
        assert set(data.keys()) == {
            "session_id",
            "original_filename",
            "content_type",
            "file_size",
            "status",
            "extraction_error",
        }


def test_upload_works_while_interview_is_in_progress():
    with build_client(FakeAsyncRedis(), _llm_full()) as (client, _):
        created = create_interview(client)
        start_interview(client, created["id"])

        response = upload_pdf(client, created["id"])

        assert response.status_code == 200
        assert response.json()["data"]["status"] == "READY"


# ---------------------------------------------------------------------------
# Request-level validation errors — clean 4xx envelope, no internals leaked
# ---------------------------------------------------------------------------


def test_unsupported_file_type_returns_422():
    with build_client(FakeAsyncRedis(), _llm_with_resume_profile()) as (client, _):
        created = create_interview(client)

        response = client.post(
            f"/api/v1/interviews/{created['id']}/resume",
            files={"resume": ("resume.txt", b"just plain text", "text/plain")},
        )

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "UNSUPPORTED_RESUME_FILE_TYPE"


def test_empty_file_returns_422():
    with build_client(FakeAsyncRedis(), _llm_with_resume_profile()) as (client, _):
        created = create_interview(client)

        response = client.post(
            f"/api/v1/interviews/{created['id']}/resume",
            files={"resume": ("resume.pdf", b"", "application/pdf")},
        )

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "EMPTY_RESUME_FILE"


def test_oversized_file_returns_413(monkeypatch):
    monkeypatch.setattr(settings, "resume_max_file_size_bytes", 10)
    with build_client(FakeAsyncRedis(), _llm_with_resume_profile()) as (client, _):
        created = create_interview(client)

        response = upload_pdf(client, created["id"])

        assert response.status_code == 413
        assert response.json()["error"]["code"] == "RESUME_FILE_TOO_LARGE"


def test_nonexistent_session_returns_404():
    with build_client(FakeAsyncRedis(), _llm_with_resume_profile()) as (client, _):
        response = upload_pdf(client, str(uuid.uuid4()))

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "INTERVIEW_NOT_FOUND"


def test_completed_session_returns_409():
    with build_client(FakeAsyncRedis(), _llm_full()) as (client, _):
        created = create_interview(client, question_limit=3)
        started = start_interview(client, created["id"])
        question_id = started["question"]["id"]
        for i in range(3):
            result = submit_answer(client, created["id"], question_id, f"answer {i}", f"resume-api-complete-{i}")
            data = result.json()["data"]
            if data["question"] is not None:
                question_id = data["question"]["id"]
        assert data["status"] == "COMPLETED"

        response = upload_pdf(client, created["id"])

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "INVALID_INTERVIEW_STATE"


# ---------------------------------------------------------------------------
# Processing failures — a normal 200, never a 5xx
# ---------------------------------------------------------------------------


def test_unreadable_scanned_pdf_returns_200_with_failed_status():
    from tests.fakes import make_test_pdf_with_no_text_bytes

    with build_client(FakeAsyncRedis(), _llm_with_resume_profile()) as (client, _):
        created = create_interview(client)

        response = upload_pdf(client, created["id"], data=make_test_pdf_with_no_text_bytes())

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["status"] == "FAILED"
        assert data["extraction_error"]


def test_llm_failure_returns_200_with_failed_status_never_a_5xx():
    from app.llm.exceptions import LLMTimeoutError

    with build_client(FakeAsyncRedis(), FakeLLMProvider(error=LLMTimeoutError("simulated"))) as (client, _):
        created = create_interview(client)

        response = upload_pdf(client, created["id"])

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["status"] == "FAILED"
        assert "simulated" not in data["extraction_error"]


# ---------------------------------------------------------------------------
# Duplicate upload / replace
# ---------------------------------------------------------------------------


def test_reuploading_replaces_the_resume_and_persists_exactly_one_row():
    with build_client(FakeAsyncRedis(), _llm_with_resume_profile()) as (client, session_factory):
        created = create_interview(client)

        first = upload_pdf(client, created["id"], filename="first.pdf")
        second = upload_pdf(client, created["id"], filename="second.pdf")

        assert first.status_code == 200
        assert second.status_code == 200
        assert second.json()["data"]["original_filename"] == "second.pdf"

        db = session_factory()
        try:
            from sqlalchemy import select

            rows = (
                db.execute(select(InterviewResume).where(InterviewResume.session_id == uuid.UUID(created["id"])))
                .scalars()
                .all()
            )
            assert len(rows) == 1
            assert rows[0].original_filename == "second.pdf"
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Skip flow — the rest of the interview is unaffected by never uploading
# ---------------------------------------------------------------------------


def test_interview_starts_and_completes_normally_when_no_resume_is_ever_uploaded():
    with build_client(FakeAsyncRedis(), _llm_full()) as (client, session_factory):
        created = create_interview(client, question_limit=3)
        started = start_interview(client, created["id"])
        question_id = started["question"]["id"]
        response = None
        for i in range(3):
            response = submit_answer(
                client, created["id"], question_id, f"answer {i}", f"resume-skip-flow-{i}"
            )
            data = response.json()["data"]
            if data["question"] is not None:
                question_id = data["question"]["id"]

        assert response.status_code == 200
        assert response.json()["data"]["status"] == "COMPLETED"

        db = session_factory()
        try:
            from sqlalchemy import select

            rows = (
                db.execute(select(InterviewResume).where(InterviewResume.session_id == uuid.UUID(created["id"])))
                .scalars()
                .all()
            )
            assert rows == []
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Error envelope shape (matches every other endpoint in this project)
# ---------------------------------------------------------------------------


def test_error_responses_use_the_standard_error_envelope():
    with build_client(FakeAsyncRedis(), _llm_with_resume_profile()) as (client, _):
        created = create_interview(client)

        response = client.post(
            f"/api/v1/interviews/{created['id']}/resume",
            files={"resume": ("resume.txt", b"plain text", "text/plain")},
        )

        body = response.json()
        assert set(body.keys()) == {"error"}
        assert set(body["error"].keys()) == {"code", "message"}
