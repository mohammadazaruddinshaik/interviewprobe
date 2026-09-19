"""The role catalog: static domain configuration describing which topics
(and which concepts within each topic) are available for a given
interview `Role`.

This is deliberately a different thing from an interview's *persisted*
topic state (`InterviewTopicEntry` / the `interview_topics` table,
Task 10):

    Role Catalog                           Interview Topic State
    ─────────────                          ─────────────────────
    "What topics COULD a candidate         "What topics did THIS
     interviewing for this role be          candidate actually select,
     asked about?"                          and what's each one's
                                             PENDING / IN_PROGRESS /
    Fixed, versioned with the code —        COMPLETED status right now?"
    the same for every interview of a
    given role.                             One row per (session, topic).
                                             Different for every interview,
    Lives only in this module — never       even two interviews for the
    written to the database.                same role. Lives in PostgreSQL.

Interview creation is expected to validate a candidate's requested
topics *against* this catalog (`validate_role_topics`); only the
selected subset then gets persisted as `interview_topics` rows. The
catalog answers "is this a legal choice?" — it never represents "what
this particular candidate chose."

Kept intentionally simple: a handful of typed Pydantic models plus a
plain `dict` constant. No database, no plugin system, no dynamic
role/topic registration — see the Task 16 report for why.
"""

from pydantic import BaseModel, Field

from app.domain.enums import InterviewTopic, Role


class ConceptDefinition(BaseModel):
    """One testable concept within a topic.

    `concept` is a simple, stable, lowercase slug — not another enum.
    Concepts are open-ended catalog *content* (there could reasonably be
    dozens per topic over time), unlike the small, closed sets that
    justify a real enum elsewhere in this project (`InterviewStatus`,
    `QuestionType`, ...). Making every concept its own enum member would
    be exactly the over-engineering this task asks to avoid.
    """

    concept: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    description: str = Field(min_length=1)


class TopicDefinition(BaseModel):
    """One topic's catalog metadata: its machine identity (the existing
    `InterviewTopic` enum — never duplicated), a human-readable name/
    description, and the concepts it covers."""

    topic: InterviewTopic
    display_name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    concepts: list[ConceptDefinition] = Field(default_factory=list)


class RoleDefinition(BaseModel):
    """One role's full catalog entry: identity (the `Role` enum), display
    metadata, and the topics available for interviews of this role."""

    role: Role
    display_name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    topics: list[TopicDefinition] = Field(min_length=1)


class InvalidRoleTopicError(Exception):
    """Raised when one or more requested topics are not part of the given
    role's catalog (e.g. proposing a React question for a Backend
    Developer interview)."""


class InvalidTopicConceptError(Exception):
    """Raised when a concept is not part of the given role/topic's catalog
    (e.g. proposing a "hooks" concept under Backend Developer/Databases)."""


def _concept(concept: str, display_name: str, description: str) -> ConceptDefinition:
    return ConceptDefinition(concept=concept, display_name=display_name, description=description)


def _topic(
    topic: InterviewTopic, display_name: str, description: str, concepts: list[ConceptDefinition]
) -> TopicDefinition:
    return TopicDefinition(topic=topic, display_name=display_name, description=description, concepts=concepts)


