class VoiceError(Exception):
    """Base class for every error the TTS provider abstraction raises.

    Application code should only ever need to catch these — never a
    provider SDK's own exception types (`azure.cognitiveservices.speech.*`).
    Each provider translates raw SDK errors into one of the subclasses
    below before they leave the provider module.
    """


class VoiceConfigurationError(VoiceError):
    """The provider is misconfigured: missing/rejected credentials, or an
    unsupported provider name. Not retryable."""


class VoiceProviderUnavailableError(VoiceError):
    """The provider/network is unavailable: connection failure, 5xx, or
    another transient server-side condition. Retryable."""


class VoiceTimeoutError(VoiceError):
    """The request exceeded the configured TTS timeout. Not retried
    automatically — a slow request retried immediately is unlikely to get
    faster."""


class VoiceProviderRejectedError(VoiceError):
    """The provider rejected the request as malformed (e.g. bad voice name
    or unsupported input). Not retryable — retrying an invalid request
    produces the same result."""


class VoiceSynthesisError(VoiceError):
    """Synthesis did not complete for a reason that doesn't fit the other
    categories. Not retryable."""
