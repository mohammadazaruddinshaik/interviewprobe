import uuid

import pytest

from app.domain.enums import (
    Difficulty,
    InterviewStatus,
    InterviewTopic,
    InterviewTopicStatus,
    QuestionType,
    Role,
)
from app.llm.exceptions import LLMTimeoutError
from app.models.interview_question import InterviewQuestion
from app.models.interview_session import InterviewSession
from app.models.interview_topic import InterviewTopicEntry
from app.workflows.interview.graph import (
    InterviewWorkflow,
    build_answer_graph,
    build_initial_question_graph,
)
from app.workflows.interview.models import AnswerAnalysis, GeneratedQuestion, NextAction
from tests.fakes import FakeInterviewRepository, FakeLLMProvider


def make_session(**overrides) -> InterviewSession:
    defaults = dict(
        id=uuid.uuid4(),
        role=Role.AI_ENGINEER,
        difficulty=Difficulty.MEDIUM,
        status=InterviewStatus.IN_PROGRESS,
        question_limit=5,
        current_question_number=1,
        version=2,
    )
    defaults.update(overrides)
    return InterviewSession(**defaults)


def make_topic(session_id, topic, sequence_number, status=InterviewTopicStatus.PENDING) -> InterviewTopicEntry:
    # `status` is set explicitly — these are plain Python objects, never
    # flushed through SQLAlchemy, so the column's `default=` never applies.
    return InterviewTopicEntry(
        id=uuid.uuid4(),
        session_id=session_id,
        topic=topic,
        sequence_number=sequence_number,
        status=status,
    )


def make_question(session_id, **overrides) -> InterviewQuestion:
    defaults = dict(
        id=uuid.uuid4(),
        session_id=session_id,
        sequence_number=1,
        question_text="Explain RAG.",
        topic=InterviewTopic.RAG,
        difficulty=Difficulty.MEDIUM,
        question_type=QuestionType.INITIAL,
    )
    defaults.update(overrides)
    return InterviewQuestion(**defaults)


SAMPLE_GENERATED_QUESTION = GeneratedQuestion(
    question="Explain how LLMs generate text.",
    topic=InterviewTopic.LLM_FUNDAMENTALS,
    difficulty=Difficulty.MEDIUM,
    question_type=QuestionType.INITIAL,
)


def analysis(needs_follow_up: bool) -> AnswerAnalysis:
    return AnswerAnalysis(
        understanding="BASIC",
        correctness=0.5,
        depth=0.4,
        concepts_demonstrated=["retrieval"],
        concepts_missing=["reranking"],
        reasoning_quality="MODERATE",
        needs_follow_up=needs_follow_up,
    )


def next_action(action: str, topic: InterviewTopic | None) -> NextAction:
    return NextAction(action=action, topic=topic, difficulty=Difficulty.MEDIUM, rationale="LLM proposal")


# ---------------------------------------------------------------------------
# Initial-question graph
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_initial_question_graph_end_to_end_produces_a_question():
    session = make_session()
    topics = [make_topic(session.id, InterviewTopic.LLM_FUNDAMENTALS, 1)]
    repository = FakeInterviewRepository(session=session, topics=topics)
    provider = FakeLLMProvider(structured_responses={"GeneratedQuestion": SAMPLE_GENERATED_QUESTION})

    graph = build_initial_question_graph(repository, provider)
    final_state = await graph.ainvoke({"session_id": session.id})

    assert final_state["generated_question"] == SAMPLE_GENERATED_QUESTION
    assert final_state["current_topic"] is InterviewTopic.LLM_FUNDAMENTALS
    assert final_state["role"] is Role.AI_ENGINEER


@pytest.mark.asyncio
async def test_initial_question_graph_propagates_not_found_from_context_load():
    from app.services.interview_service import InterviewNotFoundError

    repository = FakeInterviewRepository(session=None)
    provider = FakeLLMProvider(structured_responses={"GeneratedQuestion": SAMPLE_GENERATED_QUESTION})
    graph = build_initial_question_graph(repository, provider)

    with pytest.raises(InterviewNotFoundError):
        await graph.ainvoke({"session_id": uuid.uuid4()})


