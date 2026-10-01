import ast
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import event

from app.domain.enums import Difficulty, InterviewStatus, InterviewTopic, InterviewTopicStatus, Role
from app.models.evaluation import Evaluation
from app.models.interview_session import InterviewSession
from app.models.interview_topic import InterviewTopicEntry
from app.repositories.dashboard_repository import DashboardRepository
from app.services.dashboard_service import DashboardService, compute_streak_days
from tests.auth_helpers import auth_app, sign_in

T = InterviewTopic
TS = InterviewTopicStatus
NOW = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)


def seed(
    db,
    user_id,
    *,
    status=InterviewStatus.COMPLETED,
    completed_at=None,
    created_at=None,
    topics=((T.RAG, TS.COMPLETED),),
    score=None,
    role=Role.AI_ENGINEER,
    question_limit=5,
):
    user_id = uuid.UUID(str(user_id))
    created_at = created_at or completed_at or NOW
    session = InterviewSession(
        user_id=user_id,
        role=role,
        difficulty=Difficulty.MEDIUM,
        status=status,
        question_limit=question_limit,
        created_at=created_at,
        completed_at=completed_at,
    )
    db.add(session)
    db.flush()
    for index, (topic, topic_status) in enumerate(topics, start=1):
        db.add(InterviewTopicEntry(session_id=session.id, topic=topic, sequence_number=index, status=topic_status))
    if score is not None:
        db.add(
            Evaluation(
                session_id=session.id,
                technical_knowledge_score=score,
                reasoning_score=score,
                depth_score=score,
                communication_score=score,
                overall_score=score,
                strengths=[],
                weaknesses=[],
                evidence=[],
            )
        )
    db.commit()
    return session


def day(days_ago, hour=10):
    return (NOW - timedelta(days=days_ago)).replace(hour=hour)


@pytest.fixture()
def world():
    with auth_app() as (make_client, session_factory, _redis):
        a, b = make_client(), make_client()
        user_a = sign_in(a, sub="sub-a", email="a@example.com", name="A").json()["data"]["user"]["id"]
        user_b = sign_in(b, sub="sub-b", email="b@example.com", name="B").json()["data"]["user"]["id"]
        yield {"a": a, "b": b, "ua": user_a, "ub": user_b, "sf": session_factory, "make_client": make_client}


def dashboard(client, **kwargs):
    response = client.get("/api/v1/dashboard", **kwargs)
    assert response.status_code == 200, response.text
    return response.json()["data"]


def service_for(db, user_id):
    return DashboardService(DashboardRepository(db, uuid.UUID(str(user_id))))


# ---- authentication -----------------------------------------------------------------


def test_unauthenticated_request_is_rejected(world):
    response = world["make_client"]().get("/api/v1/dashboard")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_empty_state(world):
    data = dashboard(world["a"])

    assert data["stats"] == {
        "completed_interviews": 0,
        "average_score": None,
        "completed_this_month": 0,
        "average_score_change": None,
        "topics_practiced": 0,
    }
    assert data["next_interview"] is None
    assert data["recent_interviews"] == []
    assert data["streak"]["days"] == 0
    assert len(data["streak"]["activity"]) == 7
    assert not any(item["active"] for item in data["streak"]["activity"])


# ---- isolation ------------------------------------------------------------------------


def _seed_two_users(world):
    now = datetime.now(UTC)
    with world["sf"]() as db:
        # User A
        seed(db, world["ua"], completed_at=now - timedelta(hours=2), score=8, topics=((T.RAG, TS.COMPLETED), (T.AI_AGENTS, TS.IN_PROGRESS)))
        seed(db, world["ua"], completed_at=now - timedelta(days=1), score=6, topics=((T.EMBEDDINGS_VECTOR_DB, TS.COMPLETED),))
        a_active = seed(db, world["ua"], status=InterviewStatus.IN_PROGRESS, created_at=now, topics=((T.LLM_EVALUATION, TS.IN_PROGRESS),))
        # User B
        seed(db, world["ub"], completed_at=now - timedelta(hours=1), score=3, role=Role.SDE, topics=((T.DATA_STRUCTURES_ALGORITHMS, TS.COMPLETED),))
        b_created = seed(db, world["ub"], status=InterviewStatus.CREATED, created_at=now, role=Role.SDE, topics=((T.DATA_STRUCTURES_ALGORITHMS, TS.PENDING),))
        return str(a_active.id), str(b_created.id)