_AI_ENGINEER = RoleDefinition(
    role=Role.AI_ENGINEER,
    display_name="AI Engineer",
    description="Builds LLM-powered applications: retrieval, agents, evaluation, and system design.",
    topics=[
        _topic(
            InterviewTopic.LLM_FUNDAMENTALS,
            "LLM Fundamentals",
            "How large language models work under the hood.",
            [
                _concept("tokenization", "Tokenization", "How text is split into model input tokens."),
                _concept("context_window", "Context Window", "The model's limited input/output token budget."),
                _concept("sampling", "Sampling", "Temperature, top-p, and other decoding strategies."),
            ],
        ),
        _topic(
            InterviewTopic.RAG,
            "Retrieval-Augmented Generation",
            "Grounding LLM responses in retrieved external context.",
            [
                _concept("retrieval", "Retrieval", "Fetching relevant context before generation."),
                _concept("chunking", "Chunking", "Splitting source documents for retrieval."),
                _concept("reranking", "Reranking", "Reordering retrieved results by relevance."),
            ],
        ),
        _topic(
            InterviewTopic.EMBEDDINGS_VECTOR_DB,
            "Embeddings & Vector Databases",
            "Representing and searching meaning as vectors.",
            [
                _concept("embeddings", "Embeddings", "Dense vector representations of text/meaning."),
                _concept("similarity_search", "Similarity Search", "Finding nearest vectors by a distance metric."),
                _concept("indexing", "Indexing", "Structures like HNSW/IVF for fast vector search."),
            ],
        ),
        _topic(
            InterviewTopic.AI_AGENTS,
            "AI Agents",
            "LLM-driven systems that plan and take actions.",
            [
                _concept("tool_use", "Tool Use", "Letting an LLM call external functions/APIs."),
                _concept("planning", "Planning", "Breaking a goal into a sequence of steps."),
                _concept("memory", "Memory", "Carrying state across agent turns."),
            ],
        ),
        _topic(
            InterviewTopic.LLM_EVALUATION,
            "LLM Evaluation",
            "Measuring the quality of LLM output.",
            [
                _concept("metrics", "Metrics", "Quantitative measures of output quality."),
                _concept("llm_as_judge", "LLM-as-Judge", "Using an LLM to grade another LLM's output."),
                _concept("human_eval", "Human Evaluation", "Manual review as a quality baseline."),
            ],
        ),
        _topic(
            InterviewTopic.AI_SYSTEM_DESIGN,
            "AI System Design",
            "Architecting production LLM-backed systems.",
            [
                _concept("latency_cost", "Latency & Cost", "Trade-offs in serving LLM-backed features."),
                _concept("caching", "Caching", "Reusing prior LLM results where it's safe to."),
                _concept("observability", "Observability", "Logging/tracing LLM calls without leaking data."),
            ],
        ),
    ],
)

_FRONTEND_DEVELOPER = RoleDefinition(
    role=Role.FRONTEND_DEVELOPER,
    display_name="Frontend Developer",
    description="Builds user-facing web interfaces with JavaScript, React, and modern CSS.",
    topics=[
        _topic(
            InterviewTopic.JAVASCRIPT,
            "JavaScript",
            "Core language mechanics behind the browser and Node runtimes.",
            [
                _concept("closures", "Closures", "Functions retaining access to their defining scope."),
                _concept("event_loop", "Event Loop", "How JavaScript schedules async callbacks."),
                _concept("promises", "Promises", "Representing eventual async results."),
            ],
        ),
        _topic(
            InterviewTopic.REACT,
            "React",
            "Building UIs with React's component and rendering model.",
            [
                _concept("hooks", "Hooks", "useState/useEffect and other composable component logic."),
                _concept("rendering", "Rendering", "How and when React re-renders components."),
                _concept("performance", "Performance", "Avoiding unnecessary renders and re-computation."),
            ],
        ),
        _topic(
            InterviewTopic.CSS,
            "CSS",
            "Styling and layout on the web.",
            [
                _concept("flexbox", "Flexbox", "One-dimensional flexible box layout."),
                _concept("grid", "Grid", "Two-dimensional layout with CSS Grid."),
            ],
        ),
        _topic(
            InterviewTopic.WEB_PERFORMANCE,
            "Web Performance",
            "Making web applications fast to load and interact with.",
            [
                _concept("critical_rendering_path", "Critical Rendering Path", "Steps the browser takes to paint a page."),
                _concept("lazy_loading", "Lazy Loading", "Deferring work until it's actually needed."),
                _concept("caching", "Caching", "Reusing assets/responses across requests."),
            ],
        ),
        _topic(
            InterviewTopic.BROWSER_FUNDAMENTALS,
            "Browser Fundamentals",
            "How browsers parse, render, and execute web pages.",
            [
                _concept("dom", "DOM", "The in-memory tree representation of a page."),
                _concept("http", "HTTP", "The request/response protocol underlying the web."),
                _concept("rendering_pipeline", "Rendering Pipeline", "Style, layout, paint, and composite."),
            ],
        ),
    ],
)

