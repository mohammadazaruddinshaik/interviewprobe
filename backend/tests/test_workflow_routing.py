import pytest
from langgraph.graph import END

from app.domain.enums import Difficulty, InterviewTopic
from app.workflows.interview.models import NextAction
from app.workflows.interview.routing import (
    ANSWER_ROUTING_MAP,
    GENERATE_QUESTION_NODE,
    RETRIEVE_KNOWLEDGE_NODE,
    route_after_decision,
)


@pytest.mark.parametrize("action", ["FOLLOW_UP", "CLARIFY", "NEW_TOPIC"])
def test_route_after_decision_returns_the_action_for_generation_branches(action):
    state = {
        "next_action": NextAction(action=action, topic=None, difficulty=Difficulty.MEDIUM, rationale="x")
    }

    assert route_after_decision(state) == action
    # Task 20: generation branches route through `retrieve_knowledge`
    # first, not directly to `generate_question`.
    assert ANSWER_ROUTING_MAP[route_after_decision(state)] == RETRIEVE_KNOWLEDGE_NODE
    assert GENERATE_QUESTION_NODE != RETRIEVE_KNOWLEDGE_NODE


def test_route_after_decision_returns_end_action():
    state = {
        "next_action": NextAction(action="END", topic=None, difficulty=Difficulty.MEDIUM, rationale="x")
    }

    assert route_after_decision(state) == "END"
    assert ANSWER_ROUTING_MAP[route_after_decision(state)] is END


def test_route_after_decision_defaults_to_end_when_next_action_missing():
    assert route_after_decision({}) == "END"
    assert ANSWER_ROUTING_MAP[route_after_decision({})] is END


def test_routing_map_covers_exactly_the_four_actions():
    assert set(ANSWER_ROUTING_MAP.keys()) == {"FOLLOW_UP", "CLARIFY", "NEW_TOPIC", "END"}


def test_topic_preserved_through_next_action_for_follow_up():
    state = {
        "next_action": NextAction(
            action="FOLLOW_UP", topic=InterviewTopic.RAG, difficulty=Difficulty.MEDIUM, rationale="x"
        )
    }

    assert route_after_decision(state) == "FOLLOW_UP"