def test_each_user_sees_only_their_own_data(world):
    a_active_id, b_created_id = _seed_two_users(world)

    a = dashboard(world["a"])
    b = dashboard(world["b"])

    assert a["stats"]["completed_interviews"] == 2
    assert a["stats"]["average_score"] == 7.0
    assert a["stats"]["topics_practiced"] == 4  # RAG, AI_AGENTS, EMBEDDINGS_VECTOR_DB, LLM_EVALUATION
    assert {r["role"] for r in a["recent_interviews"]} == {"AI_ENGINEER"}
    assert a["next_interview"]["id"] == a_active_id
    assert a["next_interview"]["status"] == "IN_PROGRESS"

    assert b["stats"]["completed_interviews"] == 1
    assert b["stats"]["average_score"] == 3.0
    assert b["stats"]["topics_practiced"] == 1  # the PENDING topic was never reached
    assert [r["role"] for r in b["recent_interviews"]] == ["SDE"]
    assert b["recent_interviews"][0]["topics"] == ["DATA_STRUCTURES_ALGORITHMS"]
    assert b["next_interview"]["id"] == b_created_id
    assert b["next_interview"]["status"] == "CREATED"


def test_user_id_in_query_or_body_cannot_change_scope(world):
    _seed_two_users(world)
    baseline = dashboard(world["a"])

    via_query = dashboard(world["a"], params={"user_id": world["ub"]})
    via_body = world["a"].request("GET", "/api/v1/dashboard", json={"user_id": world["ub"]})
    via_header = dashboard(world["a"], headers={"X-User-Id": world["ub"]})

    assert via_query == baseline
    assert via_body.status_code == 200 and via_body.json()["data"] == baseline
    assert via_header == baseline


def test_other_users_session_ids_never_appear(world):
    a_active_id, b_created_id = _seed_two_users(world)
    text_a = world["a"].get("/api/v1/dashboard").text
    text_b = world["b"].get("/api/v1/dashboard").text
    assert b_created_id not in text_a
    assert a_active_id not in text_b


# ---- unevaluated sessions, recent list ----------------------------------------------------


def test_unevaluated_completed_session_is_listed_but_not_averaged(world):
    with world["sf"]() as db:
        seed(db, world["ua"], completed_at=NOW - timedelta(days=400), score=9)
        seed(db, world["ua"], completed_at=NOW - timedelta(days=400, hours=1), score=None)

    data = dashboard(world["a"])

    assert data["stats"]["completed_interviews"] == 2
    assert data["stats"]["average_score"] == 9.0
    scores = sorted(r["overall_score"] if r["overall_score"] is not None else -1 for r in data["recent_interviews"])
    assert scores == [-1, 9.0]


def test_recent_interviews_are_bounded_sorted_and_ordered_topics(world):
    with world["sf"]() as db:
        for i in range(7):
            seed(db, world["ua"], completed_at=NOW - timedelta(days=500 + i), topics=((T.REST_APIS, TS.COMPLETED), (T.DATABASES, TS.COMPLETED), (T.CACHING, TS.COMPLETED)))
        # non-completed sessions are not "recent interviews"
        seed(db, world["ua"], status=InterviewStatus.FAILED, created_at=NOW)
        seed(db, world["ua"], status=InterviewStatus.CREATED, created_at=NOW)

    data = dashboard(world["a"])

    recent = data["recent_interviews"]
    assert len(recent) == 5
    assert [r["completed_at"] for r in recent] == sorted((r["completed_at"] for r in recent), reverse=True)
    assert all(r["status"] == "COMPLETED" for r in recent)
    assert recent[0]["topics"] == ["REST_APIS", "DATABASES", "CACHING"]
    assert data["stats"]["completed_interviews"] == 7


# ---- next interview ---------------------------------------------------------------------------


def test_next_interview_prefers_in_progress_then_latest_created(world):
    with world["sf"]() as db:
        older_in_progress = seed(db, world["ua"], status=InterviewStatus.IN_PROGRESS, created_at=NOW - timedelta(days=3))
        seed(db, world["ua"], status=InterviewStatus.CREATED, created_at=NOW)
        seed(db, world["ua"], status=InterviewStatus.COMPLETED, completed_at=NOW, score=5)
        expected = str(older_in_progress.id)

    assert dashboard(world["a"])["next_interview"]["id"] == expected


def test_next_interview_uses_latest_created_when_nothing_in_progress(world):
    with world["sf"]() as db:
        seed(db, world["ua"], status=InterviewStatus.CREATED, created_at=NOW - timedelta(days=2))
        latest = seed(db, world["ua"], status=InterviewStatus.CREATED, created_at=NOW - timedelta(days=1))
        seed(db, world["ua"], status=InterviewStatus.FAILED, created_at=NOW)
        expected = str(latest.id)

    next_interview = dashboard(world["a"])["next_interview"]

    assert next_interview["id"] == expected
    assert set(next_interview) == {"id", "role", "difficulty", "question_limit", "status"}
    # Planner-owned: a CREATED interview's internal placeholders are never reported.
    assert next_interview["difficulty"] is None and next_interview["question_limit"] is None