@pytest.mark.asyncio
async def test_initial_question_graph_propagates_normalized_llm_error_not_provider_specific():
    session = make_session()
    repository = FakeInterviewRepository(session=session, topics=[])
    provider = FakeLLMProvider(error=LLMTimeoutError("simulated timeout"))
    graph = build_initial_question_graph(repository, provider)

    with pytest.raises(LLMTimeoutError):
        await graph.ainvoke({"session_id": session.id})


# ---------------------------------------------------------------------------
# Answer graph — routing branches, driven by an LLM-proposed NextAction
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_answer_graph_follow_up_branch_reaches_generate_question():
    session = make_session(current_question_number=2, question_limit=5)
    question = make_question(session.id, topic=InterviewTopic.RAG)
    repository = FakeInterviewRepository(session=session, topics=[], current_question=question)
    provider = FakeLLMProvider(
        structured_responses={
            "AnswerAnalysis": analysis(needs_follow_up=True),
            "NextAction": next_action("FOLLOW_UP", InterviewTopic.RAG),
            "GeneratedQuestion": SAMPLE_GENERATED_QUESTION,
        }
    )

    graph = build_answer_graph(repository, provider)
    final_state = await graph.ainvoke(
        {"session_id": session.id, "candidate_answer": "RAG retrieves relevant context."}
    )

    assert final_state["next_action"].action == "FOLLOW_UP"
    assert final_state["next_action"].topic is InterviewTopic.RAG
    assert final_state["generated_question"] == SAMPLE_GENERATED_QUESTION
    assert final_state["decision_fallback_used"] is False


@pytest.mark.asyncio
async def test_answer_graph_new_topic_branch_reaches_generate_question():
    session = make_session(current_question_number=2, question_limit=5)
    question = make_question(session.id, topic=InterviewTopic.RAG)
    topics = [
        make_topic(session.id, InterviewTopic.RAG, 1, status=InterviewTopicStatus.IN_PROGRESS),
        make_topic(session.id, InterviewTopic.AI_AGENTS, 2, status=InterviewTopicStatus.PENDING),
    ]
    repository = FakeInterviewRepository(session=session, topics=topics, current_question=question)
    provider = FakeLLMProvider(
        structured_responses={
            "AnswerAnalysis": analysis(needs_follow_up=False),
            "NextAction": next_action("NEW_TOPIC", InterviewTopic.AI_AGENTS),
            "GeneratedQuestion": SAMPLE_GENERATED_QUESTION,
        }
    )

    graph = build_answer_graph(repository, provider)
    final_state = await graph.ainvoke(
        {"session_id": session.id, "candidate_answer": "RAG retrieves relevant context."}
    )

    assert final_state["next_action"].action == "NEW_TOPIC"
    assert final_state["next_action"].topic is InterviewTopic.AI_AGENTS
    assert final_state["topic_transition"].from_topic is InterviewTopic.RAG
    assert final_state["topic_transition"].to_topic is InterviewTopic.AI_AGENTS
    assert final_state["generated_question"] == SAMPLE_GENERATED_QUESTION
    assert final_state["decision_fallback_used"] is False


@pytest.mark.asyncio
async def test_answer_graph_clarify_branch_reaches_generate_question():
    session = make_session(current_question_number=2, question_limit=5)
    question = make_question(session.id, topic=InterviewTopic.RAG)
    repository = FakeInterviewRepository(session=session, topics=[], current_question=question)
    provider = FakeLLMProvider(
        structured_responses={
            "AnswerAnalysis": analysis(needs_follow_up=True),
            "NextAction": next_action("CLARIFY", InterviewTopic.RAG),
            "GeneratedQuestion": SAMPLE_GENERATED_QUESTION,
        }
    )

    graph = build_answer_graph(repository, provider)
    final_state = await graph.ainvoke(
        {"session_id": session.id, "candidate_answer": "Embeddings basically store the meaning."}
    )

    assert final_state["next_action"].action == "CLARIFY"
    assert final_state["next_action"].topic is InterviewTopic.RAG
    assert final_state["generated_question"] == SAMPLE_GENERATED_QUESTION


