"""Tests for InterviewPlan persistence (interview_plans table).

Uses the same in-memory SQLite fixture pattern as test_interview_repository.py.
Repository only flushes; transaction ownership is the caller's.
"""

import uuid

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, event
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.domain.enums import (
    Difficulty,
    InterviewStatus,
    InterviewTopic,
    PlannedTopicPriority,
    ResumeRelevance,
    Role,
)
from app.models.interview_plan import InterviewPlanRecord
from app.models.interview_session import InterviewSession
from app.planning.models import InterviewPlan, PlannedTopic, identify_resume_claims
from app.repositories.interview_repository import InterviewRepository
from app.resume.models import ResumeClaim


# ---------------------------------------------------------------------------
# SQLite dialect hooks (same as test_interview_repository.py)
# ---------------------------------------------------------------------------

@compiles(UUID, "sqlite")
def _compile_uuid_sqlite(element, compiler, **kw):
    return "CHAR(32)"


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(element, compiler, **kw):
    return "JSON"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # SQLite requires PRAGMA foreign_keys = ON to enforce ON DELETE CASCADE.
    @event.listens_for(engine, "connect")
    def _enable_fk(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    yield factory
    engine.dispose()


@pytest.fixture()
def db_session(session_factory) -> Session:
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def repository(db_session: Session) -> InterviewRepository:
    return InterviewRepository(db_session)


def _make_interview_session(role: Role = Role.AI_ENGINEER, **overrides) -> InterviewSession:
    defaults = {
        "role": role,
        "difficulty": Difficulty.MEDIUM,
        "status": InterviewStatus.CREATED,
        "question_limit": 5,
    }
    return InterviewSession(**(defaults | overrides))


RAG_CLAIM = ResumeClaim(claim="Built a RAG system using Qdrant", category="project", source="Projects")


def _plan(role: Role = Role.AI_ENGINEER, topics: list[PlannedTopic] | None = None) -> InterviewPlan:
    if topics is None:
        topics = [
            PlannedTopic(
                topic=InterviewTopic.LLM_FUNDAMENTALS,
                competency_keys=["llm_fundamentals"],
                priority=PlannedTopicPriority.HIGH,
                rationale="Core knowledge assessment.",
                suggested_time_budget_minutes=10,
            ),
            PlannedTopic(
                topic=InterviewTopic.RAG,
                competency_keys=["retrieval_augmented_generation"],
                priority=PlannedTopicPriority.MEDIUM,
                rationale="Key role competency.",
                suggested_time_budget_minutes=8,
            ),
        ]
    return InterviewPlan(
        role=role,
        objectives=["Assess core AI engineering competency."],
        planned_topics=topics,
    )


def _plan_with_claims(role: Role = Role.AI_ENGINEER) -> InterviewPlan:
    claims = identify_resume_claims([RAG_CLAIM])
    return InterviewPlan(
        role=role,
        objectives=["Probe candidate's reported RAG experience."],
        planned_topics=[
            PlannedTopic(
                topic=InterviewTopic.RAG,
                competency_keys=["retrieval_augmented_generation"],
                priority=PlannedTopicPriority.HIGH,
                rationale="Candidate claims RAG experience.",
                resume_relevance=ResumeRelevance.PRIMARY,
                related_claim_ids=[c.claim_id for c in claims],
                suggested_time_budget_minutes=12,
            ),
            PlannedTopic(
                topic=InterviewTopic.LLM_FUNDAMENTALS,
                competency_keys=["llm_fundamentals"],
                priority=PlannedTopicPriority.MEDIUM,
                rationale="Baseline knowledge.",
                suggested_time_budget_minutes=8,
            ),
        ],
    )


# ===================================================================
# Creation
# ===================================================================


class TestCreation:
    def test_valid_plan_persists(self, repository: InterviewRepository, db_session: Session):
        session = repository.create_session(_make_interview_session())
        plan = _plan()

        record = repository.create_plan(session.id, plan)
        db_session.commit()

        assert record.id is not None
        assert isinstance(record.id, uuid.UUID)

    def test_persisted_session_id_matches(self, repository: InterviewRepository, db_session: Session):
        session = repository.create_session(_make_interview_session())
        plan = _plan()

        record = repository.create_plan(session.id, plan)
        db_session.commit()

        assert record.session_id == session.id

    def test_persisted_role_matches_plan_role(self, repository: InterviewRepository, db_session: Session):
        session = repository.create_session(_make_interview_session())
        plan = _plan(Role.AI_ENGINEER)

        record = repository.create_plan(session.id, plan)
        db_session.commit()

        assert record.role is Role.AI_ENGINEER

    def test_plan_version_is_persisted(self, repository: InterviewRepository, db_session: Session):
        session = repository.create_session(_make_interview_session())
        plan = _plan()

        record = repository.create_plan(session.id, plan)
        db_session.commit()

        assert record.plan_version == 1

    def test_jsonb_contains_expected_domain_representation(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = repository.create_session(_make_interview_session())
        plan = _plan_with_claims()

        record = repository.create_plan(session.id, plan)
        db_session.commit()

        stored = record.plan
        assert stored["role"] == "AI_ENGINEER"
        assert stored["plan_version"] == 1
        assert len(stored["objectives"]) == 1
        assert len(stored["planned_topics"]) == 2

        rag_topic = next(t for t in stored["planned_topics"] if t["topic"] == "RAG")
        assert rag_topic["competency_keys"] == ["retrieval_augmented_generation"]
        assert rag_topic["resume_relevance"] == "PRIMARY"
        assert len(rag_topic["related_claim_ids"]) == 1
        assert rag_topic["related_claim_ids"][0].startswith("claim_")


# ===================================================================
# Retrieval
# ===================================================================


class TestRetrieval:
    def test_plan_can_be_loaded_by_session_id(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = repository.create_session(_make_interview_session())
        plan = _plan()
        repository.create_plan(session.id, plan)
        db_session.commit()

        record = repository.get_plan(session.id)

        assert record is not None
        assert record.session_id == session.id

    def test_plan_can_be_loaded_by_plan_id(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = repository.create_session(_make_interview_session())
        plan = _plan()
        created = repository.create_plan(session.id, plan)
        db_session.commit()

        record = repository.get_plan_by_id(created.id)

        assert record is not None
        assert record.id == created.id

    def test_loaded_plan_is_reconstructed_as_interview_plan(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = repository.create_session(_make_interview_session())
        plan = _plan()
        repository.create_plan(session.id, plan)
        db_session.commit()

        loaded = repository.load_plan(session.id)

        assert isinstance(loaded, InterviewPlan)
        assert not isinstance(loaded, dict)

    def test_loaded_plan_matches_original_domain_object(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = repository.create_session(_make_interview_session())
        original = _plan_with_claims()
        repository.create_plan(session.id, original)
        db_session.commit()

        loaded = repository.load_plan(session.id)

        assert loaded == original

    def test_load_plan_returns_none_when_no_plan_exists(
        self, repository: InterviewRepository
    ):
        assert repository.load_plan(uuid.uuid4()) is None

    def test_get_plan_returns_none_for_nonexistent_session(
        self, repository: InterviewRepository
    ):
        assert repository.get_plan(uuid.uuid4()) is None

    def test_get_plan_by_id_returns_none_for_nonexistent_id(
        self, repository: InterviewRepository
    ):
        assert repository.get_plan_by_id(uuid.uuid4()) is None


# ===================================================================
# Integrity
# ===================================================================


class TestIntegrity:
    def test_different_sessions_can_each_have_version_1(
        self, repository: InterviewRepository, db_session: Session
    ):
        s1 = repository.create_session(_make_interview_session())
        s2 = repository.create_session(_make_interview_session())
        plan = _plan()

        repository.create_plan(s1.id, plan)
        repository.create_plan(s2.id, plan)
        db_session.commit()

        assert repository.get_plan(s1.id).session_id == s1.id
        assert repository.get_plan(s2.id).session_id == s2.id

    def test_same_session_cannot_have_duplicate_version(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = repository.create_session(_make_interview_session())
        plan = _plan()

        repository.create_plan(session.id, plan)
        db_session.flush()

        with pytest.raises(Exception):
            repository.create_plan(session.id, plan)
            db_session.flush()

    def test_session_deletion_cascades_to_plan(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = repository.create_session(_make_interview_session())
        plan = _plan()
        created = repository.create_plan(session.id, plan)
        plan_id = created.id
        db_session.commit()

        db_session.delete(session)
        db_session.commit()

        assert repository.get_plan_by_id(plan_id) is None

    def test_corrupted_json_cannot_silently_load(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = repository.create_session(_make_interview_session())
        # Directly create a record with invalid JSONB (missing required fields)
        record = InterviewPlanRecord(
            session_id=session.id,
            plan_version=1,
            role=Role.AI_ENGINEER,
            plan={"role": "AI_ENGINEER", "planned_topics": []},
        )
        db_session.add(record)
        db_session.flush()
        db_session.commit()

        with pytest.raises(ValidationError):
            repository.load_plan(session.id)

    def test_stored_role_cannot_diverge_from_plan_role(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = repository.create_session(_make_interview_session())
        plan = _plan(Role.AI_ENGINEER)

        record = repository.create_plan(session.id, plan)
        db_session.commit()

        assert record.role is Role.AI_ENGINEER
        assert record.plan["role"] == "AI_ENGINEER"


# ===================================================================
# Transaction behavior
# ===================================================================


class TestLegacyPlans:
    """Plans persisted before `starting_difficulty` / `max_questions` existed must keep loading, untouched."""

    LEGACY = {
        "role": "AI_ENGINEER",
        "plan_version": 1,
        "objectives": ["Assess core AI engineering competency."],
        "planned_topics": [
            {
                "topic": "RAG",
                "competency_keys": ["retrieval_augmented_generation"],
                "priority": "HIGH",
                "rationale": "Key role competency.",
                "resume_relevance": "NONE",
                "related_claim_ids": [],
                "suggested_time_budget_minutes": 10,
            }
        ],
    }

    def test_legacy_plan_without_planner_decisions_loads(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = repository.create_session(_make_interview_session())
        db_session.add(
            InterviewPlanRecord(session_id=session.id, plan_version=1, role=Role.AI_ENGINEER, plan=dict(self.LEGACY))
        )
        db_session.commit()

        loaded = repository.load_plan(session.id)

        assert loaded is not None
        assert loaded.starting_difficulty is None
        assert loaded.max_questions is None
        assert loaded.planned_topics[0].topic is InterviewTopic.RAG

    def test_loading_a_legacy_plan_does_not_rewrite_the_stored_json(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = repository.create_session(_make_interview_session())
        db_session.add(
            InterviewPlanRecord(session_id=session.id, plan_version=1, role=Role.AI_ENGINEER, plan=dict(self.LEGACY))
        )
        db_session.commit()

        repository.load_plan(session.id)
        db_session.expire_all()

        assert repository.get_plan(session.id).plan == self.LEGACY

    def test_new_plan_persists_and_reloads_planner_decisions(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = repository.create_session(_make_interview_session())
        plan = _plan().model_copy(update={"starting_difficulty": Difficulty.HARD, "max_questions": 7})
        repository.create_plan(session.id, plan)
        db_session.commit()

        record = repository.get_plan(session.id)
        assert record.plan["starting_difficulty"] == "HARD"
        assert record.plan["max_questions"] == 7
        loaded = repository.load_plan(session.id)
        assert loaded.starting_difficulty is Difficulty.HARD
        assert loaded.max_questions == 7
        assert record.plan_version == 1  # version / uniqueness semantics unchanged


class TestTransactionBehavior:
    def test_repository_does_not_independently_commit(
        self, repository: InterviewRepository, db_session: Session
    ):
        """After create_plan, the row should be visible in the same
        session (flushed) but not yet committed. Rolling back should
        remove it."""
        session = repository.create_session(_make_interview_session())
        plan = _plan()

        repository.create_plan(session.id, plan)
        # Should be flushed (visible in this session) but not committed
        assert repository.get_plan(session.id) is not None

        db_session.rollback()

        assert repository.get_plan(session.id) is None

    def test_rollback_prevents_partial_persistence(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = repository.create_session(_make_interview_session())
        plan = _plan()

        repository.create_plan(session.id, plan)
        db_session.rollback()

        # Both the session and plan should be gone
        assert repository.get_session(session.id) is None
        assert repository.get_plan(session.id) is None


# ===================================================================
# Versioning
# ===================================================================


class TestVersioning:
    def test_version_1_persists_correctly(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = repository.create_session(_make_interview_session())
        plan = _plan()

        record = repository.create_plan(session.id, plan)
        db_session.commit()

        assert record.plan_version == 1
        assert record.plan["plan_version"] == 1

    def test_schema_allows_future_version_2(
        self, repository: InterviewRepository, db_session: Session
    ):
        """The UNIQUE(session_id, plan_version) constraint should allow
        a second version for the same session."""
        session = repository.create_session(_make_interview_session())
        plan_v1 = _plan()

        repository.create_plan(session.id, plan_v1)
        db_session.flush()

        # Manually create a v2 record to prove the schema allows it
        v2_data = plan_v1.model_dump(mode="json")
        v2_data["plan_version"] = 2
        record_v2 = InterviewPlanRecord(
            session_id=session.id,
            plan_version=2,
            role=plan_v1.role,
            plan=v2_data,
        )
        db_session.add(record_v2)
        db_session.flush()
        db_session.commit()

        # get_plan returns the latest version
        latest = repository.get_plan(session.id)
        assert latest.plan_version == 2


# ===================================================================
# Serialization round-trip
# ===================================================================


class TestSerializationRoundTrip:
    def test_full_plan_with_claims_survives_roundtrip(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = repository.create_session(_make_interview_session())
        original = _plan_with_claims()

        repository.create_plan(session.id, original)
        db_session.commit()

        loaded = repository.load_plan(session.id)

        assert loaded.role == original.role
        assert loaded.plan_version == original.plan_version
        assert loaded.objectives == original.objectives
        assert len(loaded.planned_topics) == len(original.planned_topics)

        for loaded_topic, original_topic in zip(
            loaded.planned_topics, original.planned_topics
        ):
            assert loaded_topic.topic == original_topic.topic
            assert loaded_topic.competency_keys == original_topic.competency_keys
            assert loaded_topic.priority == original_topic.priority
            assert loaded_topic.rationale == original_topic.rationale
            assert loaded_topic.resume_relevance == original_topic.resume_relevance
            assert loaded_topic.related_claim_ids == original_topic.related_claim_ids
            assert (
                loaded_topic.suggested_time_budget_minutes
                == original_topic.suggested_time_budget_minutes
            )

    def test_jsonb_does_not_contain_raw_resume_text_or_contact_info(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = repository.create_session(_make_interview_session())
        plan = _plan_with_claims()

        record = repository.create_plan(session.id, plan)
        db_session.commit()

        import json
        serialized = json.dumps(record.plan)
        assert "jane@example.com" not in serialized
        assert "555-0100" not in serialized
        assert "Built a RAG" not in serialized

    def test_jsonb_does_not_contain_provider_metadata(
        self, repository: InterviewRepository, db_session: Session
    ):
        session = repository.create_session(_make_interview_session())
        plan = _plan()

        record = repository.create_plan(session.id, plan)
        db_session.commit()

        import json
        serialized = json.dumps(record.plan)
        for forbidden in ["openai", "gemini", "prompt", "temperature", "model_name"]:
            assert forbidden not in serialized.lower()
