"""Task 19 — `KnowledgeChunk` must never silently belong to an invalid
role/topic/concept combination; it validates against the existing role
catalog at construction time."""

import uuid

import pytest

from app.domain.enums import Difficulty, InterviewTopic, Role
from app.knowledge.models import KnowledgeChunk, KnowledgeSearchResult


def test_valid_role_topic_concept_combination_constructs():
    chunk = KnowledgeChunk(
        role=Role.BACKEND_DEVELOPER,
        topic=InterviewTopic.DATABASES,
        concept="indexing",
        content="An index speeds up lookups at the cost of writes.",
    )

    assert chunk.role is Role.BACKEND_DEVELOPER
    assert chunk.topic is InterviewTopic.DATABASES
    assert chunk.concept == "indexing"
    assert isinstance(chunk.id, uuid.UUID)


def test_ai_engineer_rag_chunking_is_valid():
    chunk = KnowledgeChunk(
        role=Role.AI_ENGINEER,
        topic=InterviewTopic.RAG,
        concept="chunking",
        content="Chunking splits source documents for retrieval.",
    )

    assert chunk.topic is InterviewTopic.RAG


def test_invalid_role_topic_combination_is_rejected():
    # React is not a Backend Developer topic.
    with pytest.raises(ValueError, match="not valid for role"):
        KnowledgeChunk(
            role=Role.BACKEND_DEVELOPER,
            topic=InterviewTopic.REACT,
            concept="hooks",
            content="Should never construct.",
        )


def test_invalid_role_concept_combination_is_rejected():
    # "hooks" is a React concept, not a Databases concept — same role,
    # valid topic, invalid concept.
    with pytest.raises(ValueError, match="not valid for role"):
        KnowledgeChunk(
            role=Role.BACKEND_DEVELOPER,
            topic=InterviewTopic.DATABASES,
            concept="hooks",
            content="Should never construct.",
        )


def test_optional_metadata_defaults_are_empty_not_required():
    chunk = KnowledgeChunk(
        role=Role.JAVA_DEVELOPER,
        topic=InterviewTopic.COLLECTIONS,
        concept="iterators",
        content="An Iterator lets code traverse a collection safely.",
    )

    assert chunk.source is None
    assert chunk.title is None
    assert chunk.section is None
    assert chunk.difficulty is None
    assert chunk.tags == []


def test_metadata_fields_are_accepted_when_provided():
    chunk = KnowledgeChunk(
        role=Role.JAVA_DEVELOPER,
        topic=InterviewTopic.CONCURRENCY,
        concept="threads",
        content="A thread is an independent unit of execution.",
        source="seed",
        title="Threads 101",
        section="intro",
        difficulty=Difficulty.EASY,
        tags=["fundamentals"],
    )

    assert chunk.source == "seed"
    assert chunk.title == "Threads 101"
    assert chunk.difficulty is Difficulty.EASY
    assert chunk.tags == ["fundamentals"]


def test_empty_content_is_rejected():
    with pytest.raises(ValueError):
        KnowledgeChunk(role=Role.AI_ENGINEER, topic=InterviewTopic.RAG, concept="retrieval", content="")


def test_search_result_is_provider_neutral_and_immutable():
    result = KnowledgeSearchResult(
        content="Chunking splits source documents.",
        score=0.87,
        role=Role.AI_ENGINEER,
        topic=InterviewTopic.RAG,
        concept="chunking",
        metadata={"source": "seed"},
    )

    assert result.score == 0.87
    with pytest.raises(Exception):  # frozen model — attribute assignment must fail
        result.score = 0.5  # type: ignore[misc]
