import pytest

from app.domain.enums import InterviewTopic, Role
from app.domain.roles import (
    ROLE_CATALOG,
    ConceptDefinition,
    InvalidRoleTopicError,
    InvalidTopicConceptError,
    RoleDefinition,
    TopicDefinition,
    get_concepts_for_topic,
    get_role_definition,
    get_topic_definition,
    get_topics_for_role,
    is_concept_valid_for_topic,
    is_topic_valid_for_role,
    validate_role_topic_concept,
    validate_role_topics,
)

# ---------------------------------------------------------------------------
# Role definitions
# ---------------------------------------------------------------------------


def test_all_supported_roles_have_a_catalog_entry():
    for role in Role:
        assert role in ROLE_CATALOG


def test_each_role_definition_has_a_non_empty_display_name_and_description():
    for role, definition in ROLE_CATALOG.items():
        assert isinstance(definition, RoleDefinition)
        assert definition.role is role
        assert definition.display_name.strip() != ""
        assert definition.description.strip() != ""


def test_each_role_has_at_least_one_topic():
    for role, definition in ROLE_CATALOG.items():
        assert len(definition.topics) >= 1


def test_display_names_are_human_readable_and_distinct_from_machine_values():
    # e.g. machine value "BACKEND_DEVELOPER" vs display name "Backend Developer"
    for definition in ROLE_CATALOG.values():
        assert definition.display_name != definition.role.value
        assert " " in definition.display_name or definition.display_name.istitle()


def test_topic_definitions_have_valid_metadata():
    for definition in ROLE_CATALOG.values():
        for topic_def in definition.topics:
            assert isinstance(topic_def, TopicDefinition)
            assert isinstance(topic_def.topic, InterviewTopic)
            assert topic_def.display_name.strip() != ""
            assert topic_def.description.strip() != ""


def test_concept_definitions_are_valid():
    for definition in ROLE_CATALOG.values():
        for topic_def in definition.topics:
            for concept_def in topic_def.concepts:
                assert isinstance(concept_def, ConceptDefinition)
                assert concept_def.concept.strip() != ""
                assert concept_def.display_name.strip() != ""
                assert concept_def.description.strip() != ""


def test_each_topic_has_at_least_one_concept():
    for definition in ROLE_CATALOG.values():
        for topic_def in definition.topics:
            assert len(topic_def.concepts) >= 1, f"{topic_def.topic} has no concepts"


def test_no_topic_is_duplicated_within_a_single_role():
    for role, definition in ROLE_CATALOG.items():
        topics = [t.topic for t in definition.topics]
        assert len(topics) == len(set(topics)), f"{role} has duplicate topics"


def test_get_role_definition_returns_the_matching_entry():
    definition = get_role_definition(Role.JAVA_DEVELOPER)

    assert definition.role is Role.JAVA_DEVELOPER
    assert definition.display_name == "Java Developer"


# ---------------------------------------------------------------------------
# Preserving the existing AI Engineer topics (must not be renamed/removed)
# ---------------------------------------------------------------------------


def test_ai_engineer_topics_match_the_original_six_used_throughout_the_workflow():
    assert set(get_topics_for_role(Role.AI_ENGINEER)) == {
        InterviewTopic.LLM_FUNDAMENTALS,
        InterviewTopic.RAG,
        InterviewTopic.EMBEDDINGS_VECTOR_DB,
        InterviewTopic.AI_AGENTS,
        InterviewTopic.LLM_EVALUATION,
        InterviewTopic.AI_SYSTEM_DESIGN,
    }


# ---------------------------------------------------------------------------
# get_topics_for_role
# ---------------------------------------------------------------------------


def test_get_topics_for_role_returns_only_that_roles_topics():
    frontend_topics = set(get_topics_for_role(Role.FRONTEND_DEVELOPER))
    backend_topics = set(get_topics_for_role(Role.BACKEND_DEVELOPER))

    assert InterviewTopic.REACT in frontend_topics
    assert InterviewTopic.REST_APIS not in frontend_topics

    assert InterviewTopic.REST_APIS in backend_topics
    assert InterviewTopic.REACT not in backend_topics


def test_get_topics_for_role_matches_catalog_topic_count():
    for role, definition in ROLE_CATALOG.items():
        assert len(get_topics_for_role(role)) == len(definition.topics)


# ---------------------------------------------------------------------------
# get_topic_definition / is_topic_valid_for_role
# ---------------------------------------------------------------------------


def test_get_topic_definition_returns_none_for_a_topic_outside_the_role():
    assert get_topic_definition(Role.BACKEND_DEVELOPER, InterviewTopic.REACT) is None


def test_get_topic_definition_returns_metadata_for_a_valid_combination():
    definition = get_topic_definition(Role.JAVA_DEVELOPER, InterviewTopic.COLLECTIONS)

    assert definition is not None
    assert definition.topic is InterviewTopic.COLLECTIONS
    assert definition.display_name == "Collections"


def test_is_topic_valid_for_role():
    assert is_topic_valid_for_role(Role.FRONTEND_DEVELOPER, InterviewTopic.CSS) is True
    assert is_topic_valid_for_role(Role.FRONTEND_DEVELOPER, InterviewTopic.SPRING) is False


