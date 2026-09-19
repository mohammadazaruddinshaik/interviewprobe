from app.knowledge.embedding.factory import get_embedding_provider
from app.knowledge.retrieval_service import KnowledgeRetrievalService
from app.knowledge.store.factory import get_knowledge_store

_service_instance: KnowledgeRetrievalService | None = None


def get_knowledge_retrieval_service() -> KnowledgeRetrievalService:
    """Return the configured `KnowledgeRetrievalService`, constructing it
    (and its embedding provider / knowledge store) at most once.

    Not called anywhere in the request path yet — `InterviewService` and
    the LangGraph workflow do not depend on this module in Task 19. It
    exists so a future task can wire retrieval into question generation
    without redesigning this layer.
    """
    global _service_instance
    if _service_instance is None:
        embedding_provider = get_embedding_provider()
        store = get_knowledge_store(vector_size=embedding_provider.dimension)
        _service_instance = KnowledgeRetrievalService(embedding_provider=embedding_provider, store=store)
    return _service_instance


def reset_knowledge_retrieval_service_cache() -> None:
    """Test-only: clear the cached singleton."""
    global _service_instance
    _service_instance = None
