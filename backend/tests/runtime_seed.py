"""Test helpers separating the PUBLIC create contract from the INTERNAL runtime session contract.

Public: `POST /interviews` / `InterviewService.create_interview(role)` take only a role and produce a CREATED
session with no topics. Internally, a started interview runs on planner-owned runtime state: the session's
`difficulty` / `question_limit` and its `interview_topics` rows. At start the planner (via `_materialize_plan_topics`,
and from Task 3 the session fields too) produces that state. Many tests exercise the *runtime* (adaptive workflow,
evaluation, results, deadlines) with no planner configured, so they seed that state directly here — standing in for
what the planner would have written — instead of pretending the candidate chose it."""

import uuid

from fastapi.testclient import TestClient

from app.db.session import get_db
from app.domain.enums import Difficulty, InterviewTopic, InterviewTopicStatus, Role
from app.main import app
from app.models.interview_session import InterviewSession
from app.models.interview_topic import InterviewTopicEntry
from app.repositories.interview_repository import InterviewRepository
from app.services.interview_service import InterviewService


def seed_runtime_state(
    repository: InterviewRepository,
    session: InterviewSession,
    *,
    difficulty: Difficulty = Difficulty.MEDIUM,
    question_limit: int = 5,
    topics: list[InterviewTopic] | None = None,
) -> InterviewSession:
    """Write planner-owned runtime state onto a CREATED session and commit."""
    session.difficulty = difficulty
    session.question_limit = question_limit
    repository.delete_topics(session.id)
    repository.create_topics(
        [
            InterviewTopicEntry(
                session_id=session.id, topic=topic, sequence_number=n, status=InterviewTopicStatus.PENDING
            )
            for n, topic in enumerate(topics or [], start=1)
        ]
    )
    repository.session.commit()
    return session


def create_runtime_session(
    service: InterviewService,
    role: Role = Role.AI_ENGINEER,
    difficulty: Difficulty = Difficulty.MEDIUM,
    question_limit: int = 5,
    topics: list[InterviewTopic] | None = None,
) -> InterviewSession:
    """`service.create_interview(role)` followed by seeding the runtime state a planner would provide."""
    session = service.create_interview(role=role)
    return seed_runtime_state(
        service.repository, session, difficulty=difficulty, question_limit=question_limit, topics=topics
    )


def create_api_interview(
    client: TestClient,
    role: str = "AI_ENGINEER",
    difficulty: str = "MEDIUM",
    topics: list[str] | None = None,
    question_limit: int = 5,
    **post_kwargs,
) -> dict:
    """POST /interviews with only a role, then seed runtime state through the app's overridden DB dependency.
    Returns the create response data updated with the seeded runtime values (for tests that assert on them)."""
    response = client.post("/api/v1/interviews", json={"role": role}, **post_kwargs)
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    seed_runtime_via_app_db(
        uuid.UUID(data["id"]),
        difficulty=Difficulty(difficulty),
        question_limit=question_limit,
        topics=[InterviewTopic(t) for t in (topics or ["RAG", "AI_AGENTS"])],
    )
    return data | {"difficulty": difficulty, "topics": topics or ["RAG", "AI_AGENTS"], "question_limit": question_limit}


def seed_runtime_via_app_db(session_id: uuid.UUID, **state) -> None:
    generator = app.dependency_overrides[get_db]()
    db = next(generator)
    try:
        repository = InterviewRepository(db)
        seed_runtime_state(repository, repository.get_session(session_id), **state)
    finally:
        generator.close()
