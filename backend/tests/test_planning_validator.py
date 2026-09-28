"""Cross-object validation tests for the interview planning contract.

These verify invariants that span both InterviewPlanningInput and
InterviewPlan — the layer that sits between Pydantic's structural
validation (which already rejects bad competency/topic mappings, empty
plans, duplicate topics, etc.) and a future LLM planner.
"""

import pytest
from pydantic import ValidationError

from app.domain.competencies import get_role_competencies
from app.domain.enums import Difficulty, InterviewTopic, PlannedTopicPriority, ResumeRelevance, Role
from app.planning.models import (
    InterviewPlan,
    InterviewPlanningConstraints,
    InterviewPlanningInput,
    PlannedTopic,
    PlanningResumeClaim,
    build_planning_input,
    identify_resume_claims,
)
from app.planning.validator import InvalidInterviewPlanError, validate_interview_plan
from app.resume.models import ResumeClaim, ResumeProfile, ResumeProjectEntry

RAG_CLAIM = ResumeClaim(claim="Built a RAG system using Qdrant", category="project", source="Projects")
EVAL_CLAIM = ResumeClaim(claim="Reduced hallucinations by 40% with LLM-as-judge evals", category="impact")
SPRING_CLAIM = ResumeClaim(claim="Migrated monolith to Spring Boot microservices", category="experience")


def _constraints(**overrides) -> InterviewPlanningConstraints:
    defaults = {"max_duration_minutes": 45, "difficulty": Difficulty.MEDIUM, "question_limit": 5}
    return InterviewPlanningConstraints(**(defaults | overrides))


def _input(role: Role = Role.AI_ENGINEER, claims: list[ResumeClaim] | None = None, **constraint_kw) -> InterviewPlanningInput:
    profile = None
    if claims is not None:
        profile = ResumeProfile(claims=claims)
    return build_planning_input(role, _constraints(**constraint_kw), profile)


def _topic(**overrides) -> PlannedTopic:
    defaults = {
        "topic": InterviewTopic.LLM_FUNDAMENTALS,
        "competency_keys": ["llm_fundamentals"],
        "priority": PlannedTopicPriority.MEDIUM,
        "rationale": "Core role coverage.",
        "suggested_time_budget_minutes": 5,
    }
    return PlannedTopic(**(defaults | overrides))


def _plan(role: Role = Role.AI_ENGINEER, topics: list[PlannedTopic] | None = None) -> InterviewPlan:
    if topics is None:
        topics = [_topic()]
    return InterviewPlan(role=role, objectives=["Assess candidate competency."], planned_topics=topics)


# ===================================================================
# Role consistency
# ===================================================================


class TestRoleConsistency:
    def test_matching_roles_pass(self):
        pi = _input(Role.AI_ENGINEER)
        plan = _plan(Role.AI_ENGINEER)
        validate_interview_plan(pi, plan)  # no exception

    def test_mismatched_role_input_ai_plan_backend_fails(self):
        pi = _input(Role.AI_ENGINEER)
        plan = _plan(
            Role.BACKEND_DEVELOPER,
            [_topic(topic=InterviewTopic.REST_APIS, competency_keys=["api_design"])],
        )

        with pytest.raises(InvalidInterviewPlanError, match="BACKEND_DEVELOPER.*AI_ENGINEER"):
            validate_interview_plan(pi, plan)

    def test_mismatched_role_input_backend_plan_ai_fails(self):
        pi = _input(Role.BACKEND_DEVELOPER)
        plan = _plan(Role.AI_ENGINEER)

        with pytest.raises(InvalidInterviewPlanError, match="AI_ENGINEER.*BACKEND_DEVELOPER"):
            validate_interview_plan(pi, plan)


# ===================================================================
# Competency → topic consistency (model-level, not cross-object, but
# included to confirm these rejections still work end-to-end when
# the cross-object validator is also involved)
# ===================================================================


