"""Provider-neutral data models for resume claim investigation.

Investigation is evidence collection — it tracks whether a candidate has
provided concrete technical evidence that supports a resume claim during
the interview.  It never determines whether a claim is "true" or "false",
never accuses, and never infers intent.

    InvestigationEvidence  →  investigator  →  ClaimInvestigationResult

``ClaimInvestigation`` is the persisted state per claim, updated after
each relevant interview turn.  ``ClaimInvestigationResult`` is the LLM
structured output schema (like ``AnswerAnalysis`` for answer analysis).
"""

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import ClaimInvestigationStatus


class InvestigationEvidence(BaseModel):
    """One Q&A pair from the interview transcript relevant to a claim."""

    model_config = ConfigDict(frozen=True)

    question_sequence: int
    question_text: str
    answer_text: str


class ClaimInvestigation(BaseModel):
    """Persisted investigation state for one resume claim, updated after
    each relevant interview turn.  Stored in the plan record's JSONB."""

    model_config = ConfigDict(extra="forbid")

    claim_id: str = Field(min_length=1)
    status: ClaimInvestigationStatus = ClaimInvestigationStatus.NOT_YET_ESTABLISHED
    evidence_summary: str = ""
    rationale: str = ""


class ClaimInvestigationContext(BaseModel):
    """Compact investigation context for question generation.

    Contains only what the interviewer needs to generate better questions —
    no internal claim IDs, no database IDs, no raw plan metadata.
    """

    model_config = ConfigDict(frozen=True)

    claim: str = Field(min_length=1)
    category: str | None = None
    status: ClaimInvestigationStatus
    evidence_summary: str


class ClaimInvestigationResult(BaseModel):
    """LLM-proposed investigation result for one resume claim.

    The ``generate_structured`` target for claim investigation — same
    role ``AnswerAnalysis`` plays for answer analysis.
    """

    claim_id: str = Field(min_length=1)
    status: ClaimInvestigationStatus
    evidence_summary: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
