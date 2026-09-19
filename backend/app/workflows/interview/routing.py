from langgraph.graph import END

from app.workflows.interview.state import InterviewAgentState

GENERATE_QUESTION_NODE = "generate_question"
RETRIEVE_KNOWLEDGE_NODE = "retrieve_knowledge"

# FOLLOW_UP/CLARIFY/NEW_TOPIC all currently lead to the same generic
# `retrieve_knowledge` -> `generate_question` pair (Task 14 skeleton, Task
# 20 retrieval). Kept as three distinct entries rather than collapsed into
# one, so a future task can point any single action at a different node
# without touching `route_after_decision` or the graph wiring in graph.py.
#
# END is deliberately the only action that never reaches
# `retrieve_knowledge` — a completed interview has no next question to
# ground, so there is nothing worth retrieving for.
ANSWER_ROUTING_MAP: dict[str, str] = {
    "FOLLOW_UP": RETRIEVE_KNOWLEDGE_NODE,
    "CLARIFY": RETRIEVE_KNOWLEDGE_NODE,
    "NEW_TOPIC": RETRIEVE_KNOWLEDGE_NODE,
    "END": END,
}


def route_after_decision(state: InterviewAgentState) -> str:
    """Reads the proposed `next_action.action` and returns the routing key
    looked up in `ANSWER_ROUTING_MAP`."""
    next_action = state.get("next_action")
    if next_action is None:
        return "END"
    return next_action.action
