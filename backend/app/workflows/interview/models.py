from typing import Literal

from pydantic import BaseModel, Field

from app.domain.enums import Difficulty, InterviewTopic, InterviewTopicStatus, QuestionType


class GeneratedQuestion(BaseModel):
    """LLM-proposed interview question. Structured-output target for the
    question-generation nodes — never hand-parsed from a raw string."""

    question: str = Field(min_length=1)
    topic: InterviewTopic
    difficulty: Difficulty
    question_type: QuestionType
    # A short, natural conversational remark spoken immediately before the
    # question — an acknowledgment, a reaction to the candidate's previous
    # answer, a transition, or (for the very first question) a brief
    # opening. Optional and deliberately unvalidated beyond length: this is
    # conversational flavor, not a structural decision the backend needs to
    # authorize the way it authorizes `topic`/action/sequencing — it is
    # never persisted to `interview_questions.question_text` and never
    # replayed on a resumed/refreshed session, exactly like a human
    # interviewer's spoken transition would not be.
    lead_in: str | None = Field(default=None, max_length=300)


class AnswerAnalysis(BaseModel):
    """LLM-proposed analysis of one candidate answer. Structured-output
    target for `analyze_answer`."""

    understanding: Literal["WEAK", "BASIC", "GOOD", "STRONG"]
    correctness: float = Field(ge=0, le=1)
    depth: float = Field(ge=0, le=1)
    concepts_demonstrated: list[str] = Field(default_factory=list)
    concepts_missing: list[str] = Field(default_factory=list)
    reasoning_quality: Literal["WEAK", "MODERATE", "STRONG"]
    needs_follow_up: bool


class NextAction(BaseModel):
    """The LLM/graph's *proposed* next workflow action.

    This is a proposal only — the graph never mutates PostgreSQL, Redis,
    or interview status. A future service-layer integration validates and
    executes it (enforces question limits, topic ordering, etc.).
    """

    action: Literal["FOLLOW_UP", "CLARIFY", "DEEP_DIVE", "CHALLENGE", "NEW_TOPIC", "END"]
    topic: InterviewTopic | None = None
    difficulty: Difficulty
    # Internal decision metadata only — persisted as `agent_reason` for
    # debugging/audit, never surfaced to the candidate (see
    # `_ACTION_TO_QUESTION_TYPE`/`QuestionResponse` — there is no API field
    # that exposes it). One short phrase naming why this action was chosen,
    # never a multi-step chain of thought.
    rationale: str = Field(
        min_length=1,
        description=(
            "One short internal phrase naming which decision criterion applied and why "
            "(e.g. 'demonstrated cache-aside pattern, probing invalidation next'). "
            "Concise audit metadata only — never shown to the candidate, never a "
            "multi-step chain of thought."
        ),
    )


class TopicState(BaseModel):
    """One planned topic's current progression status, as loaded from
    `interview_topics` — the minimum a decision needs to know about a
    topic, not the full persisted row."""

    topic: InterviewTopic
    status: InterviewTopicStatus
    sequence_number: int


class TopicTransition(BaseModel):
    """A *proposed* durable topic-status change: `from_topic` should
    become COMPLETED and `to_topic` should become IN_PROGRESS. Both None
    means no transition is needed for this turn. The graph only produces
    this — applying it to PostgreSQL is `TopicProgressionService`'s job.
    """

    from_topic: InterviewTopic | None = None
    to_topic: InterviewTopic | None = None


class DecisionContext(BaseModel):
    """Everything `validate_decision`/`fallback_decision` need to check a
    proposed `NextAction` — bundled so those functions take one argument
    instead of a long, easy-to-misorder parameter list."""

    current_topic: InterviewTopic | None
    difficulty: Difficulty
    question_number: int
    question_limit: int
    topics: list[TopicState] = Field(default_factory=list)


class ValidatedDecision(BaseModel):
    """The result of running a proposed `NextAction` through
    `validate_decision`: the (possibly corrected) action, the durable
    topic transition it implies, and whether a fallback was used."""

    action: NextAction
    topic_transition: TopicTransition = Field(default_factory=TopicTransition)
    fallback_used: bool = False
