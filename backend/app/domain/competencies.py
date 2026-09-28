"""The role competency catalog: static, internal domain configuration
describing the competency areas an interview plan may cover for each
`Role`.

It sits between the role catalog and a session's runtime topic state:

    ROLE_CATALOG (app/domain/roles.py)
        "Which topics/concepts are legal for this role?"
      ↓
    ROLE_COMPETENCY_CATALOG (this module)
        "Which competency areas matter for this role, how important is
         each, and in what order would we naturally cover them?"
      ↓
    InterviewPlan (app/planning/models.py)
        "For THIS candidate/session, which areas, in what priority, and
         why?" (candidate-specific; produced later by a planner)
      ↓
    interview_topics (PostgreSQL)
        "What has actually been covered so far?" (runtime state)

Every competency is anchored to one of its role's catalog `InterviewTopic`s
(and, optionally, to that topic's catalog concept slugs), so a plan built
from competencies can always be mapped onto `interview_topics` rows
without inventing new candidate-facing vocabulary. Several competencies
may share one topic — competencies are finer-grained than topics.

Not exposed through any API and never written to the database.
"""

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import CompetencyRequirement, InterviewTopic, Role

_REQUIRED = CompetencyRequirement.REQUIRED
_OPTIONAL = CompetencyRequirement.OPTIONAL


class RoleCompetency(BaseModel):
    """One competency area for a role.

    `key` is a stable lowercase slug, unique within its role — the same
    "slug, not enum" choice `ConceptDefinition.concept` makes, since
    competencies are open-ended catalog content. `concepts` are existing
    concept slugs of `topic` in the role catalog, never new vocabulary.
    """

    model_config = ConfigDict(frozen=True)

    key: str = Field(min_length=1, pattern=r"^[a-z][a-z0-9_]*$")
    topic: InterviewTopic
    display_name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    requirement: CompetencyRequirement
    suggested_order: int = Field(ge=1)
    concepts: tuple[str, ...] = ()


def _competency(
    order: int,
    key: str,
    topic: InterviewTopic,
    requirement: CompetencyRequirement,
    display_name: str,
    description: str,
    concepts: tuple[str, ...],
) -> RoleCompetency:
    return RoleCompetency(
        key=key,
        topic=topic,
        display_name=display_name,
        description=description,
        requirement=requirement,
        suggested_order=order,
        concepts=concepts,
    )


_AI_ENGINEER = [
    _competency(1, "llm_fundamentals", InterviewTopic.LLM_FUNDAMENTALS, _REQUIRED,
                "LLM Fundamentals", "How LLMs process input and generate output.",
                ("tokenization", "context_window", "sampling")),
    _competency(2, "embeddings_vector_search", InterviewTopic.EMBEDDINGS_VECTOR_DB, _REQUIRED,
                "Embeddings & Vector Search", "Representing meaning as vectors and searching them efficiently.",
                ("embeddings", "similarity_search", "indexing")),
    _competency(3, "retrieval_augmented_generation", InterviewTopic.RAG, _REQUIRED,
                "Retrieval-Augmented Generation", "Designing retrieval pipelines that ground LLM output.",
                ("retrieval", "chunking", "reranking")),
    _competency(4, "ai_agents", InterviewTopic.AI_AGENTS, _OPTIONAL,
                "AI Agents", "Tool use, planning, and state in LLM-driven agents.",
                ("tool_use", "planning", "memory")),
    _competency(5, "llm_evaluation", InterviewTopic.LLM_EVALUATION, _REQUIRED,
                "LLM Evaluation", "Measuring and regression-testing LLM output quality.",
                ("metrics", "llm_as_judge", "human_eval")),
    _competency(6, "llm_serving_tradeoffs", InterviewTopic.AI_SYSTEM_DESIGN, _REQUIRED,
                "LLM Serving Trade-offs", "Latency, cost, and caching decisions for production LLM features.",
                ("latency_cost", "caching")),
    _competency(7, "llm_observability", InterviewTopic.AI_SYSTEM_DESIGN, _OPTIONAL,
                "LLM Observability", "Tracing and monitoring LLM calls in production safely.",
                ("observability",)),
]