class TestCompetencyTopicConsistency:
    def test_valid_competency_topic_combination_passes(self):
        pi = _input(Role.AI_ENGINEER)
        plan = _plan(Role.AI_ENGINEER, [
            _topic(topic=InterviewTopic.RAG, competency_keys=["retrieval_augmented_generation"]),
        ])
        validate_interview_plan(pi, plan)

    def test_unknown_competency_fails_at_model_level(self):
        with pytest.raises(ValidationError, match="no_such_competency"):
            _plan(Role.AI_ENGINEER, [
                _topic(competency_keys=["no_such_competency"]),
            ])

    def test_competency_belonging_to_another_role_fails(self):
        # caching_strategies belongs to BACKEND_DEVELOPER, not AI_ENGINEER
        with pytest.raises(ValidationError, match="caching_strategies"):
            _plan(Role.AI_ENGINEER, [
                _topic(competency_keys=["caching_strategies"]),
            ])

    def test_competency_anchored_to_another_topic_fails(self):
        # retrieval_augmented_generation anchors to RAG, not LLM_FUNDAMENTALS
        with pytest.raises(ValidationError, match="retrieval_augmented_generation"):
            _plan(Role.AI_ENGINEER, [
                _topic(topic=InterviewTopic.LLM_FUNDAMENTALS,
                       competency_keys=["retrieval_augmented_generation"]),
            ])

    def test_multiple_valid_competencies_on_one_topic_pass(self):
        pi = _input(Role.AI_ENGINEER)
        plan = _plan(Role.AI_ENGINEER, [
            _topic(topic=InterviewTopic.AI_SYSTEM_DESIGN,
                   competency_keys=["llm_serving_tradeoffs", "llm_observability"]),
        ])
        validate_interview_plan(pi, plan)

    def test_multiple_competencies_from_different_topics_fail(self):
        # llm_fundamentals -> LLM_FUNDAMENTALS, retrieval_augmented_generation -> RAG
        with pytest.raises(ValidationError):
            _plan(Role.AI_ENGINEER, [
                _topic(topic=InterviewTopic.LLM_FUNDAMENTALS,
                       competency_keys=["llm_fundamentals", "retrieval_augmented_generation"]),
            ])


# ===================================================================
# Claim references
# ===================================================================


