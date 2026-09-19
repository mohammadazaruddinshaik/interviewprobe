import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base import Base
from app.domain.enums import Difficulty, InterviewStatus, InterviewTopic, QuestionType, Role
from app.redis.keys import InterviewRedisKeys
from app.redis.runtime_state import InterviewRuntimeNode, InterviewRuntimeState
from app.redis.runtime_state_service import RuntimeStateService, RuntimeStateUnavailableError
from app.repositories.interview_repository import InterviewRepository
from app.services.interview_service import InterviewNotFoundError, InterviewService
from app.workflows.interview.graph import InterviewWorkflow
from app.workflows.interview.models import GeneratedQuestion
from tests.fakes import FailingAsyncRedis, FakeAsyncRedis, FakeLLMProvider

# Same sqlite-compatibility strategy as the other repository/service/API
# test modules in this project (Tasks 7-10).


@compiles(UUID, "sqlite")
def _compile_uuid_sqlite(element, compiler, **kw):
    return "CHAR(32)"


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(element, compiler, **kw):
    return "JSON"


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def repository(db_session: Session) -> InterviewRepository:
    return InterviewRepository(db_session)


@pytest.fixture()
def interview_service(repository: InterviewRepository) -> InterviewService:
    fake_llm = FakeLLMProvider(
        structured_responses={
            "GeneratedQuestion": GeneratedQuestion(
                question="Explain RAG.",
                topic=InterviewTopic.RAG,
                difficulty=Difficulty.MEDIUM,
                question_type=QuestionType.INITIAL,
            )
        }
    )
    workflow = InterviewWorkflow(repository=repository, llm_provider=fake_llm)
    return InterviewService(repository, workflow)


@pytest.fixture()
def fake_redis() -> FakeAsyncRedis:
    return FakeAsyncRedis()


@pytest.fixture()
def runtime_state_service(fake_redis: FakeAsyncRedis, repository: InterviewRepository) -> RuntimeStateService:
    return RuntimeStateService(redis_client=fake_redis, repository=repository)


def sample_state(session_id: uuid.UUID | None = None) -> InterviewRuntimeState:
    return InterviewRuntimeState(
        session_id=session_id or uuid.uuid4(),
        status=InterviewStatus.IN_PROGRESS,
        current_node=InterviewRuntimeNode.WAITING_FOR_ANSWER,
        question_number=1,
        question_limit=5,
        current_topic=InterviewTopic.RAG,
        current_question_id=uuid.uuid4(),
        difficulty=Difficulty.MEDIUM,
        last_action=None,
        version=2,
    )


# ---------------------------------------------------------------------------
# Key generation
# ---------------------------------------------------------------------------


def test_state_key_format_is_deterministic():
    session_id = uuid.uuid4()

    assert InterviewRedisKeys.state(session_id) == f"interview:{session_id}:state"
    assert InterviewRedisKeys.state(session_id) == InterviewRedisKeys.state(session_id)


# ---------------------------------------------------------------------------
# Serialization / set / get / delete / exists
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_then_get_returns_identical_state(runtime_state_service: RuntimeStateService):
    state = sample_state()

    await runtime_state_service.set_state(state)
    fetched = await runtime_state_service.get_state(state.session_id)

    assert fetched == state


@pytest.mark.asyncio
async def test_get_returns_none_on_redis_miss(runtime_state_service: RuntimeStateService):
    assert await runtime_state_service.get_state(uuid.uuid4()) is None


@pytest.mark.asyncio
async def test_exists_reflects_presence(runtime_state_service: RuntimeStateService):
    state = sample_state()

    assert await runtime_state_service.exists(state.session_id) is False

    await runtime_state_service.set_state(state)

    assert await runtime_state_service.exists(state.session_id) is True


@pytest.mark.asyncio
async def test_delete_removes_state(runtime_state_service: RuntimeStateService):
    state = sample_state()
    await runtime_state_service.set_state(state)

    await runtime_state_service.delete_state(state.session_id)

    assert await runtime_state_service.get_state(state.session_id) is None