@pytest.mark.asyncio
async def test_answer_graph_end_branch_does_not_reach_generate_question():
    session = make_session(current_question_number=2, question_limit=5)
    question = make_question(session.id, topic=InterviewTopic.RAG)
    repository = FakeInterviewRepository(session=session, topics=[], current_question=question)
    provider = FakeLLMProvider(
        structured_responses={
            "AnswerAnalysis": analysis(needs_follow_up=True),
            "NextAction": next_action("END", None),
            "GeneratedQuestion": SAMPLE_GENERATED_QUESTION,
        }
    )

    graph = build_answer_graph(repository, provider)
    final_state = await graph.ainvoke(
        {"session_id": session.id, "candidate_answer": "RAG retrieves relevant context."}
    )

    assert final_state["next_action"].action == "END"
    assert "generated_question" not in final_state
    assert all(schema != "GeneratedQuestion" for schema, _ in provider.calls)


@pytest.mark.asyncio
async def test_answer_graph_propagates_normalized_llm_error_from_analysis():
    session = make_session()
    question = make_question(session.id)
    repository = FakeInterviewRepository(session=session, topics=[], current_question=question)
    provider = FakeLLMProvider(error=LLMTimeoutError("simulated timeout"))
    graph = build_answer_graph(repository, provider)

    with pytest.raises(LLMTimeoutError):
        await graph.ainvoke({"session_id": session.id, "candidate_answer": "an answer"})


# ---------------------------------------------------------------------------
# Question-limit correctness — the backend rule overrides the LLM (Task 15 #17)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_answer_graph_forces_end_at_limit_even_when_llm_proposes_follow_up():
    session = make_session(current_question_number=5, question_limit=5)
    question = make_question(session.id, topic=InterviewTopic.RAG)
    repository = FakeInterviewRepository(session=session, topics=[], current_question=question)
    provider = FakeLLMProvider(
        structured_responses={
            "AnswerAnalysis": analysis(needs_follow_up=True),
            "NextAction": next_action("FOLLOW_UP", InterviewTopic.RAG),
        }
    )

    graph = build_answer_graph(repository, provider)
    final_state = await graph.ainvoke(
        {"session_id": session.id, "candidate_answer": "an answer to question 5"}
    )

    assert final_state["next_action"].action == "END"
    assert final_state["decision_fallback_used"] is True
    assert "generated_question" not in final_state


@pytest.mark.asyncio
async def test_answer_graph_forces_end_at_limit_even_when_llm_proposes_new_topic():
    session = make_session(current_question_number=5, question_limit=5)
    question = make_question(session.id, topic=InterviewTopic.RAG)
    topics = [
        make_topic(session.id, InterviewTopic.RAG, 1, status=InterviewTopicStatus.IN_PROGRESS),
        make_topic(session.id, InterviewTopic.AI_AGENTS, 2, status=InterviewTopicStatus.PENDING),
    ]
    repository = FakeInterviewRepository(session=session, topics=topics, current_question=question)
    provider = FakeLLMProvider(
        structured_responses={
            "AnswerAnalysis": analysis(needs_follow_up=False),
            "NextAction": next_action("NEW_TOPIC", InterviewTopic.AI_AGENTS),
        }
    )

    graph = build_answer_graph(repository, provider)
    final_state = await graph.ainvoke(
        {"session_id": session.id, "candidate_answer": "an answer to question 5"}
    )

    assert final_state["next_action"].action == "END"
    assert "generated_question" not in final_state


