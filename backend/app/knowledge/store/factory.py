from app.core.config import settings
from app.knowledge.store.base import KnowledgeStore
from app.knowledge.store.qdrant import QdrantKnowledgeStore

_store_instance: KnowledgeStore | None = None


def get_knowledge_store(vector_size: int) -> KnowledgeStore:
    """Return the configured knowledge store, constructing it at most
    once. Building `QdrantKnowledgeStore` does not open a connection
    (`AsyncQdrantClient` connects lazily, and the collection itself is
    only created on first real use) — so, like `get_llm_provider` and
    `get_embedding_provider`, this never requires Qdrant to be reachable
    at application startup.
    """
    global _store_instance
    if _store_instance is None:
        _store_instance = QdrantKnowledgeStore(
            url=settings.qdrant_url,
            collection_name=settings.qdrant_collection,
            vector_size=vector_size,
            api_key=settings.qdrant_api_key,
        )
    return _store_instance


def reset_knowledge_store_cache() -> None:
    """Test-only: clear the cached singleton."""
    global _store_instance
    _store_instance = None