_FRONTEND_DEVELOPER = [
    _competency(1, "javascript_fundamentals", InterviewTopic.JAVASCRIPT, _REQUIRED,
                "JavaScript Fundamentals", "Scope, closures, and the asynchronous execution model.",
                ("closures", "event_loop", "promises")),
    _competency(2, "react_state_and_hooks", InterviewTopic.REACT, _REQUIRED,
                "React State & Hooks", "Managing component state and effects with hooks.",
                ("hooks",)),
    _competency(3, "react_rendering", InterviewTopic.REACT, _REQUIRED,
                "React Rendering", "When and why React re-renders, and how to keep it efficient.",
                ("rendering", "performance")),
    _competency(4, "css_layout", InterviewTopic.CSS, _REQUIRED,
                "CSS Layout", "Building responsive layouts with Flexbox and Grid.",
                ("flexbox", "grid")),
    _competency(5, "browser_rendering", InterviewTopic.BROWSER_FUNDAMENTALS, _OPTIONAL,
                "Browser Rendering", "The DOM and the browser's style/layout/paint pipeline.",
                ("dom", "rendering_pipeline")),
    _competency(6, "web_networking", InterviewTopic.BROWSER_FUNDAMENTALS, _OPTIONAL,
                "Web Networking", "How the browser talks to servers over HTTP.",
                ("http",)),
    _competency(7, "web_performance", InterviewTopic.WEB_PERFORMANCE, _OPTIONAL,
                "Web Performance", "Diagnosing and improving page load and runtime performance.",
                ("critical_rendering_path", "lazy_loading", "caching")),
]

_BACKEND_DEVELOPER = [
    _competency(1, "runtime_concurrency", InterviewTopic.BACKEND_RUNTIME, _REQUIRED,
                "Runtime & Concurrency", "How a service handles concurrent requests and background work.",
                ("async_io", "event_loop", "process_management")),
    _competency(2, "api_design", InterviewTopic.REST_APIS, _REQUIRED,
                "API Design", "Modeling resources and communicating outcomes over HTTP.",
                ("resource_design", "status_codes")),
    _competency(3, "api_evolution", InterviewTopic.REST_APIS, _OPTIONAL,
                "API Evolution", "Changing an API without breaking existing clients.",
                ("versioning",)),
    _competency(4, "data_modeling", InterviewTopic.DATABASES, _REQUIRED,
                "Data Modeling & Indexing", "Structuring relational data and making queries fast.",
                ("normalization", "indexing")),
    _competency(5, "transactions_consistency", InterviewTopic.DATABASES, _REQUIRED,
                "Transactions & Consistency", "Keeping data correct under concurrent writes.",
                ("transactions",)),
    _competency(6, "caching_strategies", InterviewTopic.CACHING, _REQUIRED,
                "Caching Strategies", "Choosing cache patterns and keeping cached data fresh.",
                ("cache_aside", "ttl", "cache_invalidation")),
    _competency(7, "system_design", InterviewTopic.SYSTEM_DESIGN, _REQUIRED,
                "System Design", "Designing backend systems that scale and stay available.",
                ("scalability", "load_balancing", "availability")),
]

_JAVA_DEVELOPER = [
    _competency(1, "core_java_language", InterviewTopic.CORE_JAVA, _REQUIRED,
                "Core Java Language", "Java's type system, language basics, and generics.",
                ("syntax_and_types", "generics")),
    _competency(2, "exception_handling", InterviewTopic.CORE_JAVA, _OPTIONAL,
                "Exception Handling", "Designing robust error handling in Java.",
                ("exception_handling",)),
    _competency(3, "object_oriented_design", InterviewTopic.OOP, _REQUIRED,
                "Object-Oriented Design", "Applying inheritance, polymorphism, and encapsulation well.",
                ("inheritance", "polymorphism", "encapsulation")),
    _competency(4, "collections_framework", InterviewTopic.COLLECTIONS, _REQUIRED,
                "Collections Framework", "Choosing and using the right collection for the job.",
                ("list_set_map", "iterators", "comparators")),
    _competency(5, "multithreading", InterviewTopic.CONCURRENCY, _REQUIRED,
                "Multithreading", "Threads, synchronization, and executor-based concurrency.",
                ("threads", "synchronization", "executors")),
    _competency(6, "jvm_internals", InterviewTopic.JVM, _OPTIONAL,
                "JVM Internals", "Memory model, garbage collection, and class loading.",
                ("memory_model", "garbage_collection", "class_loading")),
    _competency(7, "spring_core", InterviewTopic.SPRING, _REQUIRED,
                "Spring Core", "Dependency injection and the Spring IoC container.",
                ("dependency_injection",)),
    _competency(8, "spring_web_applications", InterviewTopic.SPRING, _OPTIONAL,
                "Spring Web Applications", "Building web services with Spring Boot and Spring MVC.",
                ("spring_boot", "spring_mvc")),
]

