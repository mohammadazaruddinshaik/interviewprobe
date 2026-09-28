import pytest
from pydantic import ValidationError

from app.domain.competencies import (
    ROLE_COMPETENCY_CATALOG,
    RoleCompetency,
    get_competency,
    get_role_competencies,
)
from app.domain.enums import CompetencyRequirement, InterviewTopic, Role
from app.domain.roles import get_concepts_for_topic, get_topics_for_role


def test_every_supported_role_has_a_competency_definition():
    for role in Role:
        assert role in ROLE_COMPETENCY_CATALOG


def test_catalog_contains_no_roles_beyond_the_supported_ones():
    assert set(ROLE_COMPETENCY_CATALOG) == set(Role)


def test_no_role_has_an_empty_competency_list():
    for role in Role:
        assert len(get_role_competencies(role)) >= 1


def test_competency_lists_stay_focused():
    for role in Role:
        assert 5 <= len(get_role_competencies(role)) <= 9, role


def test_competency_keys_are_unique_within_a_role():
    for role, competencies in ROLE_COMPETENCY_CATALOG.items():
        keys = [c.key for c in competencies]
        assert len(keys) == len(set(keys)), role


def test_suggested_orders_are_unique_and_contiguous_within_a_role():
    for role, competencies in ROLE_COMPETENCY_CATALOG.items():
        orders = sorted(c.suggested_order for c in competencies)
        assert orders == list(range(1, len(competencies) + 1)), role


def test_every_competency_is_anchored_to_one_of_its_roles_catalog_topics():
    for role, competencies in ROLE_COMPETENCY_CATALOG.items():
        role_topics = set(get_topics_for_role(role))
        for competency in competencies:
            assert competency.topic in role_topics, (role, competency.key)


def test_competency_concepts_reuse_existing_catalog_concepts():
    for role, competencies in ROLE_COMPETENCY_CATALOG.items():
        for competency in competencies:
            catalog_concepts = set(get_concepts_for_topic(role, competency.topic))
            assert set(competency.concepts) <= catalog_concepts, (role, competency.key)


def test_every_role_catalog_topic_is_reachable_through_some_competency():
    for role, competencies in ROLE_COMPETENCY_CATALOG.items():
        assert {c.topic for c in competencies} == set(get_topics_for_role(role)), role


def test_every_role_has_at_least_one_required_competency():
    for role in Role:
        requirements = {c.requirement for c in get_role_competencies(role)}
        assert CompetencyRequirement.REQUIRED in requirements, role


def test_competency_metadata_is_non_blank():
    for competencies in ROLE_COMPETENCY_CATALOG.values():
        for competency in competencies:
            assert competency.display_name.strip()
            assert competency.description.strip()


def test_catalogs_are_role_specific():
    ai_topics = {c.topic for c in get_role_competencies(Role.AI_ENGINEER)}
    backend_topics = {c.topic for c in get_role_competencies(Role.BACKEND_DEVELOPER)}

    assert InterviewTopic.RAG in ai_topics
    assert InterviewTopic.RAG not in backend_topics
    assert InterviewTopic.CACHING in backend_topics


def test_get_role_competencies_returns_suggested_order():
    orders = [c.suggested_order for c in get_role_competencies(Role.JAVA_DEVELOPER)]
    assert orders == sorted(orders)


def test_get_competency_looks_up_by_key_within_a_role():
    assert get_competency(Role.AI_ENGINEER, "retrieval_augmented_generation").topic is InterviewTopic.RAG
    assert get_competency(Role.BACKEND_DEVELOPER, "retrieval_augmented_generation") is None


def test_unknown_role_is_rejected():
    with pytest.raises(ValueError):
        Role("DATA_SCIENTIST")
    with pytest.raises(KeyError):
        get_role_competencies("DATA_SCIENTIST")  # type: ignore[arg-type]


def test_competency_is_immutable_and_key_must_be_a_slug():
    competency = get_role_competencies(Role.SDE)[0]
    with pytest.raises(ValidationError):
        competency.key = "changed"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        RoleCompetency(
            key="Not A Slug",
            topic=InterviewTopic.SYSTEM_DESIGN,
            display_name="x",
            description="x",
            requirement=CompetencyRequirement.REQUIRED,
            suggested_order=1,
        )
