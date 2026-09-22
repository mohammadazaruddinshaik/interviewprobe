class KnowledgeError(Exception):
    """Base class for every error the knowledge/retrieval layer raises.

    Application code should only ever need to catch these — never a
    vector-store SDK's own exception types (`qdrant_client.*`) or an
    embedding provider SDK's own types (`openai.*`). Each concrete
    implementation translates raw SDK errors into one of the subclasses
    below before they leave its module.
    """


class EmbeddingConfigurationError(KnowledgeError):
    """The embedding provider is misconfigured: an unsupported provider
    name, an unsupported model, or a required API key is missing."""


class EmbeddingProviderUnavailableError(KnowledgeError):
    """The embedding provider/network is unavailable: connection failure,
    5xx, rate limiting, or another transient provider-side condition."""


class EmbeddingTimeoutError(KnowledgeError):
    """The embedding request exceeded the configured timeout
    (`EMBEDDING_TIMEOUT_SECONDS`) — deliberately its own subclass, not
    folded into `EmbeddingProviderUnavailableError`, so a stalled request
    is distinguishable from a genuine outage/rejection if that distinction
    ever matters to a caller. Like every other `KnowledgeError`, the
    `retrieve_knowledge` workflow node catches this at the same boundary
    and degrades to ungrounded generation rather than failing the turn."""


class KnowledgeStoreUnavailableError(KnowledgeError):
    """The vector store (Qdrant) is unreachable or returned an unexpected
    error while upserting, searching, or deleting knowledge."""


class KnowledgeRetrievalError(KnowledgeError):
    """A retrieval request itself cannot be fulfilled: an invalid role/
    topic/concept filter, an empty query, or an invalid `limit` — never
    used for infrastructure failures (those raise the two errors above
    instead)."""
