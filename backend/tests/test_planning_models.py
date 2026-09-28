import pytest
from pydantic import BaseModel, ValidationError

from app.domain.competencies import get_role_competencies
from app.domain.enums import Difficulty, InterviewTopic, PlannedTopicPriority, ResumeRelevance, Role
from app.planning.models import (
    PLAN_VERSION,
    InterviewPlan,
    InterviewPlanningConstraints,
    InterviewPlanningInput,
    PlannedTopic,
    PlanningResumeClaim,
    build_claim_id,
    build_planning_input,
    identify_resume_claims,
)
from app.resume.models import ResumeCandidateInfo, ResumeClaim, ResumeProfile, ResumeProjectEntry

RAG_CLAIM = ResumeClaim(claim="Built a RAG system using Qdrant", category="project", source="Projects")
EVAL_CLAIM = ResumeClaim(claim="Reduced hallucinations by 40% with LLM-as-judge evals", category="impact")


def _constraints(**overrides) -> InterviewPlanningConstraints:
    values = {"max_duration_minutes": 30, "difficulty": Difficulty.MEDIUM, "question_limit": 5}
    return InterviewPlanningConstraints(**(values | overrides))


def _profile() -> ResumeProfile:
    return ResumeProfile(
        candidate=ResumeCandidateInfo(name="Jane Doe", email="jane@example.com", phone="555-0100"),
        summary="AI engineer focused on retrieval systems.",
        projects=[ResumeProjectEntry(name="DocSearch", technologies=["Python", "Qdrant"])],
        skills=["Python", "LangChain"],
        claims=[RAG_CLAIM, EVAL_CLAIM],
    )


def _topic(**overrides) -> PlannedTopic:
    values = {
        "topic": InterviewTopic.LLM_FUNDAMENTALS,
        "competency_keys": ["llm_fundamentals"],
        "priority": PlannedTopicPriority.MEDIUM,
        "rationale": "Core role coverage.",
        "suggested_time_budget_minutes": 5,
    }
    return PlannedTopic(**(values | overrides))


# ---------------------------------------------------------------------------
# Planning input
# ---------------------------------------------------------------------------


def test_planning_input_without_resume():
    planning_input = build_planning_input(Role.BACKEND_DEVELOPER, _constraints())

    assert planning_input.role is Role.BACKEND_DEVELOPER
    assert planning_input.competencies == get_role_competencies(Role.BACKEND_DEVELOPER)
    assert planning_input.resume_profile is None
    assert planning_input.resume_claims == []


def test_planning_input_with_resume_profile_and_claims():
    planning_input = build_planning_input(Role.AI_ENGINEER, _constraints(), _profile())

    assert planning_input.resume_profile is not None
    assert planning_input.resume_profile.skills == ["Python", "LangChain"]
    assert planning_input.resume_profile.projects[0].name == "DocSearch"
    assert [c.claim for c in planning_input.resume_claims] == [RAG_CLAIM, EVAL_CLAIM]
    assert all(c.claim_id.startswith("claim_") for c in planning_input.resume_claims)


def test_planning_input_moves_claims_out_of_profile_and_drops_contact_details():
    planning_input = build_planning_input(Role.AI_ENGINEER, _constraints(), _profile())

    assert planning_input.resume_profile.claims == []
    assert planning_input.resume_profile.candidate == ResumeCandidateInfo()


def test_planning_input_can_be_built_directly_with_claims_and_no_profile():
    claims = identify_resume_claims([RAG_CLAIM])
    planning_input = InterviewPlanningInput(
        role=Role.AI_ENGINEER,
        competencies=get_role_competencies(Role.AI_ENGINEER),
        resume_claims=claims,
        constraints=_constraints(),
    )
    assert planning_input.resume_claims[0].claim == RAG_CLAIM


def test_planning_input_rejects_profile_that_still_carries_unidentified_claims():
    with pytest.raises(ValidationError):
        InterviewPlanningInput(
            role=Role.AI_ENGINEER,
            competencies=get_role_competencies(Role.AI_ENGINEER),
            resume_profile=_profile(),
            constraints=_constraints(),
        )


