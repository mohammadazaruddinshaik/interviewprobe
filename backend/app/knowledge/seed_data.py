"""A small, deterministic seed dataset for development/testing.

Just enough original, concise technical material to prove retrieval is
role/topic/concept aware — not a real knowledge base. Nothing here is
scraped or copied from external documentation.
"""

from app.domain.enums import Difficulty, InterviewTopic, Role
from app.knowledge.embedding.base import EmbeddingProvider
from app.knowledge.models import KnowledgeChunk
from app.knowledge.store.base import KnowledgeStore

SEED_KNOWLEDGE: list[KnowledgeChunk] = [
    # Frontend Developer — JavaScript
    KnowledgeChunk(
        role=Role.FRONTEND_DEVELOPER,
        topic=InterviewTopic.JAVASCRIPT,
        concept="closures",
        content=(
            "A closure is a function bundled together with references to its surrounding lexical "
            "scope. It lets an inner function keep accessing variables from an outer function even "
            "after that outer function has returned."
        ),
        source="seed",
        difficulty=Difficulty.MEDIUM,
    ),
    KnowledgeChunk(
        role=Role.FRONTEND_DEVELOPER,
        topic=InterviewTopic.JAVASCRIPT,
        concept="event_loop",
        content=(
            "The JavaScript event loop repeatedly pulls callbacks from a queue and runs them on the "
            "single main thread once the call stack is empty. Microtasks (like resolved promises) are "
            "drained before the next macrotask (like a setTimeout callback)."
        ),
        source="seed",
        difficulty=Difficulty.MEDIUM,
    ),
    # Frontend Developer — React
    KnowledgeChunk(
        role=Role.FRONTEND_DEVELOPER,
        topic=InterviewTopic.REACT,
        concept="hooks",
        content=(
            "Hooks let function components use state and other React features without writing a "
            "class. useState holds local state across renders; useEffect runs side effects after "
            "render and can clean them up when dependencies change or the component unmounts."
        ),
        source="seed",
        difficulty=Difficulty.EASY,
    ),
    KnowledgeChunk(
        role=Role.FRONTEND_DEVELOPER,
        topic=InterviewTopic.REACT,
        concept="rendering",
        content=(
            "React re-renders a component when its state or props change, then diffs the resulting "
            "virtual DOM tree against the previous one to compute the minimal set of real DOM updates "
            "needed."
        ),
        source="seed",
        difficulty=Difficulty.MEDIUM,
    ),
    # Backend Developer — REST APIs
    KnowledgeChunk(
        role=Role.BACKEND_DEVELOPER,
        topic=InterviewTopic.REST_APIS,
        concept="resource_design",
        content=(
            "A well-designed REST API models domain concepts as nouns (resources) addressed by URLs, "
            "with HTTP verbs (GET/POST/PUT/DELETE) expressing the operation, rather than encoding "
            "actions into the URL path itself."
        ),
        source="seed",
        difficulty=Difficulty.EASY,
    ),
    KnowledgeChunk(
        role=Role.BACKEND_DEVELOPER,
        topic=InterviewTopic.REST_APIS,
        concept="status_codes",
        content=(
            "HTTP status codes communicate the outcome of a request: 2xx for success, 4xx for a "
            "client-caused problem (bad input, missing auth, not found), and 5xx for a server-side "
            "failure the client couldn't have prevented."
        ),
        source="seed",
        difficulty=Difficulty.EASY,
    ),
    # Backend Developer — Databases
    KnowledgeChunk(
        role=Role.BACKEND_DEVELOPER,
        topic=InterviewTopic.DATABASES,
        concept="indexing",
        content=(
            "A database index is an auxiliary structure (commonly a B-tree) that lets the engine "
            "locate matching rows without scanning the whole table, trading extra storage and slower "
            "writes for much faster reads on the indexed columns."
        ),
        source="seed",
        difficulty=Difficulty.MEDIUM,
    ),
    KnowledgeChunk(
        role=Role.BACKEND_DEVELOPER,
        topic=InterviewTopic.DATABASES,
        concept="transactions",
        content=(
            "A transaction groups multiple operations so they succeed or fail together, giving "
            "atomicity and letting the database guarantee consistency even if a later operation in "
            "the group fails and everything is rolled back."
        ),
        source="seed",
        difficulty=Difficulty.MEDIUM,
    ),
    # AI Engineer — RAG
    KnowledgeChunk(
        role=Role.AI_ENGINEER,
        topic=InterviewTopic.RAG,
        concept="retrieval",
        content=(
            "Retrieval-augmented generation fetches relevant context from an external knowledge "
            "source before generation, grounding the model's answer in that retrieved text instead of "
            "relying solely on what it memorized during training."
        ),
        source="seed",
        difficulty=Difficulty.MEDIUM,
    ),
    KnowledgeChunk(
        role=Role.AI_ENGINEER,
        topic=InterviewTopic.RAG,
        concept="chunking",
        content=(
            "Chunking splits source documents into smaller, retrievable pieces before indexing. "
            "Chunk size is a trade-off: too small loses surrounding context, too large dilutes "
            "relevance and wastes context-window budget at generation time."
        ),
        source="seed",
        difficulty=Difficulty.MEDIUM,
    ),
    # AI Engineer — Embeddings & Vector Databases
    KnowledgeChunk(
        role=Role.AI_ENGINEER,
        topic=InterviewTopic.EMBEDDINGS_VECTOR_DB,
        concept="embeddings",
        content=(
            "An embedding is a dense vector representation of text where semantic similarity "
            "corresponds to geometric closeness — texts with related meaning end up near each other "
            "in the vector space, even if they share few or no exact words."
        ),
        source="seed",
        difficulty=Difficulty.EASY,
    ),
    KnowledgeChunk(
        role=Role.AI_ENGINEER,
        topic=InterviewTopic.EMBEDDINGS_VECTOR_DB,
        concept="similarity_search",
        content=(
            "Similarity search finds the nearest vectors to a query vector under a distance metric "
            "such as cosine similarity or Euclidean distance, typically using an approximate nearest-"
            "neighbor index (e.g. HNSW) so it stays fast at large scale."
        ),
        source="seed",
        difficulty=Difficulty.MEDIUM,
    ),
    # Java Developer — Collections
    KnowledgeChunk(
        role=Role.JAVA_DEVELOPER,
        topic=InterviewTopic.COLLECTIONS,
        concept="list_set_map",
        content=(
            "List preserves insertion order and allows duplicates; Set enforces uniqueness with no "
            "guaranteed order (unless it's a LinkedHashSet/TreeSet); Map stores key-value pairs, "
            "trading between HashMap's speed and TreeMap's sorted iteration."
        ),
        source="seed",
        difficulty=Difficulty.EASY,
    ),
    KnowledgeChunk(
        role=Role.JAVA_DEVELOPER,
        topic=InterviewTopic.COLLECTIONS,
        concept="iterators",
        content=(
            "An Iterator lets code traverse a collection without exposing its internal structure, and "
            "supports safe removal during iteration via `Iterator.remove()` — modifying the underlying "
            "collection directly during a for-each loop throws ConcurrentModificationException."
        ),
        source="seed",
        difficulty=Difficulty.MEDIUM,
    ),
    # Java Developer — Concurrency
    KnowledgeChunk(
        role=Role.JAVA_DEVELOPER,
        topic=InterviewTopic.CONCURRENCY,
        concept="threads",
        content=(
            "A Java thread is an independent unit of execution sharing the same process memory. "
            "Multiple threads accessing the same mutable state without coordination is what makes "
            "concurrent code prone to race conditions."
        ),
        source="seed",
        difficulty=Difficulty.MEDIUM,
    ),
    KnowledgeChunk(
        role=Role.JAVA_DEVELOPER,
        topic=InterviewTopic.CONCURRENCY,
        concept="synchronization",
        content=(
            "The `synchronized` keyword ensures only one thread at a time can execute a block or "
            "method guarded by a given monitor, preventing concurrent access to shared state at the "
            "cost of threads blocking while they wait for the lock."
        ),
        source="seed",
        difficulty=Difficulty.MEDIUM,
    ),
]


async def seed_knowledge_store(
    store: KnowledgeStore,
    embedding_provider: EmbeddingProvider,
    chunks: list[KnowledgeChunk] | None = None,
) -> int:
    """Embed and upsert `chunks` (default: `SEED_KNOWLEDGE`) into `store`.

    A thin convenience wrapper, not a background job or a CLI — used by
    the opt-in real-Qdrant integration test, and available for local
    manual seeding. Returns the number of chunks upserted.
    """
    chunks = chunks if chunks is not None else SEED_KNOWLEDGE
    if not chunks:
        return 0
    vectors = await embedding_provider.embed_many([chunk.content for chunk in chunks])
    await store.upsert(chunks, vectors)
    return len(chunks)
