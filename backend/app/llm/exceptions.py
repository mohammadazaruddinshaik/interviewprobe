class LLMError(Exception):
    """Base class for every error the LLM provider abstraction raises.

    Application code should only ever need to catch these — never a
    provider SDK's own exception types (`openai.*`, `google.genai.*`).
    Each provider translates raw SDK errors into one of the subclasses
    below before they leave the provider module.
    """


class LLMProviderUnavailableError(LLMError):
    """The provider/network is unavailable: connection failure, 5xx, or
    another transient server-side condition. Retryable."""


class LLMTimeoutError(LLMError):
    """The request exceeded `LLM_TIMEOUT_SECONDS`. Not retried automatically
    — a slow request retried immediately is unlikely to get faster."""


class LLMRateLimitError(LLMError):
    """The provider rejected the request due to rate limiting. Retryable."""


class LLMInvalidResponseError(LLMError):
    """The provider's request was rejected as malformed, or its response
    could not be parsed/validated into the expected structure. Not
    retryable — retrying an invalid request produces the same result."""


class LLMConfigurationError(LLMError):
    """The provider is misconfigured: an unsupported provider name, or a
    required API key is missing/rejected as invalid. Not retryable."""
