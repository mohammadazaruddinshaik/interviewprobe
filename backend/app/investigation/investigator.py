"""Provider-neutral claim investigator.

Follows the same ABC + LLM-implementation pattern as
``InterviewPlanner`` (``app/planning/planner.py``) — application code
depends on the ``ClaimInvestigator`` interface; the ``LLMClaimInvestigator``
implementation uses the existing ``LLMProvider.generate_structured``
abstraction.
"""

from abc import ABC, abstractmethod

from app.investigation.models import ClaimInvestigationResult, InvestigationEvidence
from app.investigation.prompts import build_investigation_messages
from app.llm.base import LLMProvider
from app.resume.models import ResumeClaim


class ClaimInvestigator(ABC):
    @abstractmethod
    async def investigate(
        self,
        claim: ResumeClaim,
        claim_id: str,
        evidence: list[InvestigationEvidence],
    ) -> ClaimInvestigationResult: ...


class LLMClaimInvestigator(ClaimInvestigator):
    def __init__(self, llm_provider: LLMProvider):
        self._llm_provider = llm_provider

    async def investigate(
        self,
        claim: ResumeClaim,
        claim_id: str,
        evidence: list[InvestigationEvidence],
    ) -> ClaimInvestigationResult:
        messages = build_investigation_messages(claim, claim_id, evidence)
        response = await self._llm_provider.generate_structured(
            messages, ClaimInvestigationResult
        )
        return response.data
