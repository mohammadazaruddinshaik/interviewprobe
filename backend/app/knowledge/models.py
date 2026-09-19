from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.enums import Difficulty, InterviewTopic, Role
from app.domain.roles import InvalidRoleTopicError, InvalidTopicConceptError, validate_role_topic_concept


class KnowledgeChunk(BaseModel):
    """One piece of role/topic/concept-scoped technical knowledge, before
    it is embedded and upserted into the vector store.

    Validated against the existing role catalog at construction time
    (`validate_role_topic_concept`) — a chunk can never silently belong to
    a role/topic/concept combination the catalog doesn't recognize. This
    is deliberately a *different* thing from `InterviewTopicEntry`: a
    chunk describes catalog-scoped technical knowledge, never a specific
    candidate's interview state.
    """

    id: UUID = Field(default_factory=uuid4)
    role: Role
    topic: InterviewTopic
    concept: str = Field(min_length=1)
    content: str = Field(min_length=1)

    # Optional metadata — only what Task 19 actually asks for, not
    # speculative future fields.
    source: str | None = None
    title: str | None = None
    section: str | None = None
    difficulty: Difficulty | None = None
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_against_role_catalog(self) -> "KnowledgeChunk":
        try:
            validate_role_topic_concept(self.role, self.topic, self.concept)
        except (InvalidRoleTopicError, InvalidTopicConceptError) as exc:
            raise ValueError(str(exc)) from exc
        return self


class KnowledgeSearchResult(BaseModel):
    """Provider-neutral retrieval result — the same shape regardless of
    which vector store produced it. No raw Qdrant (or other SDK) response
    object is ever exposed outside the knowledge-infrastructure layer;
    this is the only shape callers see."""

    model_config = ConfigDict(frozen=True)

    content: str
    score: float
    role: Role
    topic: InterviewTopic
    concept: str
    metadata: dict[str, Any] = Field(default_factory=dict)