_BACKEND_DEVELOPER = RoleDefinition(
    role=Role.BACKEND_DEVELOPER,
    display_name="Backend Developer",
    description="Builds server-side APIs, data storage, and scalable backend systems.",
    topics=[
        _topic(
            InterviewTopic.BACKEND_RUNTIME,
            "Backend Runtime",
            "How a backend service executes and handles concurrent work.",
            [
                _concept("async_io", "Async I/O", "Non-blocking handling of concurrent requests."),
                _concept("process_management", "Process Management", "Workers, threads, and process lifecycles."),
                _concept("event_loop", "Event Loop", "Single-threaded event-driven request handling."),
            ],
        ),
        _topic(
            InterviewTopic.REST_APIS,
            "REST APIs",
            "Designing HTTP APIs for backend services.",
            [
                _concept("resource_design", "Resource Design", "Modeling domain concepts as REST resources."),
                _concept("status_codes", "Status Codes", "Communicating outcomes via HTTP semantics."),
                _concept("versioning", "Versioning", "Evolving an API without breaking clients."),
            ],
        ),
        _topic(
            InterviewTopic.DATABASES,
            "Databases",
            "Storing and querying data reliably.",
            [
                _concept("indexing", "Indexing", "Speeding up lookups at the cost of writes/storage."),
                _concept("transactions", "Transactions", "Atomic, consistent groups of operations."),
                _concept("normalization", "Normalization", "Structuring relational data to reduce redundancy."),
            ],
        ),
        _topic(
            InterviewTopic.CACHING,
            "Caching",
            "Reducing latency and load by reusing prior results.",
            [
                _concept("cache_invalidation", "Cache Invalidation", "Keeping cached data from going stale."),
                _concept("ttl", "TTL", "Expiring cached entries after a fixed time."),
                _concept("cache_aside", "Cache-Aside", "Loading into cache on read-miss."),
            ],
        ),
        _topic(
            InterviewTopic.SYSTEM_DESIGN,
            "System Design",
            "Architecting backend systems that scale reliably.",
            [
                _concept("scalability", "Scalability", "Handling growing load without falling over."),
                _concept("load_balancing", "Load Balancing", "Distributing traffic across instances."),
                _concept("availability", "Availability", "Keeping a system usable despite failures."),
            ],
        ),
    ],
)

_JAVA_DEVELOPER = RoleDefinition(
    role=Role.JAVA_DEVELOPER,
    display_name="Java Developer",
    description="Builds backend applications and services using Java and the JVM ecosystem.",
    topics=[
        _topic(
            InterviewTopic.CORE_JAVA,
            "Core Java",
            "Fundamental Java language features.",
            [
                _concept("syntax_and_types", "Syntax & Types", "Java's type system and language basics."),
                _concept("exception_handling", "Exception Handling", "Checked/unchecked exceptions and try-with-resources."),
                _concept("generics", "Generics", "Type-safe, reusable code across types."),
            ],
        ),
        _topic(
            InterviewTopic.OOP,
            "Object-Oriented Programming",
            "Core OOP principles as applied in Java.",
            [
                _concept("inheritance", "Inheritance", "Reusing and extending behavior through class hierarchies."),
                _concept("polymorphism", "Polymorphism", "Treating different types through a common interface."),
                _concept("encapsulation", "Encapsulation", "Hiding internal state behind a controlled interface."),
            ],
        ),
        _topic(
            InterviewTopic.COLLECTIONS,
            "Collections",
            "Java's standard data structure library.",
            [
                _concept("list_set_map", "List/Set/Map", "Core collection interfaces and their trade-offs."),
                _concept("iterators", "Iterators", "Traversing collections safely."),
                _concept("comparators", "Comparators", "Custom ordering of collection elements."),
            ],
        ),
        _topic(
            InterviewTopic.CONCURRENCY,
            "Concurrency",
            "Writing correct multi-threaded Java code.",
            [
                _concept("threads", "Threads", "Units of concurrent execution in the JVM."),
                _concept("synchronization", "Synchronization", "Coordinating access to shared state."),
                _concept("executors", "Executors", "Managing thread pools for concurrent tasks."),
            ],
        ),
        _topic(
            InterviewTopic.JVM,
            "JVM",
            "How the Java Virtual Machine runs Java programs.",
            [
                _concept("garbage_collection", "Garbage Collection", "Automatic reclamation of unused memory."),
                _concept("class_loading", "Class Loading", "How the JVM loads and links classes at runtime."),
                _concept("memory_model", "Memory Model", "Heap, stack, and visibility guarantees across threads."),
            ],
        ),
        _topic(
            InterviewTopic.SPRING,
            "Spring",
            "Building backend applications with the Spring ecosystem.",
            [
                _concept("dependency_injection", "Dependency Injection", "Spring's core IoC container pattern."),
                _concept("spring_boot", "Spring Boot", "Convention-based Spring application setup."),
                _concept("spring_mvc", "Spring MVC", "Building web controllers with Spring."),
            ],
        ),
    ],
)