def test_next_interview_reports_runtime_values_once_in_progress(world):
    with world["sf"]() as db:
        seed(db, world["ua"], status=InterviewStatus.IN_PROGRESS, created_at=NOW)

    next_interview = dashboard(world["a"])["next_interview"]

    assert next_interview["difficulty"] == "MEDIUM" and next_interview["question_limit"] == 5


# ---- topics practiced ------------------------------------------------------------------------------


def test_topics_practiced_counts_distinct_reached_topics(world):
    with world["sf"]() as db:
        seed(db, world["ua"], completed_at=NOW, topics=((T.RAG, TS.COMPLETED), (T.AI_AGENTS, TS.IN_PROGRESS), (T.CSS, TS.PENDING)))
        seed(db, world["ua"], completed_at=NOW, topics=((T.RAG, TS.COMPLETED),))  # duplicate topic counts once

    assert dashboard(world["a"])["stats"]["topics_practiced"] == 2


# ---- months -------------------------------------------------------------------------------------------


def test_month_boundaries_and_score_change(world):
    with world["sf"]() as db:
        seed(db, world["ua"], completed_at=datetime(2026, 9, 30, 23, 59, 59, tzinfo=UTC), score=6)  # previous month
        seed(db, world["ua"], completed_at=datetime(2026, 10, 1, 0, 0, 0, tzinfo=UTC), score=9)  # current month
        seed(db, world["ua"], completed_at=datetime(2026, 8, 31, 23, 0, tzinfo=UTC), score=1)  # two months ago
        result = service_for(db, world["ua"]).get_dashboard(now=datetime(2026, 10, 1, 0, 0, 30, tzinfo=UTC))

    assert result.stats.completed_interviews == 3
    assert result.stats.completed_this_month == 1
    assert result.stats.average_score == pytest.approx(5.33, abs=0.01)
    assert result.stats.average_score_change == 0.5  # (9 - 6) / 6


def test_score_change_is_null_without_a_comparable_previous_month(world):
    with world["sf"]() as db:
        seed(db, world["ua"], completed_at=datetime(2026, 10, 2, tzinfo=UTC), score=8)
        only_current = service_for(db, world["ua"]).get_dashboard(now=NOW)
        seed(db, world["ub"], completed_at=datetime(2026, 9, 2, tzinfo=UTC), score=8)
        only_previous = service_for(db, world["ub"]).get_dashboard(now=NOW)
        seed(db, world["ua"], completed_at=datetime(2026, 9, 3, tzinfo=UTC), score=0)  # previous avg is 0 -> undefined
        zero_previous = service_for(db, world["ua"]).get_dashboard(now=NOW)

    assert only_current.stats.average_score_change is None
    assert only_previous.stats.average_score_change is None
    assert zero_previous.stats.average_score_change is None


def test_previous_month_wraps_across_the_year_boundary(world):
    with world["sf"]() as db:
        seed(db, world["ua"], completed_at=datetime(2025, 12, 20, tzinfo=UTC), score=5)
        seed(db, world["ua"], completed_at=datetime(2026, 1, 5, tzinfo=UTC), score=10)
        result = service_for(db, world["ua"]).get_dashboard(now=datetime(2026, 1, 15, tzinfo=UTC))

    assert result.stats.completed_this_month == 1
    assert result.stats.average_score_change == 1.0  # (10 - 5) / 5


# ---- streak ------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "active_days_ago, expected",
    [
        ([], 0),
        ([0], 1),
        ([1], 1),  # today not yet active, yesterday was: streak still alive
        ([2], 0),  # a full inactive day before today resets it
        ([0, 1, 2, 3], 4),
        ([0, 1, 3, 4, 5], 2),  # gap at day 2
        ([1, 2, 3], 3),
    ],
)
def test_compute_streak_days(active_days_ago, expected):
    today = NOW.date()
    assert compute_streak_days({today - timedelta(days=n) for n in active_days_ago}, today) == expected


def test_multiple_interviews_on_one_day_count_once(world):
    with world["sf"]() as db:
        for hour in (8, 12, 18):
            seed(db, world["ua"], completed_at=day(0, hour))
        seed(db, world["ua"], completed_at=day(1, 9))
        result = service_for(db, world["ua"]).get_dashboard(now=NOW)

    assert result.streak.days == 2
    assert result.stats.completed_interviews == 4
    assert [item.active for item in result.streak.activity] == [False] * 5 + [True, True]
    assert result.streak.activity[-1].date == NOW.date()
    assert result.streak.activity[0].date == NOW.date() - timedelta(days=6)


