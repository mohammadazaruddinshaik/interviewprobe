from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.enums import Difficulty, InterviewTopic, QuestionType, Role


class EvidenceItem(BaseModel):
    """One LLM-proposed piece of evidence for a strength/weakness claim.

    `question_id` is deliberately a loose string, not a `UUID` field: a
    malformed or hallucinated value must never fail structured-output
    parsing. It is validated against the interview's real question IDs
    afterward (see `validator.py`) and normalized away if it doesn't
    match — never trusted directly, never persisted as an invented
    reference.
    """

    question_id: str | None = None
    topic: InterviewTopic | None = None
    claim: str = Field(min_length=1)
    evidence: str = Field(min_length=1)


class EvaluationResult(BaseModel):
    """LLM-proposed structured evaluation — the `generate_structured`
    target for the evaluation prompt.

    `overall_score` is accepted here for schema completeness (the model
    is asked to produce one), but it is never trusted for persistence:
    the backend always recomputes it deterministically from the four
    component scores (see `validator.validate_and_normalize`).
    """

    technical_knowledge_score: float = Field(ge=0, le=10)
    reasoning_score: float = Field(ge=0, le=10)
    depth_score: float = Field(ge=0, le=10)
    communication_score: float = Field(ge=0, le=10)
    overall_score: float = Field(ge=0, le=10)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)


class EvaluationQuestionAnswer(BaseModel):
    """One (question, candidate answer) pair — the evaluator's basic unit
    of evidence. `candidate_answer` is `None` for a question the
    candidate never got to answer (e.g. the interview was ended via the
    explicit `/complete` endpoint before answering it)."""

    question_id: UUID
    sequence: int
    topic: InterviewTopic
    difficulty: Difficulty
    question_type: QuestionType
    question_text: str
    candidate_answer: str | None = None


class EvaluationContext(BaseModel):
    """Structured evaluation input, built entirely from persisted
    PostgreSQL state (never Redis, never Qdrant) — the evaluator's
    evidence kept as typed, structured data rather than one concatenated
    transcript string."""

    session_id: UUID
    role: Role
    difficulty: Difficulty
    topics: list[InterviewTopic]
    question_limit: int
    turns: list[EvaluationQuestionAnswer]


class ValidatedEvaluation(BaseModel):
    """The backend-validated, ready-to-persist evaluation.

    Scores are guaranteed finite and in [0, 10]; `overall_score` is the
    deterministic backend calculation (never the LLM's proposal);
    strengths/weaknesses/evidence are cleaned (non-empty, bounded count)
    and evidence question IDs are guaranteed to reference real questions
    from this interview, or to be absent.
    """

    technical_knowledge_score: float
    reasoning_score: float
    depth_score: float
    communication_score: float
    overall_score: float
    strengths: list[str]
    weaknesses: list[str]
    evidence: list[dict]