ROLE_CATALOG: dict[Role, RoleDefinition] = {
    Role.AI_ENGINEER: _AI_ENGINEER,
    Role.FRONTEND_DEVELOPER: _FRONTEND_DEVELOPER,
    Role.BACKEND_DEVELOPER: _BACKEND_DEVELOPER,
    Role.JAVA_DEVELOPER: _JAVA_DEVELOPER,
}


def get_role_definition(role: Role) -> RoleDefinition:
    return ROLE_CATALOG[role]


def get_topics_for_role(role: Role) -> list[InterviewTopic]:
    """The topics a candidate interviewing for `role` may be asked about."""
    return [topic_def.topic for topic_def in ROLE_CATALOG[role].topics]


def get_topic_definition(role: Role, topic: InterviewTopic) -> TopicDefinition | None:
    """The catalog metadata for `topic` under `role`, or None if `topic`
    is not part of that role's catalog."""
    for topic_def in ROLE_CATALOG[role].topics:
        if topic_def.topic == topic:
            return topic_def
    return None


def is_topic_valid_for_role(role: Role, topic: InterviewTopic) -> bool:
    return topic in get_topics_for_role(role)


def validate_role_topics(role: Role, topics: list[InterviewTopic]) -> None:
    """Raise `InvalidRoleTopicError` if any of `topics` is not part of
    `role`'s catalog. Pure/deterministic — no database, Redis, or LLM
    calls, and no side effects. Returns `None` (does not raise) when every
    topic is valid.
    """
    valid_topics = set(get_topics_for_role(role))
    invalid = [topic for topic in topics if topic not in valid_topics]
    if invalid:
        raise InvalidRoleTopicError(
            f"Topic(s) {[t.value for t in invalid]} are not valid for role {role.value}. "
            f"Valid topics for this role: {[t.value for t in valid_topics]}."
        )


def get_concepts_for_topic(role: Role, topic: InterviewTopic) -> list[str]:
    """The concept slugs available under `role`'s catalog entry for
    `topic`. Empty if `topic` isn't part of `role`'s catalog at all — use
    `validate_role_topics`/`validate_role_topic_concept` to distinguish
    that case from "topic is valid but has no concepts listed"."""
    topic_def = get_topic_definition(role, topic)
    if topic_def is None:
        return []
    return [concept_def.concept for concept_def in topic_def.concepts]


def is_concept_valid_for_topic(role: Role, topic: InterviewTopic, concept: str) -> bool:
    return concept in get_concepts_for_topic(role, topic)


def validate_role_topic_concept(role: Role, topic: InterviewTopic, concept: str | None) -> None:
    """Raise `InvalidRoleTopicError` if `topic` isn't valid for `role`
    (reusing `validate_role_topics` rather than re-checking membership
    here), or `InvalidTopicConceptError` if `concept` isn't one of that
    topic's catalog concepts. `concept=None` skips concept-level
    validation — useful for role/topic-only filtering, where no specific
    concept was requested.
    """
    validate_role_topics(role, [topic])
    if concept is not None and not is_concept_valid_for_topic(role, topic, concept):
        raise InvalidTopicConceptError(
            f"Concept '{concept}' is not valid for role {role.value}, topic {topic.value}. "
            f"Valid concepts: {get_concepts_for_topic(role, topic)}."
        )
