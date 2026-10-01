"""The provider-neutral interview planning contract: what a (future)
planner receives, and the shape of the plan it must return.

    InterviewPlanningInput  →  planner  →  InterviewPlan

The planner decides WHAT areas to cover. It never generates questions —
the existing question generator does that — and it never decides how to
react to an answer — the existing adaptive engine does that. A plan maps
onto the existing `interview_topics` runtime state via `PlannedTopic.topic`,
which must be one of the role's catalog topics.

Resume semantics: everything taken from a resume is candidate-reported
evidence, never verified fact. `PlanningResumeClaim` deliberately carries
no verified/true/false field (mirroring `ResumeClaim`), and a plan may
only point at claims by `claim_id` — it never copies claim or resume text.

Nothing here is persisted or exposed through an API yet, and nothing here
calls an LLM.
"""

import hashlib

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.competencies import RoleCompetency, get_competency, get_role_competencies
from app.domain.enums import Difficulty, InterviewTopic, PlannedTopicPriority, ResumeRelevance, Role
from app.domain.roles import is_topic_valid_for_role
from app.resume.models import ResumeCandidateInfo, ResumeClaim, ResumeProfile

PLAN_VERSION = 1

# Backend-defined bounds on planner output. The question bounds mirror the existing runtime contract for
# `interview_sessions.question_limit` (ck_interview_sessions_question_limit_min, >= 3), since `max_questions` is
# copied into that column at start. The topic bounds: a plan needs at least two topics (the smallest role —
# SDE_INTERN — has two required topics) and at most six.
PLAN_MIN_QUESTIONS = 3
PLAN_MAX_QUESTIONS = 10
PLAN_MIN_TOPICS = 2
PLAN_MAX_TOPICS = 6


# ---------------------------------------------------------------------------
# Resume claim identity
# ---------------------------------------------------------------------------


def build_claim_id(claim: ResumeClaim) -> str:
    """A deterministic ID for a resume claim.

    `ResumeClaim` has no ID of its own — claims are persisted as a list
    inside `interview_resumes.structured_profile` — and adding one to the
    extraction schema would ask the LLM to invent it. A content hash is
    stable for a given persisted profile regardless of list order, so the
    same claim always gets the same ID across planner runs.
    """
    fingerprint = "\x1f".join(
        (part or "").strip().lower() for part in (claim.claim, claim.category, claim.source)
    )
    return "claim_" + hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:12]


class PlanningResumeClaim(BaseModel):
    """A candidate-reported resume claim with a stable ID the plan can
    reference. Unverified by definition — a planner may prioritize
    investigating it, but must never treat it as true."""

    model_config = ConfigDict(frozen=True)

    claim_id: str = Field(min_length=1)
    claim: ResumeClaim


def identify_resume_claims(claims: list[ResumeClaim]) -> list[PlanningResumeClaim]:
    """Assign IDs to `claims`, dropping exact duplicates (same ID)."""
    identified: dict[str, PlanningResumeClaim] = {}
    for claim in claims:
        claim_id = build_claim_id(claim)
        identified.setdefault(claim_id, PlanningResumeClaim(claim_id=claim_id, claim=claim))
    return list(identified.values())


# ---------------------------------------------------------------------------
# Planning input
# ---------------------------------------------------------------------------


class InterviewPlanningConstraints(BaseModel):
    """The only hard limit on a plan. Difficulty, question count and topics are the planner's decisions, not
    inputs — `extra="forbid"` so a caller still passing them fails loudly."""

    model_config = ConfigDict(extra="forbid")

    max_duration_minutes: int = Field(ge=1)


class InterviewPlanningInput(BaseModel):
    """Everything a planner may use. `competencies` is always the role's full competency catalog — the planner
    chooses the topics. `resume_profile` holds no claims and no candidate contact details — claims travel
    separately, identified, in `resume_claims` (see `build_planning_input`)."""

    model_config = ConfigDict(extra="forbid")

    role: Role
    competencies: list[RoleCompetency] = Field(min_length=1)
    resume_profile: ResumeProfile | None = None
    resume_claims: list[PlanningResumeClaim] = Field(default_factory=list)
    constraints: InterviewPlanningConstraints

    @model_validator(mode="after")
    def _check_consistency(self) -> "InterviewPlanningInput":
        for competency in self.competencies:
            if get_competency(self.role, competency.key) != competency:
                raise ValueError(
                    f"Competency '{competency.key}' is not part of the {self.role.value} competency catalog."
                )
        if self.resume_profile is not None and self.resume_profile.claims:
            raise ValueError("resume_profile.claims must be empty; pass identified claims via resume_claims.")
        claim_ids = [c.claim_id for c in self.resume_claims]
        if len(claim_ids) != len(set(claim_ids)):
            raise ValueError("resume_claims contains duplicate claim_id values.")
        return self


