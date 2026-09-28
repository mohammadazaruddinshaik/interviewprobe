"""The provider-neutral structured resume schema — the `generate_structured`
target for resume parsing (see app/resume/parser.py), the same role
`EvaluationResult` plays for evaluation (app/evaluation/models.py).

Every field is optional/defaults to empty: a real resume rarely states
everything here, and the LLM is explicitly instructed (app/resume/prompts.py)
to leave a field null/empty rather than invent a value for it. Nothing in
this module is trusted for persistence until it has passed through
`app.resume.validator.validate_and_normalize_profile` — this module only
defines the shape.
"""

from pydantic import BaseModel, Field


class ResumeCandidateInfo(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None


class ResumeEducationEntry(BaseModel):
    institution: str | None = None
    degree: str | None = None
    field: str | None = None
    start: str | None = None
    end: str | None = None


class ResumeExperienceEntry(BaseModel):
    company: str | None = None
    title: str | None = None
    start: str | None = None
    end: str | None = None
    description: str | None = None


class ResumeProjectEntry(BaseModel):
    name: str | None = None
    description: str | None = None
    technologies: list[str] = Field(default_factory=list)


# A concrete, checkable statement the candidate made about themselves —
# the raw material a later interview phase can probe ("you said you built
# a RAG pipeline with Qdrant — walk me through that"). Deliberately has no
# true/false/verified field: at this stage a claim is only ever what the
# candidate reported, never something this phase judges or scores.
class ResumeClaim(BaseModel):
    claim: str = Field(min_length=1)
    category: str | None = None
    source: str | None = None
    evidence: str | None = None


class ResumeProfile(BaseModel):
    candidate: ResumeCandidateInfo = Field(default_factory=ResumeCandidateInfo)
    summary: str | None = None
    education: list[ResumeEducationEntry] = Field(default_factory=list)
    experience: list[ResumeExperienceEntry] = Field(default_factory=list)
    projects: list[ResumeProjectEntry] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    claims: list[ResumeClaim] = Field(default_factory=list)