# ---------------------------------------------------------------------------
# validate_role_topics — valid combinations
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "role,topics",
    [
        (Role.FRONTEND_DEVELOPER, [InterviewTopic.REACT]),
        (Role.BACKEND_DEVELOPER, [InterviewTopic.REST_APIS]),
        (Role.AI_ENGINEER, [InterviewTopic.RAG]),
        (Role.JAVA_DEVELOPER, [InterviewTopic.COLLECTIONS]),
        (Role.FRONTEND_DEVELOPER, [InterviewTopic.JAVASCRIPT, InterviewTopic.REACT, InterviewTopic.CSS]),
    ],
)
def test_validate_role_topics_accepts_valid_combinations(role, topics):
    validate_role_topics(role, topics)  # must not raise


# ---------------------------------------------------------------------------
# validate_role_topics — invalid combinations
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "role,topics",
    [
        (Role.BACKEND_DEVELOPER, [InterviewTopic.REACT]),
        (Role.FRONTEND_DEVELOPER, [InterviewTopic.DATABASES]),
        (Role.JAVA_DEVELOPER, [InterviewTopic.RAG]),
        (Role.AI_ENGINEER, [InterviewTopic.SPRING]),
    ],
)
def test_validate_role_topics_rejects_invalid_combinations(role, topics):
    with pytest.raises(InvalidRoleTopicError):
        validate_role_topics(role, topics)


def test_validate_role_topics_rejects_a_mix_of_valid_and_invalid_topics():
    with pytest.raises(InvalidRoleTopicError):
        validate_role_topics(Role.BACKEND_DEVELOPER, [InterviewTopic.REST_APIS, InterviewTopic.REACT])


def test_validate_role_topics_error_message_names_the_invalid_topic():
    with pytest.raises(InvalidRoleTopicError, match="REACT"):
        validate_role_topics(Role.BACKEND_DEVELOPER, [InterviewTopic.REACT])


def test_validate_role_topics_accepts_empty_list():
    validate_role_topics(Role.BACKEND_DEVELOPER, [])  # nothing to reject


# ---------------------------------------------------------------------------
# Purity — no database, Redis, LLM, or HTTP dependency
# ---------------------------------------------------------------------------


def test_role_catalog_module_has_no_infrastructure_imports():
    import app.domain.roles as roles_module
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(roles_module))
    imported_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])

    forbidden = {"redis", "sqlalchemy", "fastapi", "httpx", "openai", "requests"}
    assert not (imported_roots & forbidden), imported_roots & forbidden


def test_validate_role_topics_is_deterministic_and_side_effect_free():
    topics = [InterviewTopic.RAG, InterviewTopic.AI_AGENTS]
    # Calling it repeatedly must produce the same result and must not
    # mutate its inputs.
    validate_role_topics(Role.AI_ENGINEER, topics)
    validate_role_topics(Role.AI_ENGINEER, topics)
    assert topics == [InterviewTopic.RAG, InterviewTopic.AI_AGENTS]


# ---------------------------------------------------------------------------
# Task 19 — concept-level validation (built on top of the existing
# role/topic catalog, not a parallel/duplicated concept catalog)
# ---------------------------------------------------------------------------


def test_get_concepts_for_topic_returns_the_catalog_concepts():
    concepts = get_concepts_for_topic(Role.BACKEND_DEVELOPER, InterviewTopic.DATABASES)

    assert concepts == ["indexing", "transactions", "normalization"]


def test_get_concepts_for_topic_empty_for_a_topic_not_in_the_role():
    assert get_concepts_for_topic(Role.BACKEND_DEVELOPER, InterviewTopic.REACT) == []


def test_is_concept_valid_for_topic_true_for_a_real_concept():
    assert is_concept_valid_for_topic(Role.AI_ENGINEER, InterviewTopic.RAG, "chunking") is True


def test_is_concept_valid_for_topic_false_for_a_mismatched_concept():
    # "hooks" is a React concept, not a RAG concept.
    assert is_concept_valid_for_topic(Role.AI_ENGINEER, InterviewTopic.RAG, "hooks") is False


def test_validate_role_topic_concept_accepts_a_valid_combination():
    validate_role_topic_concept(Role.FRONTEND_DEVELOPER, InterviewTopic.REACT, "hooks")  # does not raise


def test_validate_role_topic_concept_accepts_none_concept():
    # concept=None means "topic-level filtering only" — no concept check.
    validate_role_topic_concept(Role.FRONTEND_DEVELOPER, InterviewTopic.REACT, None)


def test_validate_role_topic_concept_rejects_invalid_topic_for_role():
    with pytest.raises(InvalidRoleTopicError):
        validate_role_topic_concept(Role.BACKEND_DEVELOPER, InterviewTopic.REACT, None)


def test_validate_role_topic_concept_rejects_invalid_concept_for_valid_topic():
    with pytest.raises(InvalidTopicConceptError, match="hooks"):
        validate_role_topic_concept(Role.BACKEND_DEVELOPER, InterviewTopic.DATABASES, "hooks")