# ---------------------------------------------------------------------------
# Topic-validation correctness (Task 15 #18)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_answer_graph_falls_back_when_llm_proposes_unselected_topic():
    session = make_session(current_question_number=2, question_limit=5)
    question = make_question(session.id, topic=InterviewTopic.RAG)
    topics = [
        make_topic(session.id, InterviewTopic.RAG, 1, status=InterviewTopicStatus.IN_PROGRESS),
        make_topic(session.id, InterviewTopic.AI_AGENTS, 2, status=InterviewTopicStatus.PENDING),
    ]
    repository = FakeInterviewRepository(session=session, topics=topics, current_question=question)
    provider = FakeLLMProvider(
        structured_responses={
            "AnswerAnalysis": analysis(needs_follow_up=False),
            # Not one of the session's selected topics (RAG, AI_AGENTS).
            "NextAction": next_action("NEW_TOPIC", InterviewTopic.EMBEDDINGS_VECTOR_DB),
            "GeneratedQuestion": SAMPLE_GENERATED_QUESTION,
        }
    )

    graph = build_answer_graph(repository, provider)
    final_state = await graph.ainvoke(
        {"session_id": session.id, "candidate_answer": "RAG retrieves relevant context."}
    )

    assert final_state["decision_fallback_used"] is True
    # The invalid topic never enters durable-transition territory.
    assert final_state["next_action"].topic != InterviewTopic.EMBEDDINGS_VECTOR_DB


@pytest.mark.asyncio
async def test_answer_graph_falls_back_when_llm_proposes_completed_topic():
    session = make_session(current_question_number=2, question_limit=5)
    question = make_question(session.id, topic=InterviewTopic.RAG)
    topics = [
        make_topic(session.id, InterviewTopic.RAG, 1, status=InterviewTopicStatus.IN_PROGRESS),
        make_topic(session.id, InterviewTopic.AI_AGENTS, 2, status=InterviewTopicStatus.COMPLETED),
    ]
    repository = FakeInterviewRepository(session=session, topics=topics, current_question=question)
    provider = FakeLLMProvider(
        structured_responses={
            "AnswerAnalysis": analysis(needs_follow_up=False),
            "NextAction": next_action("NEW_TOPIC", InterviewTopic.AI_AGENTS),  # already COMPLETED
            "GeneratedQuestion": SAMPLE_GENERATED_QUESTION,
        }
    )

    graph = build_answer_graph(repository, provider)
    final_state = await graph.ainvoke(
        {"session_id": session.id, "candidate_answer": "RAG retrieves relevant context."}
    )

    assert final_state["decision_fallback_used"] is True
    assert final_state["next_action"].action != "NEW_TOPIC" or final_state["next_action"].topic != InterviewTopic.AI_AGENTS


@pytest.mark.asyncio
async def test_answer_graph_falls_back_to_follow_up_when_new_topic_proposed_but_none_remain():
    """No PENDING topics remain, but we're still mid-question on RAG (its
    status hasn't transitioned to COMPLETED) — the safe fallback stays on
    the current topic rather than inventing one. See
    test_decision_validator.py for the "no current topic either" case,
    where the fallback is END instead — that combination cannot occur in
    a real answer-graph run, since `current_topic` is always resolved
    from the question being answered.
    """
    session = make_session(current_question_number=2, question_limit=5)
    question = make_question(session.id, topic=InterviewTopic.RAG)
    topics = [make_topic(session.id, InterviewTopic.RAG, 1, status=InterviewTopicStatus.IN_PROGRESS)]
    repository = FakeInterviewRepository(session=session, topics=topics, current_question=question)
    provider = FakeLLMProvider(
        structured_responses={
            "AnswerAnalysis": analysis(needs_follow_up=False),
            "NextAction": next_action("NEW_TOPIC", None),
            "GeneratedQuestion": SAMPLE_GENERATED_QUESTION,
        }
    )

    graph = build_answer_graph(repository, provider)
    final_state = await graph.ainvoke(
        {"session_id": session.id, "candidate_answer": "RAG retrieves relevant context."}
    )

    assert final_state["decision_fallback_used"] is True
    assert final_state["next_action"].action == "FOLLOW_UP"
    assert final_state["next_action"].topic is InterviewTopic.RAG
    assert final_state["generated_question"] == SAMPLE_GENERATED_QUESTION


