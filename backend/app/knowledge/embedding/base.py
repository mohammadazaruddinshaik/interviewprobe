from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Provider-neutral interface for turning text into vectors.

    Mirrors `app.llm.base.LLMProvider`'s shape deliberately: application
    code (the future retrieval-integrated question generation) must depend
    only on this interface, never on a provider SDK directly. Subclasses
    translate every raw SDK exception into an `EmbeddingProviderUnavailableError`/
    `EmbeddingConfigurationError` before it leaves their module.

    `dimension` is set by the concrete subclass from its configured model
    (e.g. a small per-model lookup table) — never hardcoded by a caller —
    so `KnowledgeStore` collection setup can read it rather than guess it.
    """

    def __init__(self, *, provider_name: str, model: str, dimension: int):
        self.provider_name = provider_name
        self.model = model
        self.dimension = dimension

    @abstractmethod
    async def embed(self, text: str) -> list[float]: ...

    @abstractmethod
    async def embed_many(self, texts: list[str]) -> list[list[float]]: ...
