"""Resume-claim context builder for question generation.

Given an interview plan and a resume profile, derives which resume
claims are relevant to a specific interview topic.  Only claims whose
deterministic IDs (via ``build_claim_id``) appear in the planned
topic's ``related_claim_ids`` are included.

Everything here is pure — no DB, no LLM, no side effects.
"""

from app.domain.enums import InterviewTopic
from app.planning.models import InterviewPlan, build_claim_id
from app.resume.models import ResumeClaim, ResumeProfile


def build_resume_claims_map(
    plan: InterviewPlan | None,
    resume_profile: ResumeProfile | None,
) -> dict[str, list[ResumeClaim]]:
    """Pre-compute a mapping of topic value -> relevant resume claims.

    Returns an empty dict when no plan, no resume, or no claims exist,
    making resume-free and legacy sessions behave identically to before.
    """
    if plan is None or resume_profile is None or not resume_profile.claims:
        return {}

    claims_by_id: dict[str, ResumeClaim] = {}
    for claim in resume_profile.claims:
        claims_by_id[build_claim_id(claim)] = claim

    result: dict[str, list[ResumeClaim]] = {}
    for planned_topic in plan.planned_topics:
        if not planned_topic.related_claim_ids:
            continue
        matched = [
            claims_by_id[cid]
            for cid in planned_topic.related_claim_ids
            if cid in claims_by_id
        ]
        if matched:
            result[planned_topic.topic.value] = matched

    return result


def resolve_resume_claims_for_topic(
    topic: InterviewTopic | None,
    claims_map: dict[str, list[ResumeClaim]],
) -> list[ResumeClaim]:
    """Look up claims for a specific topic from a pre-computed map."""
    if topic is None or not claims_map:
        return []
    return claims_map.get(topic.value, [])
