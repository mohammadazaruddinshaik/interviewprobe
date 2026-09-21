from pydantic import BaseModel, Field

# The endpoint is for interviewer speech (a question, at most a couple of
# sentences), not arbitrary document synthesis — this bound keeps request
# cost/latency predictable, not an attempt at a "generous" limit.
MAX_TTS_TEXT_LENGTH = 2_000


class TTSRequest(BaseModel):
    """Provider-neutral synthesis request. No Azure-specific fields (voice
    IDs, SSML, output-format enums) are exposed here — those are an
    implementation detail of the concrete provider."""

    text: str = Field(min_length=1, max_length=MAX_TTS_TEXT_LENGTH)


class TTSResponse(BaseModel):
    """Normalized synthesis result — the same shape regardless of which
    provider produced it."""

    audio: bytes
    content_type: str


class SttAuthToken(BaseModel):
    """A short-lived, browser-safe credential the client uses to open its
    own streaming STT connection directly. Never the permanent provider
    key — that never leaves the backend process."""

    access_token: str
    expires_in: int