class TestClaimReferences:
    def test_valid_claim_ids_pass(self):
        pi = _input(Role.AI_ENGINEER, claims=[RAG_CLAIM])
        claim_id = pi.resume_claims[0].claim_id

        plan = _plan(Role.AI_ENGINEER, [
            _topic(topic=InterviewTopic.RAG,
                   competency_keys=["retrieval_augmented_generation"],
                   resume_relevance=ResumeRelevance.PRIMARY,
                   related_claim_ids=[claim_id]),
        ])
        validate_interview_plan(pi, plan)

    def test_unknown_claim_id_fails(self):
        pi = _input(Role.AI_ENGINEER, claims=[RAG_CLAIM])

        plan = _plan(Role.AI_ENGINEER, [
            _topic(topic=InterviewTopic.RAG,
                   competency_keys=["retrieval_augmented_generation"],
                   resume_relevance=ResumeRelevance.PRIMARY,
                   related_claim_ids=["claim_xyz999"]),
        ])

        with pytest.raises(InvalidInterviewPlanError, match="claim_xyz999"):
            validate_interview_plan(pi, plan)

    def test_multiple_valid_claim_ids_pass(self):
        pi = _input(Role.AI_ENGINEER, claims=[RAG_CLAIM, EVAL_CLAIM])
        claim_ids = [c.claim_id for c in pi.resume_claims]

        plan = _plan(Role.AI_ENGINEER, [
            _topic(topic=InterviewTopic.RAG,
                   competency_keys=["retrieval_augmented_generation"],
                   resume_relevance=ResumeRelevance.PRIMARY,
                   related_claim_ids=claim_ids),
        ])
        validate_interview_plan(pi, plan)

    def test_duplicate_claim_ids_within_a_topic_rejected_at_model_level(self):
        """Task 1's PlannedTopic model validator already rejects duplicates."""
        pi = _input(Role.AI_ENGINEER, claims=[RAG_CLAIM])
        claim_id = pi.resume_claims[0].claim_id

        with pytest.raises(ValidationError, match="duplicates"):
            _topic(topic=InterviewTopic.RAG,
                   competency_keys=["retrieval_augmented_generation"],
                   resume_relevance=ResumeRelevance.PRIMARY,
                   related_claim_ids=[claim_id, claim_id])

    def test_unknown_claim_error_names_the_topic_and_claim(self):
        pi = _input(Role.AI_ENGINEER)

        plan = _plan(Role.AI_ENGINEER, [
            _topic(topic=InterviewTopic.RAG,
                   competency_keys=["retrieval_augmented_generation"],
                   resume_relevance=ResumeRelevance.PRIMARY,
                   related_claim_ids=["claim_ghost"]),
        ])

        with pytest.raises(InvalidInterviewPlanError) as exc_info:
            validate_interview_plan(pi, plan)

        msg = str(exc_info.value)
        assert "RAG" in msg
        assert "claim_ghost" in msg
        assert "(none)" in msg  # no claims in input

    def test_claim_reference_against_input_with_no_resume(self):
        pi = _input(Role.AI_ENGINEER)

        plan = _plan(Role.AI_ENGINEER, [
            _topic(topic=InterviewTopic.RAG,
                   competency_keys=["retrieval_augmented_generation"],
                   resume_relevance=ResumeRelevance.PRIMARY,
                   related_claim_ids=["claim_abc"]),
        ])

        with pytest.raises(InvalidInterviewPlanError, match="claim_abc"):
            validate_interview_plan(pi, plan)


# ===================================================================
# Resume relevance
# ===================================================================


class TestResumeRelevance:
    def test_none_with_no_claims_passes(self):
        pi = _input(Role.AI_ENGINEER)
        plan = _plan(Role.AI_ENGINEER, [_topic()])
        validate_interview_plan(pi, plan)

    def test_none_with_claim_ids_fails_at_model_level(self):
        with pytest.raises(ValidationError):
            _topic(resume_relevance=ResumeRelevance.NONE, related_claim_ids=["claim_abc"])

    def test_primary_with_valid_claim_passes(self):
        pi = _input(Role.AI_ENGINEER, claims=[RAG_CLAIM])
        claim_id = pi.resume_claims[0].claim_id

        plan = _plan(Role.AI_ENGINEER, [
            _topic(topic=InterviewTopic.RAG,
                   competency_keys=["retrieval_augmented_generation"],
                   resume_relevance=ResumeRelevance.PRIMARY,
                   related_claim_ids=[claim_id]),
        ])
        validate_interview_plan(pi, plan)

    def test_supporting_with_valid_claim_passes(self):
        pi = _input(Role.AI_ENGINEER, claims=[RAG_CLAIM])
        claim_id = pi.resume_claims[0].claim_id

        plan = _plan(Role.AI_ENGINEER, [
            _topic(topic=InterviewTopic.RAG,
                   competency_keys=["retrieval_augmented_generation"],
                   resume_relevance=ResumeRelevance.SUPPORTING,
                   related_claim_ids=[claim_id]),
        ])
        validate_interview_plan(pi, plan)

    def test_primary_with_no_claims_fails_at_model_level(self):
        with pytest.raises(ValidationError):
            _topic(resume_relevance=ResumeRelevance.PRIMARY)

    def test_supporting_with_no_claims_fails_at_model_level(self):
        with pytest.raises(ValidationError):
            _topic(resume_relevance=ResumeRelevance.SUPPORTING)

    def test_primary_with_unknown_claim_fails_at_cross_validation(self):
        pi = _input(Role.AI_ENGINEER, claims=[RAG_CLAIM])

        plan = _plan(Role.AI_ENGINEER, [
            _topic(topic=InterviewTopic.RAG,
                   competency_keys=["retrieval_augmented_generation"],
                   resume_relevance=ResumeRelevance.PRIMARY,
                   related_claim_ids=["claim_unknown"]),
        ])

        with pytest.raises(InvalidInterviewPlanError, match="claim_unknown"):
            validate_interview_plan(pi, plan)