@pytest.mark.asyncio
async def test_state_is_stored_as_json_under_the_correct_key(
    runtime_state_service: RuntimeStateService, fake_redis: FakeAsyncRedis
):
    state = sample_state()

    await runtime_state_service.set_state(state)

    key = InterviewRedisKeys.state(state.session_id)
    assert key in fake_redis.store
    assert fake_redis.store[key] == state.model_dump_json()


# ---------------------------------------------------------------------------
# TTL
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_state_applies_configured_ttl(
    runtime_state_service: RuntimeStateService, fake_redis: FakeAsyncRedis
):
    state = sample_state()

    await runtime_state_service.set_state(state)

    key = InterviewRedisKeys.state(state.session_id)
    assert fake_redis.ttls[key] == settings.redis_interview_state_ttl_seconds


# ---------------------------------------------------------------------------
# Rebuild from PostgreSQL
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_or_rebuild_state_returns_redis_value_on_hit(
    runtime_state_service: RuntimeStateService,
):
    state = sample_state()
    await runtime_state_service.set_state(state)

    result = await runtime_state_service.get_or_rebuild_state(state.session_id)

    assert result == state


@pytest.mark.asyncio
async def test_get_or_rebuild_state_reconstructs_from_postgres_on_miss(
    runtime_state_service: RuntimeStateService,
    interview_service: InterviewService,
    fake_redis: FakeAsyncRedis,
):
    session = interview_service.create_interview(
        role=Role.AI_ENGINEER,
        difficulty=Difficulty.MEDIUM,
        question_limit=3,
        topics=[InterviewTopic.RAG],
    )
    session, question = await interview_service.start_interview(session.id)

    # Nothing was ever written to Redis for this session.
    assert await runtime_state_service.exists(session.id) is False

    rebuilt = await runtime_state_service.get_or_rebuild_state(session.id)

    assert rebuilt.session_id == session.id
    assert rebuilt.status == InterviewStatus.IN_PROGRESS
    assert rebuilt.current_node == InterviewRuntimeNode.WAITING_FOR_ANSWER
    assert rebuilt.question_number == 1
    assert rebuilt.question_limit == 3
    assert rebuilt.current_topic == question.topic
    assert rebuilt.current_question_id == question.id
    assert rebuilt.difficulty == Difficulty.MEDIUM
    assert rebuilt.version == session.version
    assert rebuilt.last_action is None

    # The rebuilt state is written back to Redis.
    assert await runtime_state_service.exists(session.id) is True
    key = InterviewRedisKeys.state(session.id)
    assert fake_redis.ttls[key] == settings.redis_interview_state_ttl_seconds


@pytest.mark.asyncio
async def test_get_or_rebuild_state_raises_for_nonexistent_session(
    runtime_state_service: RuntimeStateService,
):
    with pytest.raises(InterviewNotFoundError):
        await runtime_state_service.get_or_rebuild_state(uuid.uuid4())


# ---------------------------------------------------------------------------
# Redis failure behavior
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_redis_failure_raises_explicit_error_not_silent(repository: InterviewRepository):
    service = RuntimeStateService(redis_client=FailingAsyncRedis(), repository=repository)
    state = sample_state()

    with pytest.raises(RuntimeStateUnavailableError):
        await service.set_state(state)


@pytest.mark.asyncio
async def test_redis_failure_does_not_affect_postgres_interview_state(
    repository: InterviewRepository, interview_service: InterviewService
):
    session = interview_service.create_interview(
        role=Role.AI_ENGINEER,
        difficulty=Difficulty.MEDIUM,
        question_limit=3,
        topics=[InterviewTopic.RAG],
    )
    session, question = await interview_service.start_interview(session.id)

    failing_runtime_state_service = RuntimeStateService(
        redis_client=FailingAsyncRedis(), repository=repository
    )

    with pytest.raises(RuntimeStateUnavailableError):
        await failing_runtime_state_service.set_state(
            failing_runtime_state_service.build_state(session=session, last_action=None)
        )

    # PostgreSQL state is untouched by the Redis failure.
    reloaded = repository.get_session(session.id)
    assert reloaded.status == InterviewStatus.IN_PROGRESS
    assert reloaded.current_question_number == 1
