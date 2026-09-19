from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.knowledge.retrieval_service import KnowledgeRetrievalService
from app.llm.base import LLMProvider
from app.repositories.interview_repository import InterviewRepository
from app.workflows.interview.nodes import (
    analyze_answer,
    decide_next_action,
    generate_initial_question,
    generate_question,
    load_interview_context,
    retrieve_knowledge,
    validate_decision_node,
)
from app.workflows.interview.routing import ANSWER_ROUTING_MAP, route_after_decision
from app.workflows.interview.state import InterviewAgentState

# Task 20 default: a small, bounded number of retrieved chunks per turn —
# overridable per `InterviewWorkflow` instance (deps.py wires it from
# `settings.knowledge_retrieval_limit`), never unbounded.
DEFAULT_KNOWLEDGE_RETRIEVAL_LIMIT = 5


def build_initial_question_graph(
    repository: InterviewRepository,
    llm_provider: LLMProvider,
    knowledge_service: KnowledgeRetrievalService | None = None,
    knowledge_retrieval_limit: int = DEFAULT_KNOWLEDGE_RETRIEVAL_LIMIT,
) -> CompiledStateGraph:
    """START -> load_interview_context -> retrieve_knowledge -> generate_initial_question -> END

    `retrieve_knowledge` never talks to Qdrant/an embedding provider
    directly — only through the injected `KnowledgeRetrievalService`
    (Task 19's abstraction). `knowledge_service=None` (no knowledge layer
    configured) degrades to ungrounded generation, never a failed graph.
    """
    graph = StateGraph(InterviewAgentState)
    graph.add_node("load_interview_context", load_interview_context(repository))
    graph.add_node("retrieve_knowledge", retrieve_knowledge(knowledge_service, knowledge_retrieval_limit))
    graph.add_node("generate_initial_question", generate_initial_question(llm_provider))

    graph.add_edge(START, "load_interview_context")
    graph.add_edge("load_interview_context", "retrieve_knowledge")
    graph.add_edge("retrieve_knowledge", "generate_initial_question")
    graph.add_edge("generate_initial_question", END)

    return graph.compile()


def build_answer_graph(
    repository: InterviewRepository,
    llm_provider: LLMProvider,
    knowledge_service: KnowledgeRetrievalService | None = None,
    knowledge_retrieval_limit: int = DEFAULT_KNOWLEDGE_RETRIEVAL_LIMIT,
) -> CompiledStateGraph:
    """START -> load_interview_context -> analyze_answer -> decide_next_action
    -> validate_decision -> (FOLLOW_UP | CLARIFY | NEW_TOPIC -> retrieve_knowledge
    -> generate_question | END) -> END

    `decide_next_action` calls the LLM for a proposed `NextAction`;
    `validate_decision` is a separate, pure, LLM-free node that validates
    (and corrects if necessary) that proposal before routing — see
    decision_validator.py. Routing itself reads the *validated* action, so
    `retrieve_knowledge` always sees the final topic (e.g. the *new*
    topic on a NEW_TOPIC transition, never the one being left). END routes
    straight to END — a completed interview has nothing left to retrieve
    knowledge for.
    """
    graph = StateGraph(InterviewAgentState)
    graph.add_node("load_interview_context", load_interview_context(repository))
    graph.add_node("analyze_answer", analyze_answer(llm_provider))
    graph.add_node("decide_next_action", decide_next_action(llm_provider))
    graph.add_node("validate_decision", validate_decision_node)
    graph.add_node("retrieve_knowledge", retrieve_knowledge(knowledge_service, knowledge_retrieval_limit))
    graph.add_node("generate_question", generate_question(llm_provider))

    graph.add_edge(START, "load_interview_context")
    graph.add_edge("load_interview_context", "analyze_answer")
    graph.add_edge("analyze_answer", "decide_next_action")
    graph.add_edge("decide_next_action", "validate_decision")
    graph.add_conditional_edges("validate_decision", route_after_decision, ANSWER_ROUTING_MAP)
    graph.add_edge("retrieve_knowledge", "generate_question")
    graph.add_edge("generate_question", END)

    return graph.compile()


class InterviewWorkflow:
    """Owns the compiled initial-question and answer graphs for one
    repository/LLM-provider/knowledge-service triple.

    Not tied to a single interview session — a `CompiledStateGraph` is a
    pure function over the state dict passed to `.ainvoke()`, so one
    instance is safely reusable across many invocations (including
    concurrent ones): nothing here is mutated between calls, and each
    invocation only ever sees the state dict it was given.

    Dependencies are injected, never constructed internally — this is
    what makes the workflow testable with fake repositories/providers/
    knowledge services, and it deliberately does not import Redis,
    FastAPI, SQLAlchemy session/commit machinery, or the Qdrant SDK: a
    graph node reads through the repository (or the knowledge service) and
    returns state updates, never performs a durable mutation itself.

    `knowledge_service` is optional — omitting it (or passing `None`)
    keeps the workflow fully functional, just ungrounded, which is what
    lets every pre-Task-20 caller/test keep constructing
    `InterviewWorkflow(repository, llm_provider)` unchanged.
    """

    def __init__(
        self,
        repository: InterviewRepository,
        llm_provider: LLMProvider,
        knowledge_service: KnowledgeRetrievalService | None = None,
        knowledge_retrieval_limit: int = DEFAULT_KNOWLEDGE_RETRIEVAL_LIMIT,
    ):
        self._repository = repository
        self._llm_provider = llm_provider
        self._knowledge_service = knowledge_service
        self._initial_question_graph = build_initial_question_graph(
            repository, llm_provider, knowledge_service, knowledge_retrieval_limit
        )
        self._answer_graph = build_answer_graph(
            repository, llm_provider, knowledge_service, knowledge_retrieval_limit
        )

    async def run_initial_question(self, state: InterviewAgentState) -> InterviewAgentState:
        return await self._initial_question_graph.ainvoke(state)

    async def run_answer_turn(self, state: InterviewAgentState) -> InterviewAgentState:
        return await self._answer_graph.ainvoke(state)