# ===================================================================
# Time budget
# ===================================================================


class TestTimeBudget:
    def test_total_exactly_equals_max_duration_passes(self):
        pi = _input(Role.AI_ENGINEER, max_duration_minutes=10)

        plan = _plan(Role.AI_ENGINEER, [
            _topic(suggested_time_budget_minutes=5),
            _topic(topic=InterviewTopic.RAG,
                   competency_keys=["retrieval_augmented_generation"],
                   suggested_time_budget_minutes=5),
        ])
        validate_interview_plan(pi, plan)

    def test_total_below_max_duration_passes(self):
        pi = _input(Role.AI_ENGINEER, max_duration_minutes=45)
        plan = _plan(Role.AI_ENGINEER, [_topic(suggested_time_budget_minutes=10)])
        validate_interview_plan(pi, plan)

    def test_total_exceeds_max_duration_fails(self):
        pi = _input(Role.AI_ENGINEER, max_duration_minutes=15)

        plan = _plan(Role.AI_ENGINEER, [
            _topic(suggested_time_budget_minutes=10),
            _topic(topic=InterviewTopic.RAG,
                   competency_keys=["retrieval_augmented_generation"],
                   suggested_time_budget_minutes=8),
        ])

        with pytest.raises(InvalidInterviewPlanError, match="18 minutes.*15 minutes"):
            validate_interview_plan(pi, plan)

    def test_zero_time_budget_rejected_at_model_level(self):
        with pytest.raises(ValidationError):
            _topic(suggested_time_budget_minutes=0)

    def test_negative_time_budget_rejected_at_model_level(self):
        with pytest.raises(ValidationError):
            _topic(suggested_time_budget_minutes=-1)

    def test_time_error_states_both_totals(self):
        pi = _input(Role.AI_ENGINEER, max_duration_minutes=20)

        plan = _plan(Role.AI_ENGINEER, [
            _topic(suggested_time_budget_minutes=15),
            _topic(topic=InterviewTopic.RAG,
                   competency_keys=["retrieval_augmented_generation"],
                   suggested_time_budget_minutes=10),
        ])

        with pytest.raises(InvalidInterviewPlanError) as exc_info:
            validate_interview_plan(pi, plan)

        msg = str(exc_info.value)
        assert "25" in msg
        assert "20" in msg


# ===================================================================
# Plan integrity (end-to-end happy paths)
# ===================================================================


