from typing import TypedDict
from uuid import UUID

from app.domain.enums import Difficulty, InterviewTopic, Role
from app.knowledge.models import KnowledgeSearchResult
from app.workflows.interview.models import (
    AnswerAnalysis,
    GeneratedQuestion,
    NextAction,
    TopicState,
    TopicTransition,
)


class InterviewAgentState(TypedDict, total=False):
    """One turn's worth of working state — never the full transcript.

    PostgreSQL remains the durable transcript store; this only holds what
    a single graph invocation needs: the durable context for the current
    session (loaded fresh each invocation) plus whatever that invocation
    is actively producing. `total=False` because nodes populate this
    incrementally — no single node needs every field.
    """

    session_id: UUID

    # Durable context, loaded by `load_interview_context`.
    role: Role
    difficulty: Difficulty
    question_limit: int
    question_number: int
    current_topic: InterviewTopic | None
    current_question_id: UUID | None
    current_question: str | None
    topics: list[TopicState]

    # Supplied by the caller when invoking the answer graph.
    candidate_answer: str | None

    # Produced by the graph.
    answer_analysis: AnswerAnalysis | None
    proposed_action: NextAction | None  # raw LLM proposal, pre-validation
    next_action: NextAction | None  # final, validated decision
    topic_transition: TopicTransition | None
    decision_fallback_used: bool

    # Populated by `retrieve_knowledge` (Task 20) — provider-neutral
    # results only, bounded to a small top-k. Never the raw Qdrant
    # response, never an embedding vector, never the full transcript.
    retrieved_knowledge: list[KnowledgeSearchResult]

    generated_question: GeneratedQuestion | None