_SDE = [
    _competency(1, "data_structures", InterviewTopic.DATA_STRUCTURES_ALGORITHMS, _REQUIRED,
                "Data Structures", "Choosing and applying core data structures.",
                ("arrays_and_hashing", "recursion_and_trees")),
    _competency(2, "complexity_analysis", InterviewTopic.DATA_STRUCTURES_ALGORITHMS, _REQUIRED,
                "Complexity Analysis", "Reasoning about time/space trade-offs of a solution.",
                ("complexity_analysis",)),
    _competency(3, "runtime_concurrency", InterviewTopic.BACKEND_RUNTIME, _OPTIONAL,
                "Runtime & Concurrency", "How a service handles concurrent work.",
                ("async_io", "event_loop", "process_management")),
    _competency(4, "api_design", InterviewTopic.REST_APIS, _OPTIONAL,
                "API Design", "Designing and evolving HTTP APIs.",
                ("resource_design", "status_codes", "versioning")),
    _competency(5, "data_modeling", InterviewTopic.DATABASES, _REQUIRED,
                "Data Modeling & Indexing", "Structuring data and making queries fast.",
                ("normalization", "indexing")),
    _competency(6, "transactions_consistency", InterviewTopic.DATABASES, _OPTIONAL,
                "Transactions & Consistency", "Keeping data correct under concurrent writes.",
                ("transactions",)),
    _competency(7, "system_design", InterviewTopic.SYSTEM_DESIGN, _REQUIRED,
                "System Design", "Designing systems that scale and stay available.",
                ("scalability", "load_balancing", "availability")),
]

# SDE Intern's role catalog has only three topics (DSA, OOP, REST APIs);
# the competency list stays within that scope rather than stretching an
# intern interview into areas the role deliberately excludes.
_SDE_INTERN = [
    _competency(1, "arrays_and_hashing", InterviewTopic.DATA_STRUCTURES_ALGORITHMS, _REQUIRED,
                "Arrays & Hashing", "Using arrays and hash maps to solve problems.",
                ("arrays_and_hashing",)),
    _competency(2, "recursion_and_trees", InterviewTopic.DATA_STRUCTURES_ALGORITHMS, _REQUIRED,
                "Recursion & Trees", "Recursive decomposition and tree-shaped data.",
                ("recursion_and_trees",)),
    _competency(3, "complexity_analysis", InterviewTopic.DATA_STRUCTURES_ALGORITHMS, _REQUIRED,
                "Complexity Analysis", "Estimating the time/space cost of a solution.",
                ("complexity_analysis",)),
    _competency(4, "object_oriented_basics", InterviewTopic.OOP, _REQUIRED,
                "Object-Oriented Basics", "Core OOP principles applied in simple designs.",
                ("inheritance", "polymorphism", "encapsulation")),
    _competency(5, "http_api_basics", InterviewTopic.REST_APIS, _OPTIONAL,
                "HTTP API Basics", "Understanding resources and HTTP status codes.",
                ("resource_design", "status_codes")),
]

_FULL_STACK_DEVELOPER = [
    _competency(1, "javascript_fundamentals", InterviewTopic.JAVASCRIPT, _REQUIRED,
                "JavaScript Fundamentals", "Scope, closures, and the asynchronous execution model.",
                ("closures", "event_loop", "promises")),
    _competency(2, "react_state_and_hooks", InterviewTopic.REACT, _REQUIRED,
                "React State & Hooks", "Managing component state and effects with hooks.",
                ("hooks",)),
    _competency(3, "react_rendering", InterviewTopic.REACT, _OPTIONAL,
                "React Rendering", "When and why React re-renders, and how to keep it efficient.",
                ("rendering", "performance")),
    _competency(4, "server_runtime", InterviewTopic.BACKEND_RUNTIME, _OPTIONAL,
                "Server Runtime", "How a Node-style backend handles concurrent requests.",
                ("async_io", "event_loop", "process_management")),
    _competency(5, "api_design", InterviewTopic.REST_APIS, _REQUIRED,
                "API Design", "Designing and evolving HTTP APIs consumed by the frontend.",
                ("resource_design", "status_codes", "versioning")),
    _competency(6, "data_modeling", InterviewTopic.DATABASES, _REQUIRED,
                "Data Modeling & Indexing", "Structuring application data and making queries fast.",
                ("normalization", "indexing")),
    _competency(7, "transactions_consistency", InterviewTopic.DATABASES, _OPTIONAL,
                "Transactions & Consistency", "Keeping data correct under concurrent writes.",
                ("transactions",)),
]


ROLE_COMPETENCY_CATALOG: dict[Role, list[RoleCompetency]] = {
    Role.AI_ENGINEER: _AI_ENGINEER,
    Role.FRONTEND_DEVELOPER: _FRONTEND_DEVELOPER,
    Role.BACKEND_DEVELOPER: _BACKEND_DEVELOPER,
    Role.JAVA_DEVELOPER: _JAVA_DEVELOPER,
    Role.SDE: _SDE,
    Role.SDE_INTERN: _SDE_INTERN,
    Role.FULL_STACK_DEVELOPER: _FULL_STACK_DEVELOPER,
}


def get_role_competencies(role: Role) -> list[RoleCompetency]:
    """The competencies for `role`, in suggested order. Raises `KeyError`
    for a role missing from the catalog, like `get_role_definition`."""
    return sorted(ROLE_COMPETENCY_CATALOG[role], key=lambda c: c.suggested_order)


def get_competency(role: Role, key: str) -> RoleCompetency | None:
    for competency in ROLE_COMPETENCY_CATALOG[role]:
        if competency.key == key:
            return competency
    return None
