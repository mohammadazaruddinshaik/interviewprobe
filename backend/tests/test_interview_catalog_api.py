import pytest
from fastapi.testclient import TestClient

from app.domain.enums import Difficulty, InterviewTopic, Role
from app.domain.roles import ROLE_CATALOG
from app.main import app
from app.schemas.interview import CreateInterviewRequest
from tests.auth_helpers import auth_app, sign_in

URL = "/api/v1/interviews/catalog"


@pytest.fixture(scope="module")
def anonymous_client():
    with TestClient(app) as client:  # no cookie, no dependency overrides: proves the endpoint is public
        yield client


@pytest.fixture(scope="module")
def catalog(anonymous_client):
    response = anonymous_client.get(URL)
    assert response.status_code == 200
    return response.json()["data"]


def test_catalog_is_public_and_uses_the_data_envelope(anonymous_client):
    response = anonymous_client.get(URL)

    assert response.status_code == 200
    body = response.json()
    assert list(body) == ["data"]
    assert set(body["data"]) == {"roles", "difficulties", "question_limit", "topic_limit"}


def test_catalog_is_not_shadowed_by_the_interview_id_route(anonymous_client):
    # "/catalog" must not be parsed as a UUID session id (422) or demand auth (401).
    assert anonymous_client.get(URL).status_code == 200
    assert anonymous_client.get("/api/v1/interviews/not-a-uuid").status_code in (401, 422)


def test_roles_match_the_existing_role_catalog_exactly_and_in_order(catalog):
    assert [r["value"] for r in catalog["roles"]] == [role.value for role in ROLE_CATALOG]
    assert {r["value"] for r in catalog["roles"]} == {role.value for role in Role}
    assert len(catalog["roles"]) == 7
    labels = {r["value"]: r["label"] for r in catalog["roles"]}
    assert labels == {role.value: definition.display_name for role, definition in ROLE_CATALOG.items()}
    assert "ML_ENGINEER" not in labels


def test_each_role_exposes_only_its_own_topics_with_catalog_labels(catalog):
    for role_entry in catalog["roles"]:
        definition = ROLE_CATALOG[Role(role_entry["value"])]
        assert role_entry["description"] == definition.description
        assert [t["value"] for t in role_entry["topics"]] == [t.topic.value for t in definition.topics]
        assert [t["label"] for t in role_entry["topics"]] == [t.display_name for t in definition.topics]
        assert [t["description"] for t in role_entry["topics"]] == [t.description for t in definition.topics]
    by_role = {r["value"]: {t["value"] for t in r["topics"]} for r in catalog["roles"]}
    assert "REACT" in by_role["FRONTEND_DEVELOPER"] and "REACT" not in by_role["BACKEND_DEVELOPER"]
    assert "CORE_JAVA" not in by_role["AI_ENGINEER"]


def test_difficulties_match_the_enum(catalog):
    assert catalog["difficulties"] == [{"value": d.value} for d in Difficulty]


def test_limits_match_the_creation_request_validation(catalog):
    # Probe the real validation instead of repeating its numbers.
    valid = {"role": "AI_ENGINEER", "difficulty": "EASY", "topics": ["RAG"]}
    low, high = catalog["question_limit"]["min"], catalog["question_limit"]["max"]
    CreateInterviewRequest(**valid, question_limit=low)
    CreateInterviewRequest(**valid, question_limit=high)
    with pytest.raises(ValueError):
        CreateInterviewRequest(**valid, question_limit=low - 1)
    with pytest.raises(ValueError):
        CreateInterviewRequest(**valid, question_limit=high + 1)

    t_low, t_high = catalog["topic_limit"]["min"], catalog["topic_limit"]["max"]
    topics = list(InterviewTopic)
    CreateInterviewRequest(role="AI_ENGINEER", difficulty="EASY", question_limit=low, topics=topics[:t_low])
    CreateInterviewRequest(role="AI_ENGINEER", difficulty="EASY", question_limit=low, topics=topics[:t_high])
    with pytest.raises(ValueError):
        CreateInterviewRequest(role="AI_ENGINEER", difficulty="EASY", question_limit=low, topics=topics[: t_high + 1])
    with pytest.raises(ValueError):
        CreateInterviewRequest(role="AI_ENGINEER", difficulty="EASY", question_limit=low, topics=[])


def _all_keys(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from _all_keys(value)
    elif isinstance(node, list):
        for item in node:
            yield from _all_keys(item)


def test_response_contains_no_user_or_session_fields_and_is_cacheable(anonymous_client):
    response = anonymous_client.get(URL)

    assert set(_all_keys(response.json())) == {
        "data", "roles", "difficulties", "question_limit", "topic_limit",
        "value", "label", "description", "topics", "min", "max",
    }
    assert "set-cookie" not in response.headers
    assert "max-age" in response.headers["cache-control"]


def test_openapi_documents_the_public_catalog_endpoint():
    schema = app.openapi()
    operation = schema["paths"][URL]["get"]
    assert "401" not in operation["responses"]  # public
    assert "DataResponse_InterviewCatalogResponse_" in str(operation["responses"]["200"])
    assert {"roles", "difficulties", "question_limit", "topic_limit"} <= set(
        schema["components"]["schemas"]["InterviewCatalogResponse"]["properties"]
    )


def test_every_advertised_role_and_topic_combination_is_accepted_by_interview_creation(anonymous_client, catalog):
    """Consistency with the real creation path: each role, created with ALL of its advertised
    topics and the advertised minimum question limit, is accepted (one request per role, so
    the per-client creation rate limit is not exceeded)."""
    with auth_app() as (make_client, _session_factory, _redis):
        client = make_client()
        sign_in(client)
        for role_entry in catalog["roles"]:
            response = client.post(
                "/api/v1/interviews",
                json={
                    "role": role_entry["value"],
                    "difficulty": catalog["difficulties"][0]["value"],
                    "topics": [t["value"] for t in role_entry["topics"]],
                    "question_limit": catalog["question_limit"]["min"],
                },
            )
            assert response.status_code == 201, (role_entry["value"], response.text)


def test_a_topic_outside_the_advertised_role_topics_is_rejected_by_creation(catalog):
    frontend = next(r for r in catalog["roles"] if r["value"] == "FRONTEND_DEVELOPER")
    backend_only = next(
        t["value"]
        for r in catalog["roles"]
        if r["value"] == "BACKEND_DEVELOPER"
        for t in r["topics"]
        if t["value"] not in {x["value"] for x in frontend["topics"]}
    )
    with auth_app() as (make_client, _session_factory, _redis):
        client = make_client()
        sign_in(client)
        response = client.post(
            "/api/v1/interviews",
            json={"role": "FRONTEND_DEVELOPER", "difficulty": "EASY", "topics": [backend_only], "question_limit": 5},
        )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_ROLE_TOPIC"