# ---------------------------------------------------------------------------
# Invalid/failing LLM decision -> deterministic fallback (Task 15 #19)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_answer_graph_falls_back_when_decision_llm_call_fails():
    session = make_session(current_question_number=2, question_limit=5)
    question = make_question(session.id, topic=InterviewTopic.RAG)
    repository = FakeInterviewRepository(session=session, topics=[], current_question=question)

    class _FlakyProvider(FakeLLMProvider):
        async def generate_structured(self, messages, output_schema):
            if output_schema.__name__ == "NextAction":
                raise LLMTimeoutError("simulated decision timeout")
            return await super().generate_structured(messages, output_schema)

    provider = _FlakyProvider(
        structured_responses={
            "AnswerAnalysis": analysis(needs_follow_up=True),
            "GeneratedQuestion": SAMPLE_GENERATED_QUESTION,
        }
    )

    graph = build_answer_graph(repository, provider)
    final_state = await graph.ainvoke(
        {"session_id": session.id, "candidate_answer": "RAG retrieves relevant context."}
    )

    # The LLM failure at the decision step does not fail the whole turn —
    # a safe deterministic decision is used instead.
    assert final_state["decision_fallback_used"] is True
    assert final_state["next_action"].action == "FOLLOW_UP"
    assert final_state["generated_question"] == SAMPLE_GENERATED_QUESTION


# ---------------------------------------------------------------------------
# Isolation between invocations
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_two_initial_question_invocations_do_not_leak_state():
    session_a = make_session()
    session_b = make_session()
    topics_a = [make_topic(session_a.id, InterviewTopic.RAG, 1)]
    topics_b = [make_topic(session_b.id, InterviewTopic.AI_AGENTS, 1)]

    question_a = GeneratedQuestion(
        question="Question A", topic=InterviewTopic.RAG, difficulty=Difficulty.MEDIUM,
        question_type=QuestionType.INITIAL,
    )
    question_b = GeneratedQuestion(
        question="Question B", topic=InterviewTopic.AI_AGENTS, difficulty=Difficulty.HARD,
        question_type=QuestionType.INITIAL,
    )

    repository_a = FakeInterviewRepository(session=session_a, topics=topics_a)
    provider_a = FakeLLMProvider(structured_responses={"GeneratedQuestion": question_a})
    graph_a = build_initial_question_graph(repository_a, provider_a)

    repository_b = FakeInterviewRepository(session=session_b, topics=topics_b)
    provider_b = FakeLLMProvider(structured_responses={"GeneratedQuestion": question_b})
    graph_b = build_initial_question_graph(repository_b, provider_b)

    result_a = await graph_a.ainvoke({"session_id": session_a.id})
    result_b = await graph_b.ainvoke({"session_id": session_b.id})

    assert result_a["session_id"] == session_a.id
    assert result_a["current_topic"] is InterviewTopic.RAG
    assert result_a["generated_question"] == question_a

    assert result_b["session_id"] == session_b.id
    assert result_b["current_topic"] is InterviewTopic.AI_AGENTS
    assert result_b["generated_question"] == question_b

    assert result_a["generated_question"] != result_b["generated_question"]


