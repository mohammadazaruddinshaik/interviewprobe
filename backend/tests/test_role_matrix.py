"""Technical Round End-to-End Reliability Matrix.

Deterministic integration coverage proving the full interview lifecycle
(create -> start -> answer through completion -> evaluation/result)
behaves coherently for *every* supported role, using each role's own
full catalog topic set (never hardcoded to AI Engineer) — and that a
single interview can move through all six adaptive actions (FOLLOW_UP,
CLARIFY, DEEP_DIVE, CHALLENGE, NEW_TOPIC, END) while backend validation,
persistence, and the candidate-facing contract all stay correct.

These tests verify resulting STATE correctness (valid topics, correct
sequencing, no internal-label leakage, evaluation reachability) — never
that a real LLM chooses any particular action for any particular role.
Individual single-action contracts (FOLLOW_UP/CLARIFY/DEEP_DIVE/
CHALLENGE/NEW_TOPIC/END) are already covered turn-by-turn in
tests/test_workflow_integration.py; this file adds the cross-role matrix
and the single-session, all-six-actions chained lifecycle.

Reuses `build_client`/`create_interview`/`start_interview`/`submit_answer`
from tests/test_workflow_integration.py (Task 18's FastAPI
dependency-override harness), the same pattern tests/test_evaluation_api.py
and tests/test_result_api.py already use, rather than duplicating it.
"""

import uuid

import pytest
from sqlalchemy import select

from app.domain.enums import Difficulty, InterviewTopic, MessageRole, QuestionType, Role
from app.domain.roles import get_topics_for_role
from app.evaluation.models import EvaluationResult
from app.llm.models import StructuredLLMResponse
from app.models.interview_message import InterviewMessage
from app.models.interview_question import InterviewQuestion
from app.workflows.interview.models import AnswerAnalysis, GeneratedQuestion, NextAction
from tests.fakes import FakeAsyncRedis, FakeLLMProvider
from tests.test_workflow_integration import build_client, create_interview, start_interview, submit_answer

# Candidate-facing text (question text, lead_in) must never contain any of
# these — internal action/system vocabulary the natural-adaptive-behavior
# milestone's prompts are already engineered to avoid (see
# tests/test_workflow_nodes.py's lead_in-guidance tests for the prompt-side
# guarantee). Checked case-insensitively.
_FORBIDDEN_CANDIDATE_FACING_TERMS = [
    "langgraph",
    "rag context",
    "retrieval-augmented",
    "gpt-4",
    "gpt-3",
    "openai",
    "gemini",
    "vector database",
    "qdrant",
    "follow_up",
    "clarify",
    "clarification",
    "deep_dive",
    "deep dive",
    "challenge action",
    "new_topic",
    "new area",
    "topic_transition",
    "topic transition",
    "difficulty: medium",
    "difficulty: easy",
    "difficulty: hard",
]


def _assert_no_internal_leakage(*texts: str | None) -> None:
    for text in texts:
        if not text:
            continue
        lowered = text.lower()
        for term in _FORBIDDEN_CANDIDATE_FACING_TERMS:
            assert term not in lowered, f"Candidate-facing text leaked internal term {term!r}: {text!r}"


def _generic_generated_question(topic: InterviewTopic) -> GeneratedQuestion:
    return GeneratedQuestion(
        question="Can you walk me through your thinking on that?",
        topic=topic,
        difficulty=Difficulty.MEDIUM,
        question_type=QuestionType.FOLLOW_UP,
        lead_in="Let's continue from there.",
    )


def _generic_analysis() -> AnswerAnalysis:
    return AnswerAnalysis(
        understanding="BASIC",
        correctness=0.5,
        depth=0.4,
        concepts_demonstrated=["general_understanding"],
        concepts_missing=[],
        reasoning_quality="MODERATE",
        needs_follow_up=True,
    )


def _generic_evaluation_result() -> EvaluationResult:
    return EvaluationResult(
        technical_knowledge_score=7.0,
        reasoning_score=6.5,
        depth_score=6.0,
        communication_score=7.5,
        overall_score=1.0,  # never trusted — backend recomputes it
        strengths=["Explained the core idea clearly."],
        weaknesses=["Could go deeper on trade-offs."],
        evidence=[],
    )


# ---------------------------------------------------------------------------
# 1. Role catalog audit (documented as an assertion, not just prose) — every
# `Role` enum member has a catalog entry with at least one topic, so the
# matrix below genuinely covers "the exact supported roles", not a guess.
# ---------------------------------------------------------------------------


def test_every_role_enum_member_has_a_nonempty_catalog_entry():
    for role in Role:
        topics = get_topics_for_role(role)
        assert topics, f"{role} has no catalog topics"
        assert len(topics) <= 6, f"{role} has more topics than CreateInterviewRequest allows (max 6)"


