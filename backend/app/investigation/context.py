"""Investigation context builder for question generation.

Given an interview plan, a resume profile, and persisted claim
investigations, derives which investigation results are relevant to each
topic.  Pure — no DB, no LLM, no side effects.

Mirrors ``app/planning/resume_context.py`` for resume claims.
"""

from app.domain.enums import ClaimInvestigationStatus, InterviewTopic
from app.investigation.models import ClaimInvestigation, ClaimInvestigationContext
from app.planning.models import InterviewPlan, build_claim_id
from app.resume.models import ResumeClaim, ResumeProfile


def build_investigation_context_map(
    plan: InterviewPlan | None,
    resume_profile: ResumeProfile | None,
    investigations: list[ClaimInvestigation],
) -> dict[str, list[ClaimInvestigationContext]]:
    """Pre-compute a mapping of topic value -> relevant investigation contexts.

    Returns an empty dict when no plan, no resume, no claims, or no
    investigations exist, making resume-free and legacy sessions behave
    identically to before.
    """
    if plan is None or resume_profile is None or not resume_profile.claims or not investigations:
        return {}

    claims_by_id: dict[str, ResumeClaim] = {}
    for claim in resume_profile.claims:
        claims_by_id[build_claim_id(claim)] = claim

    inv_by_claim_id: dict[str, ClaimInvestigation] = {
        inv.claim_id: inv for inv in investigations
    }

    result: dict[str, list[ClaimInvestigationContext]] = {}
    for planned_topic in plan.planned_topics:
        if not planned_topic.related_claim_ids:
            continue
        contexts: list[ClaimInvestigationContext] = []
        for cid in planned_topic.related_claim_ids:
            claim = claims_by_id.get(cid)
            inv = inv_by_claim_id.get(cid)
            if claim is None or inv is None:
                continue
            contexts.append(
                ClaimInvestigationContext(
                    claim=claim.claim,
                    category=claim.category,
                    status=inv.status,
                    evidence_summary=inv.evidence_summary,
                )
            )
        if contexts:
            result[planned_topic.topic.value] = contexts

    return result


def resolve_investigation_context_for_topic(
    topic: InterviewTopic | None,
    context_map: dict[str, list[ClaimInvestigationContext]],
) -> list[ClaimInvestigationContext]:
    """Look up investigation contexts for a specific topic."""
    if topic is None or not context_map:
        return []
    return context_map.get(topic.value, [])