def test_planning_input_rejects_competencies_from_another_role():
    with pytest.raises(ValidationError):
        InterviewPlanningInput(
            role=Role.BACKEND_DEVELOPER,
            competencies=get_role_competencies(Role.AI_ENGINEER),
            constraints=_constraints(),
        )


def test_planning_input_rejects_duplicate_claim_ids():
    claim = PlanningResumeClaim(claim_id="claim_x", claim=RAG_CLAIM)
    with pytest.raises(ValidationError):
        InterviewPlanningInput(
            role=Role.AI_ENGINEER,
            competencies=get_role_competencies(Role.AI_ENGINEER),
            resume_claims=[claim, claim],
            constraints=_constraints(),
        )


@pytest.mark.parametrize(
    "overrides",
    [{"max_duration_minutes": 0}, {"question_limit": 2}, {"question_limit": 11}, {"difficulty": "EXTREME"}],
)
def test_constraints_are_bounded(overrides):
    with pytest.raises(ValidationError):
        _constraints(**overrides)


def test_unknown_role_is_rejected_by_planning_input_and_plan():
    with pytest.raises(ValidationError):
        InterviewPlanningInput(
            role="DATA_SCIENTIST",
            competencies=get_role_competencies(Role.AI_ENGINEER),
            constraints=_constraints(),
        )
    with pytest.raises(ValidationError):
        InterviewPlan(role="DATA_SCIENTIST", objectives=["x"], planned_topics=[_topic()])


# ---------------------------------------------------------------------------
# Claim identity
# ---------------------------------------------------------------------------


def test_claim_id_is_deterministic_and_order_independent():
    forward = identify_resume_claims([RAG_CLAIM, EVAL_CLAIM])
    reverse = identify_resume_claims([EVAL_CLAIM, RAG_CLAIM])

    assert {c.claim_id for c in forward} == {c.claim_id for c in reverse}
    assert build_claim_id(RAG_CLAIM) != build_claim_id(EVAL_CLAIM)


def test_duplicate_claims_collapse_to_one_id():
    assert len(identify_resume_claims([RAG_CLAIM, RAG_CLAIM.model_copy()])) == 1


def test_planning_claim_has_no_verification_field():
    assert set(PlanningResumeClaim.model_fields) == {"claim_id", "claim"}
    assert not any("verif" in name or "true" in name for name in ResumeClaim.model_fields)


# ---------------------------------------------------------------------------
# Planning output
# ---------------------------------------------------------------------------


def test_plan_with_no_resume_linked_topics():
    plan = InterviewPlan(
        role=Role.AI_ENGINEER,
        objectives=["Assess core LLM and retrieval knowledge."],
        planned_topics=[
            _topic(),
            _topic(topic=InterviewTopic.RAG, competency_keys=["retrieval_augmented_generation"]),
        ],
    )

    assert plan.plan_version == PLAN_VERSION
    assert all(t.resume_relevance is ResumeRelevance.NONE for t in plan.planned_topics)
    assert all(t.related_claim_ids == [] for t in plan.planned_topics)


def test_plan_with_resume_linked_topics_and_multiple_claims_on_one_topic():
    claims = identify_resume_claims([RAG_CLAIM, EVAL_CLAIM])
    claim_ids = [c.claim_id for c in claims]

    plan = InterviewPlan(
        role=Role.AI_ENGINEER,
        objectives=["Probe the candidate's reported RAG work."],
        planned_topics=[
            _topic(
                topic=InterviewTopic.RAG,
                competency_keys=["retrieval_augmented_generation"],
                priority=PlannedTopicPriority.HIGH,
                rationale="Candidate reports building a RAG system; investigate depth.",
                resume_relevance=ResumeRelevance.PRIMARY,
                related_claim_ids=claim_ids,
            ),
            _topic(),
        ],
    )

    assert plan.planned_topics[0].related_claim_ids == claim_ids
    assert plan.planned_topics[1].resume_relevance is ResumeRelevance.NONE


