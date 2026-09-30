"""Per-user interview ownership: user B must never reach user A's interview
just by knowing its UUID — for every interview route, without revealing that
the UUID exists (404, identical to a nonexistent id)."""

import uuid

import pytest
from sqlalchemy import select

from app.models.interview_session import InterviewSession
from app.models.user import User
from tests.auth_helpers import auth_app, sign_in
from tests.test_interview_api import VALID_CREATE_PAYLOAD

NOT_FOUND = "INTERVIEW_NOT_FOUND"


@pytest.fixture()
def world():
    with auth_app() as (make_client, session_factory, fake_redis):
        a, b = make_client(), make_client()
        user_a = sign_in(a, sub="sub-a", email="a@example.com", name="A").json()["data"]["user"]
        user_b = sign_in(b, sub="sub-b", email="b@example.com", name="B").json()["data"]["user"]
        yield {"a": a, "b": b, "user_a": user_a, "user_b": user_b, "sf": session_factory, "make_client": make_client}


def _create(client) -> str:
    response = client.post("/api/v1/interviews", json=VALID_CREATE_PAYLOAD)
    assert response.status_code == 201, response.text
    return response.json()["data"]["id"]


def _assert_not_found(response):
    assert response.status_code == 404, response.text
    assert response.json()["error"]["code"] == NOT_FOUND


def _owner_routes(session_id: str):
    """(method, path, kwargs) for every owner-protected interview route."""
    base = f"/api/v1/interviews/{session_id}"
    return [
        ("get", base, {}),
        ("post", f"{base}/start", {}),
        (
            "post",
            f"{base}/answers",
            {"json": {"question_id": str(uuid.uuid4()), "answer": "x"}, "headers": {"Idempotency-Key": "k" * 16}},
        ),
        ("post", f"{base}/complete", {}),
        ("get", f"{base}/evaluation", {}),
        ("get", f"{base}/result", {}),
        ("post", f"{base}/resume", {"files": {"resume": ("cv.pdf", b"%PDF-1.4 x", "application/pdf")}}),
    ]


# ---- creation ---------------------------------------------------------------


def test_new_interview_is_owned_by_the_authenticated_user(world):
    session_id = _create(world["a"])

    with world["sf"]() as db:
        row = db.get(InterviewSession, uuid.UUID(session_id))
        assert str(row.user_id) == world["user_a"]["id"]


def test_request_cannot_override_ownership(world):
    payload = {**VALID_CREATE_PAYLOAD, "user_id": world["user_b"]["id"], "owner_id": world["user_b"]["id"]}

    response = world["a"].post("/api/v1/interviews", json=payload)

    assert response.status_code == 201
    with world["sf"]() as db:
        row = db.get(InterviewSession, uuid.UUID(response.json()["data"]["id"]))
        assert str(row.user_id) == world["user_a"]["id"]


def test_creating_an_interview_requires_authentication(world):
    anonymous = world["make_client"]()
    response = anonymous.post("/api/v1/interviews", json=VALID_CREATE_PAYLOAD)
    assert response.status_code == 401
    with world["sf"]() as db:
        assert db.execute(select(InterviewSession)).first() is None


# ---- owner access -------------------------------------------------------------


def test_owner_can_access_their_own_interview(world):
    session_id = _create(world["a"])

    get_response = world["a"].get(f"/api/v1/interviews/{session_id}")
    start_response = world["a"].post(f"/api/v1/interviews/{session_id}/start")

    assert get_response.status_code == 200
    assert get_response.json()["data"]["session_id"] == session_id
    assert start_response.status_code == 200


# ---- cross-user access is denied on every route ----------------------------------


@pytest.mark.parametrize("index", range(7), ids=["get", "start", "answers", "complete", "evaluation", "result", "resume"])
def test_other_user_cannot_use_any_interview_route(world, index):
    session_id = _create(world["a"])
    method, path, kwargs = _owner_routes(session_id)[index]

    response = getattr(world["b"], method)(path, **kwargs)

    _assert_not_found(response)


def test_other_users_failed_attempts_do_not_change_the_interview(world):
    session_id = _create(world["a"])
    for method, path, kwargs in _owner_routes(session_id):
        getattr(world["b"], method)(path, **kwargs)

    with world["sf"]() as db:
        row = db.get(InterviewSession, uuid.UUID(session_id))
        assert row.status.value == "CREATED"
        assert str(row.user_id) == world["user_a"]["id"]


def test_uuid_guessing_is_indistinguishable_from_a_nonexistent_interview(world):
    real_id = _create(world["a"])
    missing_id = str(uuid.uuid4())

    for (method, path, kwargs), (_m, missing_path, missing_kwargs) in zip(
        _owner_routes(real_id), _owner_routes(missing_id)
    ):
        other = getattr(world["b"], method)(path, **kwargs)
        missing = getattr(world["b"], method)(missing_path, **missing_kwargs)
        assert (other.status_code, other.json()["error"]["code"]) == (
            missing.status_code,
            missing.json()["error"]["code"],
        )


def test_other_user_cannot_replay_an_idempotent_answer_response(world):
    """Ownership is checked before any idempotency lookup, so B gets a 404
    instead of A's stored response, even with A's exact Idempotency-Key."""
    session_id = _create(world["a"])
    question = world["a"].post(f"/api/v1/interviews/{session_id}/start").json()["data"]["question"]
    key = "shared-key-0123456789"
    answered = world["a"].post(
        f"/api/v1/interviews/{session_id}/answers",
        json={"question_id": question["id"], "answer": "my answer"},
        headers={"Idempotency-Key": key},
    )
    assert answered.status_code == 200

    stolen = world["b"].post(
        f"/api/v1/interviews/{session_id}/answers",
        json={"question_id": question["id"], "answer": "my answer"},
        headers={"Idempotency-Key": key},
    )

    _assert_not_found(stolen)


@pytest.mark.parametrize("index", range(7), ids=["get", "start", "answers", "complete", "evaluation", "result", "resume"])
def test_unauthenticated_requests_are_rejected(world, index):
    session_id = _create(world["a"])
    method, path, kwargs = _owner_routes(session_id)[index]
    anonymous = world["make_client"]()

    response = getattr(anonymous, method)(path, **kwargs)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_users_are_separate_rows(world):
    assert world["user_a"]["id"] != world["user_b"]["id"]
    with world["sf"]() as db:
        assert len(db.execute(select(User)).scalars().all()) == 2