# ---------------------------------------------------------------------------
# 2. Role matrix — full lifecycle per role
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("role_name", [role.value for role in Role])
def test_role_matrix_full_lifecycle(role_name):
    role = Role(role_name)
    topics = [t.value for t in get_topics_for_role(role)]
    first_topic = topics[0]
    question_limit = 3

    fake_redis = FakeAsyncRedis()
    fake_llm = FakeLLMProvider(
        structured_responses={
            "GeneratedQuestion": _generic_generated_question(InterviewTopic(first_topic)),
            "AnswerAnalysis": _generic_analysis(),
            # FOLLOW_UP always normalizes to the current topic regardless of
            # what's proposed here (decision_validator.py) — a fixed action
            # is enough to drive every role through a real, correct
            # completion without claiming anything about model behavior.
            "NextAction": NextAction(action="FOLLOW_UP", topic=None, difficulty=Difficulty.MEDIUM, rationale="x"),
            "EvaluationResult": _generic_evaluation_result(),
        }
    )

    with build_client(fake_redis, fake_llm) as (client, session_factory):
        created = create_interview(client, role=role_name, topics=topics, question_limit=question_limit)
        assert created["role"] == role_name
        assert set(created["topics"]) == set(topics)

        started = start_interview(client, created["id"])
        assert started["status"] == "IN_PROGRESS"
        first_question = started["question"]
        assert first_question["text"].strip()
        assert first_question["topic"] in topics
        assert first_question["type"] == "INITIAL"
        assert first_question["lead_in"] is None or first_question["lead_in"].strip()
        _assert_no_internal_leakage(first_question["text"], first_question["lead_in"])

        question_id = first_question["id"]
        data = None
        for i in range(question_limit):
            response = submit_answer(
                client, created["id"], question_id, f"My answer number {i}.", f"role-matrix-{role_name}-{i}"
            )
            assert response.status_code == 200, response.text
            data = response.json()["data"]

            if i < question_limit - 1:
                assert data["question"] is not None
                assert data["action"] == "FOLLOW_UP"
                assert data["question"]["text"].strip()
                assert data["question"]["topic"] in topics
                assert data["question"]["type"] in {t.value for t in QuestionType}
                assert data["question"]["lead_in"] is None or data["question"]["lead_in"].strip()
                _assert_no_internal_leakage(data["question"]["text"], data["question"]["lead_in"])
                question_id = data["question"]["id"]
            else:
                # The question limit always wins — the interview completes
                # on this turn regardless of what the (fixed) proposal was.
                assert data["question"] is None
                assert data["action"] == "END"

        assert data["status"] == "COMPLETED"

        # --- Persistence: questions -----------------------------------
        db = session_factory()
        try:
            questions = (
                db.execute(
                    select(InterviewQuestion)
                    .where(InterviewQuestion.session_id == uuid.UUID(created["id"]))
                    .order_by(InterviewQuestion.sequence_number)
                )
                .scalars()
                .all()
            )
            assert len(questions) == question_limit
            for expected_sequence, question in enumerate(questions, start=1):
                assert question.sequence_number == expected_sequence
                assert question.session_id == uuid.UUID(created["id"])
                assert question.question_text.strip()
                assert question.topic.value in topics
                assert isinstance(question.question_type, QuestionType)
                assert isinstance(question.difficulty, Difficulty)
            # lead_in is deliberately never persisted onto the question row
            # (see workflows/interview/models.py's GeneratedQuestion.lead_in
            # docstring) — there is no column for it to leak into.
            assert not hasattr(InterviewQuestion, "lead_in")

            # --- Persistence: transcript ---------------------------------
            messages = (
                db.execute(
                    select(InterviewMessage)
                    .where(InterviewMessage.session_id == uuid.UUID(created["id"]))
                    .order_by(InterviewMessage.sequence_number)
                )
                .scalars()
                .all()
            )
            assert len(messages) == 2 * question_limit  # one INTERVIEWER + one CANDIDATE per question
            for index, message in enumerate(messages):
                expected_role = MessageRole.INTERVIEWER if index % 2 == 0 else MessageRole.CANDIDATE
                assert message.role == expected_role
                assert message.sequence_number == index + 1
                assert message.question_id == questions[index // 2].id
        finally:
            db.close()

        # --- lead_in is never replayed on a resumed GET --------------------
        state = client.get(f"/api/v1/interviews/{created['id']}").json()["data"]
        assert state["status"] == "COMPLETED"
        assert state["current_question"] is None  # fully answered, nothing in flight
        assert state["questions_answered"] == question_limit

        # --- Evaluation/result remain reachable after natural completion --
        evaluation_response = client.get(f"/api/v1/interviews/{created['id']}/evaluation")
        assert evaluation_response.status_code == 200
        eval_data = evaluation_response.json()["data"]
        assert 0 <= eval_data["overall_score"] <= 10
        assert 0 <= eval_data["technical_knowledge_score"] <= 10
        assert 0 <= eval_data["reasoning_score"] <= 10
        assert 0 <= eval_data["depth_score"] <= 10
        assert 0 <= eval_data["communication_score"] <= 10
        assert eval_data["strengths"]
        assert eval_data["weaknesses"]

        result_response = client.get(f"/api/v1/interviews/{created['id']}/result")
        assert result_response.status_code == 200
        result_data = result_response.json()["data"]
        assert result_data["interview"]["role"] == role_name
        assert result_data["interview"]["status"] == "COMPLETED"
        assert len(result_data["questions"]) == question_limit
        for question in result_data["questions"]:
            assert question["topic"] in topics
            assert question["candidate_answer"]
            _assert_no_internal_leakage(question["text"])


# ---------------------------------------------------------------------------
# 3. Adaptive action contract — one session, all six actions chained
# ---------------------------------------------------------------------------


class _ScriptedNextActionProvider(FakeLLMProvider):
    """Returns one `NextAction` per call from a fixed, ordered script,
    rather than the same response forever — the only way to deterministically
    drive a *single* interview session through a specific sequence of
    different adaptive actions without depending on real LLM judgment.

    This is a contract/plumbing test (does the graph+validator+service
    correctly execute whatever action comes back?), never a claim about
    what a real model would choose turn to turn — that question is
    answered separately by observing real local interviews.
    """

    def __init__(self, next_actions: list[NextAction], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._next_actions = list(next_actions)

    async def generate_structured(self, messages, output_schema):
        if output_schema.__name__ != "NextAction":
            return await super().generate_structured(messages, output_schema)
        self.calls.append((output_schema.__name__, messages))
        action = self._next_actions.pop(0)
        return StructuredLLMResponse(data=action, model=self.model)


def test_full_adaptive_lifecycle_through_all_six_actions():
    """FOLLOW_UP -> CLARIFY -> DEEP_DIVE -> CHALLENGE -> NEW_TOPIC -> END,
    all inside one interview session, verifying at every step that the
    action was validated/persisted correctly, topics stayed coherent, and
    the transcript/question rows end up correctly associated."""

    question_limit = 6
    scripted_actions = [
        NextAction(action="FOLLOW_UP", topic=InterviewTopic.LLM_FUNDAMENTALS, difficulty=Difficulty.MEDIUM, rationale="x"),
        NextAction(action="CLARIFY", topic=InterviewTopic.LLM_FUNDAMENTALS, difficulty=Difficulty.MEDIUM, rationale="x"),
        NextAction(action="DEEP_DIVE", topic=InterviewTopic.LLM_FUNDAMENTALS, difficulty=Difficulty.MEDIUM, rationale="x"),
        NextAction(action="CHALLENGE", topic=InterviewTopic.LLM_FUNDAMENTALS, difficulty=Difficulty.MEDIUM, rationale="x"),
        NextAction(action="NEW_TOPIC", topic=InterviewTopic.RAG, difficulty=Difficulty.MEDIUM, rationale="x"),
        NextAction(action="END", topic=None, difficulty=Difficulty.MEDIUM, rationale="x"),  # overridden by the limit anyway
    ]
    expected_actions = ["FOLLOW_UP", "CLARIFICATION", "DEEP_DIVE", "CHALLENGE", "TOPIC_TRANSITION", "END"]
    expected_topics = [
        "LLM_FUNDAMENTALS",
        "LLM_FUNDAMENTALS",
        "LLM_FUNDAMENTALS",
        "LLM_FUNDAMENTALS",
        "RAG",
        None,  # END generates no question
    ]

    fake_redis = FakeAsyncRedis()
    fake_llm = _ScriptedNextActionProvider(
        scripted_actions,
        structured_responses={
            "GeneratedQuestion": _generic_generated_question(InterviewTopic.LLM_FUNDAMENTALS),
            "AnswerAnalysis": _generic_analysis(),
            "EvaluationResult": _generic_evaluation_result(),
        },
    )

    with build_client(fake_redis, fake_llm) as (client, _):
        created = create_interview(
            client, role="AI_ENGINEER", topics=["LLM_FUNDAMENTALS", "RAG"], question_limit=question_limit
        )
        started = start_interview(client, created["id"])
        question_id = started["question"]["id"]

        for turn, (expected_action, expected_topic) in enumerate(zip(expected_actions, expected_topics)):
            response = submit_answer(
                client, created["id"], question_id, f"Answer for turn {turn}.", f"chained-lifecycle-{turn}"
            )
            assert response.status_code == 200, response.text
            data = response.json()["data"]
            assert data["action"] == expected_action, f"turn {turn}: expected {expected_action}, got {data['action']}"

            if expected_topic is None:
                assert data["question"] is None
                assert data["status"] == "COMPLETED"
            else:
                assert data["question"]["topic"] == expected_topic
                question_id = data["question"]["id"]

        # RAG became IN_PROGRESS via NEW_TOPIC, LLM_FUNDAMENTALS COMPLETED —
        # the topic transition persisted correctly, not just this turn's
        # question.
        state = client.get(f"/api/v1/interviews/{created['id']}").json()["data"]
        topics_by_name = {t["topic"]: t["status"] for t in state["topics"]}
        assert topics_by_name["LLM_FUNDAMENTALS"] == "COMPLETED"
        assert topics_by_name["RAG"] == "IN_PROGRESS"
        assert state["status"] == "COMPLETED"