def test_plan_allows_several_competencies_for_one_topic():
    planned = _topic(
        topic=InterviewTopic.AI_SYSTEM_DESIGN,
        competency_keys=["llm_serving_tradeoffs", "llm_observability"],
    )
    InterviewPlan(role=Role.AI_ENGINEER, objectives=["x"], planned_topics=[planned])


def test_resume_relevance_and_claim_ids_must_agree():
    with pytest.raises(ValidationError):
        _topic(resume_relevance=ResumeRelevance.PRIMARY)
    with pytest.raises(ValidationError):
        _topic(related_claim_ids=["claim_abc"])
    with pytest.raises(ValidationError):
        _topic(resume_relevance=ResumeRelevance.SUPPORTING, related_claim_ids=["claim_a", "claim_a"])


def test_plan_rejects_topic_outside_the_role_catalog():
    with pytest.raises(ValidationError):
        InterviewPlan(
            role=Role.BACKEND_DEVELOPER,
            objectives=["x"],
            planned_topics=[_topic(topic=InterviewTopic.REACT, competency_keys=["react_rendering"])],
        )


def test_plan_rejects_competency_not_matching_role_or_topic():
    with pytest.raises(ValidationError):
        InterviewPlan(role=Role.AI_ENGINEER, objectives=["x"], planned_topics=[_topic(competency_keys=["caching_strategies"])])
    with pytest.raises(ValidationError):
        InterviewPlan(
            role=Role.AI_ENGINEER,
            objectives=["x"],
            planned_topics=[_topic(competency_keys=["retrieval_augmented_generation"])],
        )


def test_plan_rejects_repeated_topics_and_empty_content():
    with pytest.raises(ValidationError):
        InterviewPlan(role=Role.AI_ENGINEER, objectives=["x"], planned_topics=[_topic(), _topic()])
    with pytest.raises(ValidationError):
        InterviewPlan(role=Role.AI_ENGINEER, objectives=["x"], planned_topics=[])
    with pytest.raises(ValidationError):
        InterviewPlan(role=Role.AI_ENGINEER, objectives=["  "], planned_topics=[_topic()])


# ---------------------------------------------------------------------------
# Contract guarantees: no questions, no raw resume text, no LLM fields
# ---------------------------------------------------------------------------


def _all_field_names(model: type[BaseModel]) -> set[str]:
    names = set(model.model_fields)
    for field in model.model_fields.values():
        annotation = field.annotation
        for candidate in (annotation, *getattr(annotation, "__args__", ())):
            if isinstance(candidate, type) and issubclass(candidate, BaseModel):
                names |= _all_field_names(candidate)
    return names


def test_plan_contract_has_no_generated_question_field():
    names = _all_field_names(InterviewPlan)
    assert not any("question" in name for name in names)


def test_plan_contract_has_no_llm_specific_fields():
    names = _all_field_names(InterviewPlan)
    assert not names & {"model", "provider", "prompt", "raw_response", "tokens", "usage", "temperature"}


def test_plan_rejects_extra_fields_such_as_a_question():
    with pytest.raises(ValidationError):
        _topic(question="Tell me about your RAG system.")
    with pytest.raises(ValidationError):
        InterviewPlan(role=Role.AI_ENGINEER, objectives=["x"], planned_topics=[_topic()], questions=["q"])


def test_plan_references_claims_by_id_without_copying_resume_text():
    planning_input = build_planning_input(Role.AI_ENGINEER, _constraints(), _profile())
    claim_ids = [c.claim_id for c in planning_input.resume_claims]

    plan = InterviewPlan(
        role=Role.AI_ENGINEER,
        objectives=["Investigate reported retrieval experience."],
        planned_topics=[
            _topic(
                topic=InterviewTopic.RAG,
                competency_keys=["retrieval_augmented_generation"],
                resume_relevance=ResumeRelevance.PRIMARY,
                related_claim_ids=claim_ids,
            )
        ],
    )

    serialized = plan.model_dump_json()
    assert RAG_CLAIM.claim not in serialized
    assert "Qdrant" not in serialized
    assert all(claim_id in serialized for claim_id in claim_ids)
    assert "ResumeClaim" not in repr(PlannedTopic.model_fields["related_claim_ids"].annotation)
