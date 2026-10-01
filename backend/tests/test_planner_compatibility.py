"""B5 — provider / legacy-plan compatibility invariants of the planner contract.

Old persisted plans may omit the planner's decisions (they must still load), but a newly generated plan must carry
valid ones, and a failed regeneration of a legacy plan must not destroy it."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.domain.enums import Difficulty
from app.llm.exceptions import LLMInvalidResponseError
from app.llm.models import LLMMessage
from app.planning.models import InterviewPlan, PLAN_MAX_QUESTIONS, PLAN_MIN_QUESTIONS
from app.planning.validator import InvalidInterviewPlanError, validate_interview_plan
from tests.test_llm_gemini_provider import make_provider
from tests.test_plan_runtime_authority import _created, _llm, _plan, _service
from tests.test_plan_runtime_authority import db_session, repository, session_factory  # noqa: F401
from tests.test_planning_validator import _input, _raw_plan


def test_generated_schema_constrains_planner_decisions_and_forbids_extras():
    schema = InterviewPlan.model_json_schema()
    props = schema["properties"]
    assert schema["additionalProperties"] is False
    assert {"EASY", "MEDIUM", "HARD"} == set(schema["$defs"]["Difficulty"]["enum"])
    (integer,) = [b for b in props["max_questions"]["anyOf"] if b.get("type") == "integer"]
    assert (integer["minimum"], integer["maximum"]) == (PLAN_MIN_QUESTIONS, PLAN_MAX_QUESTIONS) == (3, 10)
    # Nullable only so legacy stored plans load; the validator below is what makes the fields mandatory.
    assert "starting_difficulty" not in schema.get("required", []) and "max_questions" not in schema.get("required", [])


@pytest.mark.parametrize("missing", ["starting_difficulty", "max_questions"])
def test_legacy_plan_loads_but_is_not_a_valid_new_plan(missing):
    full = {"starting_difficulty": Difficulty.MEDIUM, "max_questions": 5}
    full.pop(missing)
    plan = _raw_plan(**full)
    assert getattr(plan, missing) is None  # legacy shape deserializes
    with pytest.raises(InvalidInterviewPlanError):
        validate_interview_plan(_input(), plan)


@pytest.mark.parametrize("value", [2, 11, 0, -1])
def test_out_of_range_max_questions_cannot_form_a_plan(value):
    with pytest.raises(Exception):
        _raw_plan(starting_difficulty=Difficulty.MEDIUM, max_questions=value)


@pytest.mark.asyncio
async def test_gemini_dict_response_that_violates_the_schema_is_an_invalid_response():
    provider = make_provider()
    bad = {"role": "AI_ENGINEER", "starting_difficulty": "IMPOSSIBLE", "max_questions": 99}
    provider._client.aio.models.generate_content = AsyncMock(
        return_value=SimpleNamespace(parsed=bad, usage_metadata=None)
    )
    with pytest.raises(LLMInvalidResponseError):
        await provider.generate_structured([LLMMessage(role="user", content="Hi")], InterviewPlan)


@pytest.mark.asyncio
async def test_failed_regeneration_keeps_the_legacy_plan_and_a_retry_replaces_it(repository, db_session):
    fresh = _plan(Difficulty.HARD, 7)
    legacy = InterviewPlan(role=fresh.role, objectives=fresh.objectives, planned_topics=fresh.planned_topics)
    session = _created(repository, db_session)
    repository.create_plan(session.id, legacy)
    db_session.commit()

    with pytest.raises(Exception):
        await _service(repository, _llm(error=RuntimeError("llm down"))).start_interview(session.id)

    db_session.expire_all()
    kept = repository.load_plan(session.id)
    assert kept is not None and kept.max_questions is None  # the old plan was not destroyed

    await _service(repository, _llm(fresh)).start_interview(session.id)
    current = repository.load_plan(session.id)
    assert (current.starting_difficulty, current.max_questions) == (Difficulty.HARD, 7)