def test_streak_ignores_unfinished_and_other_users_activity(world):
    with world["sf"]() as db:
        seed(db, world["ub"], completed_at=day(0))
        seed(db, world["ua"], status=InterviewStatus.IN_PROGRESS, created_at=day(0))
        result = service_for(db, world["ua"]).get_dashboard(now=NOW)

    assert result.streak.days == 0


# ---- performance / architecture -------------------------------------------------------------------------------


def test_dashboard_uses_a_small_bounded_number_of_queries_and_no_transcript_tables(world):
    with world["sf"]() as db:
        for i in range(30):
            seed(db, world["ua"], completed_at=NOW - timedelta(days=i), score=7)
    statements: list[str] = []

    engine = world["sf"].kw["bind"]

    def capture(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", capture)
    try:
        dashboard(world["a"])
    finally:
        event.remove(engine, "before_cursor_execute", capture)

    assert len(statements) <= 10  # 2 for authentication + the dashboard queries, independent of history size
    joined = " ".join(statements).lower()
    assert "interview_questions" not in joined
    assert "interview_messages" not in joined


def test_dashboard_modules_do_not_depend_on_llm_evaluation_or_workflow_code():
    root = Path(__file__).resolve().parent.parent / "app"
    forbidden = ("app.llm", "app.evaluation", "app.workflows", "app.services.result_service", "app.knowledge")
    for relative in ("services/dashboard_service.py", "repositories/dashboard_repository.py", "api/routes/dashboard.py"):
        tree = ast.parse((root / relative).read_text())
        for node in ast.walk(tree):
            modules = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules = [node.module]
            for module in modules:
                assert not module.startswith(forbidden), f"{relative} imports {module}"


def test_openapi_documents_the_dashboard_endpoint():
    from app.main import app

    schema = app.openapi()
    operation = schema["paths"]["/api/v1/dashboard"]["get"]
    assert "401" in operation["responses"]
    assert "parameters" not in operation  # no user_id (or any) parameter
    dumped = str(schema["components"]["schemas"]["DashboardResponse"]) + str(schema["components"]["schemas"]["DashboardRecentInterview"])
    for internal in ("token_hash", "google_subject", "user_id", "updated_at", "version"):
        assert internal not in dumped


# ---- real PostgreSQL (skipped when unreachable; rolled back, nothing committed) ---------------------------


@pytest.fixture()
def pg_db():
    from sqlalchemy.exc import OperationalError
    from sqlalchemy.orm import Session

    from app.db.session import engine

    try:
        connection = engine.connect()
    except OperationalError as exc:
        pytest.skip(f"PostgreSQL is not reachable at the configured DATABASE_URL: {exc}")
        return
    trans = connection.begin()
    db = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield db
    finally:
        db.close()
        if trans.is_active:
            trans.rollback()
        connection.close()


def test_dashboard_queries_run_on_real_postgres(pg_db):
    from app.models.user import User

    user = User(google_subject=f"pg-test-{uuid.uuid4()}", email="pg@example.com", name="PG")
    other = User(google_subject=f"pg-test-{uuid.uuid4()}", email="pg2@example.com", name="PG2")
    pg_db.add_all([user, other])
    pg_db.flush()
    now = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)
    seed(pg_db, user.id, completed_at=now - timedelta(days=1, hours=2), score=8, topics=((T.RAG, TS.COMPLETED), (T.AI_AGENTS, TS.IN_PROGRESS)))
    seed(pg_db, user.id, completed_at=now - timedelta(days=1, hours=5), score=6)
    seed(pg_db, user.id, completed_at=datetime(2026, 9, 20, tzinfo=UTC), score=5, topics=((T.REST_APIS, TS.COMPLETED),))
    seed(pg_db, user.id, status=InterviewStatus.IN_PROGRESS, created_at=now)
    seed(pg_db, other.id, completed_at=now, score=1)

    result = DashboardService(DashboardRepository(pg_db, user.id)).get_dashboard(now=now)

    assert result.stats.completed_interviews == 3
    assert result.stats.completed_this_month == 2
    assert result.stats.average_score == pytest.approx(6.33, abs=0.01)
    assert result.stats.average_score_change == pytest.approx((7 - 5) / 5)
    assert result.stats.topics_practiced == 3
    assert result.next_interview is not None and result.next_interview.status == InterviewStatus.IN_PROGRESS
    assert len(result.recent_interviews) == 3
    assert result.streak.days == 1 and result.streak.activity[-2].active is True  # yesterday active, today not yet