def build_planning_input(
    role: Role,
    constraints: InterviewPlanningConstraints,
    resume_profile: ResumeProfile | None = None,
) -> InterviewPlanningInput:
    """Assemble planner input from the role's full competency catalog and an
    optional (already validated) resume profile. The profile's claims are
    moved into identified `resume_claims`, and candidate contact details
    are dropped — the planner has no use for them."""
    profile = None
    claims: list[PlanningResumeClaim] = []
    if resume_profile is not None:
        claims = identify_resume_claims(resume_profile.claims)
        profile = resume_profile.model_copy(update={"claims": [], "candidate": ResumeCandidateInfo()})
    return InterviewPlanningInput(
        role=role,
        competencies=get_role_competencies(role),
        resume_profile=profile,
        resume_claims=claims,
        constraints=constraints,
    )


# ---------------------------------------------------------------------------
# Planning output
# ---------------------------------------------------------------------------


class PlannedTopic(BaseModel):
    """One topic the interview should cover, in plan order. `extra="forbid"`
    so a planner can't smuggle in fields the contract doesn't define (e.g.
    a generated question)."""

    model_config = ConfigDict(extra="forbid")

    topic: InterviewTopic
    competency_keys: list[str] = Field(min_length=1)
    priority: PlannedTopicPriority
    rationale: str = Field(min_length=1, max_length=500)
    resume_relevance: ResumeRelevance = ResumeRelevance.NONE
    related_claim_ids: list[str] = Field(default_factory=list)
    suggested_time_budget_minutes: int = Field(ge=1)

    @model_validator(mode="after")
    def _check_resume_link(self) -> "PlannedTopic":
        if len(self.related_claim_ids) != len(set(self.related_claim_ids)):
            raise ValueError("related_claim_ids contains duplicates.")
        if (self.resume_relevance is ResumeRelevance.NONE) != (not self.related_claim_ids):
            raise ValueError("resume_relevance NONE requires no related_claim_ids, and vice versa.")
        return self


class InterviewPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Role
    plan_version: int = Field(default=PLAN_VERSION, ge=1)
    objectives: list[str] = Field(min_length=1)
    planned_topics: list[PlannedTopic] = Field(min_length=1)
    # The planner's interview-shaping decisions. Optional ONLY so plans persisted before these fields existed
    # still load; `validate_interview_plan` rejects a freshly generated plan that omits them. `max_questions` is
    # a safety ceiling, not a promised length — the adaptive workflow may finish earlier.
    starting_difficulty: Difficulty | None = None
    max_questions: int | None = Field(default=None, ge=PLAN_MIN_QUESTIONS, le=PLAN_MAX_QUESTIONS)

    @field_validator("objectives")
    @classmethod
    def _objectives_not_blank(cls, objectives: list[str]) -> list[str]:
        if any(not objective.strip() for objective in objectives):
            raise ValueError("objectives must not contain blank entries.")
        return objectives

    @model_validator(mode="after")
    def _check_against_role_catalog(self) -> "InterviewPlan":
        topics = [planned.topic for planned in self.planned_topics]
        if len(topics) != len(set(topics)):
            # interview_topics holds one row per (session, topic).
            raise ValueError("planned_topics must not repeat a topic.")
        for planned in self.planned_topics:
            if not is_topic_valid_for_role(self.role, planned.topic):
                raise ValueError(f"Topic {planned.topic.value} is not valid for role {self.role.value}.")
            for key in planned.competency_keys:
                competency = get_competency(self.role, key)
                if competency is None or competency.topic is not planned.topic:
                    raise ValueError(
                        f"Competency '{key}' is not a {self.role.value} competency for topic {planned.topic.value}."
                    )
        return self