class TestPlanIntegrity:
    def test_valid_complete_plan_no_resume(self):
        pi = _input(Role.BACKEND_DEVELOPER, max_duration_minutes=45)

        plan = InterviewPlan(
            role=Role.BACKEND_DEVELOPER,
            objectives=["Assess backend engineering depth."],
            planned_topics=[
                PlannedTopic(
                    topic=InterviewTopic.REST_APIS,
                    competency_keys=["api_design", "api_evolution"],
                    priority=PlannedTopicPriority.HIGH,
                    rationale="Core backend skill.",
                    suggested_time_budget_minutes=10,
                ),
                PlannedTopic(
                    topic=InterviewTopic.DATABASES,
                    competency_keys=["data_modeling", "transactions_consistency"],
                    priority=PlannedTopicPriority.MEDIUM,
                    rationale="Essential for any backend role.",
                    suggested_time_budget_minutes=10,
                ),
                PlannedTopic(
                    topic=InterviewTopic.SYSTEM_DESIGN,
                    competency_keys=["system_design"],
                    priority=PlannedTopicPriority.MEDIUM,
                    rationale="Evaluates architectural thinking.",
                    suggested_time_budget_minutes=10,
                ),
            ],
        )

        validate_interview_plan(pi, plan)  # no exception

    def test_valid_multi_topic_plan_with_resume_claims(self):
        pi = _input(Role.AI_ENGINEER, claims=[RAG_CLAIM, EVAL_CLAIM], max_duration_minutes=30)
        rag_id = [c.claim_id for c in pi.resume_claims if "RAG" in c.claim.claim][0]
        eval_id = [c.claim_id for c in pi.resume_claims if "hallucinations" in c.claim.claim][0]

        plan = InterviewPlan(
            role=Role.AI_ENGINEER,
            objectives=["Probe reported RAG work.", "Assess evaluation methodology."],
            planned_topics=[
                PlannedTopic(
                    topic=InterviewTopic.RAG,
                    competency_keys=["retrieval_augmented_generation"],
                    priority=PlannedTopicPriority.HIGH,
                    rationale="Candidate reports building a RAG system.",
                    resume_relevance=ResumeRelevance.PRIMARY,
                    related_claim_ids=[rag_id],
                    suggested_time_budget_minutes=10,
                ),
                PlannedTopic(
                    topic=InterviewTopic.LLM_EVALUATION,
                    competency_keys=["llm_evaluation"],
                    priority=PlannedTopicPriority.HIGH,
                    rationale="Candidate reports measurable eval impact.",
                    resume_relevance=ResumeRelevance.SUPPORTING,
                    related_claim_ids=[eval_id],
                    suggested_time_budget_minutes=8,
                ),
                PlannedTopic(
                    topic=InterviewTopic.LLM_FUNDAMENTALS,
                    competency_keys=["llm_fundamentals"],
                    priority=PlannedTopicPriority.MEDIUM,
                    rationale="Baseline LLM knowledge.",
                    suggested_time_budget_minutes=7,
                ),
            ],
        )

        validate_interview_plan(pi, plan)  # no exception

    def test_valid_plan_with_same_claim_across_multiple_topics(self):
        pi = _input(Role.AI_ENGINEER, claims=[RAG_CLAIM], max_duration_minutes=30)
        claim_id = pi.resume_claims[0].claim_id

        plan = InterviewPlan(
            role=Role.AI_ENGINEER,
            objectives=["Investigate RAG claim from multiple angles."],
            planned_topics=[
                PlannedTopic(
                    topic=InterviewTopic.RAG,
                    competency_keys=["retrieval_augmented_generation"],
                    priority=PlannedTopicPriority.HIGH,
                    rationale="Direct claim investigation.",
                    resume_relevance=ResumeRelevance.PRIMARY,
                    related_claim_ids=[claim_id],
                    suggested_time_budget_minutes=10,
                ),
                PlannedTopic(
                    topic=InterviewTopic.EMBEDDINGS_VECTOR_DB,
                    competency_keys=["embeddings_vector_search"],
                    priority=PlannedTopicPriority.MEDIUM,
                    rationale="RAG claim implies vector DB experience.",
                    resume_relevance=ResumeRelevance.SUPPORTING,
                    related_claim_ids=[claim_id],
                    suggested_time_budget_minutes=8,
                ),
            ],
        )

        validate_interview_plan(pi, plan)  # no exception


# ===================================================================
# Duplicate topic (already enforced at model level — confirm here)
# ===================================================================


class TestDuplicateTopics:
    def test_duplicate_topics_rejected_at_model_level(self):
        with pytest.raises(ValidationError, match="repeat"):
            InterviewPlan(
                role=Role.AI_ENGINEER,
                objectives=["x"],
                planned_topics=[_topic(), _topic()],
            )