@pytest.mark.asyncio
async def test_same_compiled_graph_reused_for_two_sessions_does_not_leak_state():
    """A single InterviewWorkflow (and its compiled graphs) is meant to be
    reused across many sessions — verify concurrent-ish reuse is safe."""
    session_a = make_session()
    session_b = make_session()
    repository = FakeInterviewRepository(
        session=session_a, topics=[make_topic(session_a.id, InterviewTopic.RAG, 1)]
    )
    provider = FakeLLMProvider(structured_responses={"GeneratedQuestion": SAMPLE_GENERATED_QUESTION})
    workflow = InterviewWorkflow(repository=repository, llm_provider=provider)

    result_a = await workflow.run_initial_question({"session_id": session_a.id})
    assert result_a["session_id"] == session_a.id

    # Swap the repository's session to simulate a second, different
    # interview using the same compiled graph object.
    repository.session = session_b
    repository.topics = [make_topic(session_b.id, InterviewTopic.AI_AGENTS, 1)]
    result_b = await workflow.run_initial_question({"session_id": session_b.id})

    assert result_b["session_id"] == session_b.id
    assert result_b["current_topic"] is InterviewTopic.AI_AGENTS
    # The first result's dict was not mutated by the second invocation.
    assert result_a["session_id"] == session_a.id
    assert result_a["current_topic"] is InterviewTopic.RAG


# ---------------------------------------------------------------------------
# No durable-state mutation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_graph_execution_does_not_mutate_the_session_object():
    session = make_session(current_question_number=2, question_limit=5)
    question = make_question(session.id, topic=InterviewTopic.RAG)
    repository = FakeInterviewRepository(session=session, topics=[], current_question=question)
    provider = FakeLLMProvider(
        structured_responses={
            "AnswerAnalysis": analysis(needs_follow_up=False),
            "NextAction": next_action("FOLLOW_UP", InterviewTopic.RAG),
            "GeneratedQuestion": SAMPLE_GENERATED_QUESTION,
        }
    )

    status_before = session.status
    version_before = session.version
    question_number_before = session.current_question_number

    graph = build_answer_graph(repository, provider)
    await graph.ainvoke({"session_id": session.id, "candidate_answer": "an answer"})

    # Nothing in the graph run touched the durable session object at all —
    # there is no repository/db/redis write method available to it.
    assert session.status == status_before
    assert session.version == version_before
    assert session.current_question_number == question_number_before


def test_fake_repository_used_in_graph_tests_exposes_no_write_methods():
    """Structural guarantee: FakeInterviewRepository (what the graph is
    given in every test above) only implements reads, so graph nodes
    literally cannot call a persistence method even if they tried."""
    repository = FakeInterviewRepository()

    write_like_methods = [
        name
        for name in (
            "create_session",
            "update_session",
            "create_question",
            "create_message",
            "update_topic_status",
            "commit",
        )
        if hasattr(repository, name)
    ]

    assert write_like_methods == []


# ---------------------------------------------------------------------------
# InterviewWorkflow wrapper
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_interview_workflow_runs_both_graphs():
    session = make_session(current_question_number=2, question_limit=5)
    question = make_question(session.id, topic=InterviewTopic.RAG)
    topics = [
        make_topic(session.id, InterviewTopic.RAG, 1, status=InterviewTopicStatus.IN_PROGRESS),
        make_topic(session.id, InterviewTopic.AI_AGENTS, 2, status=InterviewTopicStatus.PENDING),
    ]
    repository = FakeInterviewRepository(session=session, topics=topics, current_question=question)
    provider = FakeLLMProvider(
        structured_responses={
            "GeneratedQuestion": SAMPLE_GENERATED_QUESTION,
            "AnswerAnalysis": analysis(needs_follow_up=False),
            "NextAction": next_action("NEW_TOPIC", InterviewTopic.AI_AGENTS),
        }
    )
    workflow = InterviewWorkflow(repository=repository, llm_provider=provider)

    initial_result = await workflow.run_initial_question({"session_id": session.id})
    assert initial_result["generated_question"] == SAMPLE_GENERATED_QUESTION

    answer_result = await workflow.run_answer_turn(
        {"session_id": session.id, "candidate_answer": "an answer"}
    )
    assert answer_result["next_action"].action == "NEW_TOPIC"
    assert answer_result["topic_transition"].to_topic is InterviewTopic.AI_AGENTS
