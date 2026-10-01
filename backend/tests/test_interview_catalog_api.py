import pytest
from fastapi.testclient import TestClient

from app.domain.enums import Role
from app.domain.roles import ROLE_CATALOG
from app.main import app
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
    assert set(body["data"]) == {"roles"}


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


def test_each_role_exposes_only_role_information(catalog):
    for role_entry in catalog["roles"]:
        assert set(role_entry) == {"value", "label", "description"}
        assert role_entry["description"] == ROLE_CATALOG[Role(role_entry["value"])].description


def test_catalog_exposes_no_candidate_configuration(catalog):
    # Difficulty, topics and the question ceiling are planner decisions, not candidate choices.
    assert set(catalog) == {"roles"}
    assert not {"difficulties", "question_limit", "topic_limit", "topics"} & set(_all_keys(catalog))


def test_internal_topic_catalog_still_serves_the_planner():
    # The per-role topic/competency catalog is unchanged; it is just no longer candidate-facing.
    for definition in ROLE_CATALOG.values():
        assert definition.topics


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
        "data", "roles", "value", "label", "description",
    }
    assert "set-cookie" not in response.headers
    assert "max-age" in response.headers["cache-control"]


def test_openapi_documents_the_public_catalog_endpoint():
    schema = app.openapi()
    operation = schema["paths"][URL]["get"]
    assert "401" not in operation["responses"]  # public
    assert "DataResponse_InterviewCatalogResponse_" in str(operation["responses"]["200"])
    assert set(schema["components"]["schemas"]["InterviewCatalogResponse"]["properties"]) == {"roles"}


def test_every_advertised_role_is_accepted_by_interview_creation(anonymous_client, catalog):
    """Consistency with the real creation path: each advertised role is accepted with just a role (one
    request per role, so the per-client creation rate limit is not exceeded)."""
    with auth_app() as (make_client, _session_factory, _redis):
        client = make_client()
        sign_in(client)
        for role_entry in catalog["roles"]:
            response = client.post("/api/v1/interviews", json={"role": role_entry["value"]})
            assert response.status_code == 201, (role_entry["value"], response.text)
