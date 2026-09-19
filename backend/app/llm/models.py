from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

# Generic infrastructure bound, not an interview-specific limit — a
# provider request payload cap, same spirit as SubmitAnswerRequest's
# answer length cap in app/schemas/interview.py but independent of it.
MAX_MESSAGE_CONTENT_LENGTH = 32_000


class LLMMessage(BaseModel):
    """One provider-neutral chat message. No OpenAI/Gemini SDK types are
    used here or anywhere else in this abstraction's public surface."""

    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=MAX_MESSAGE_CONTENT_LENGTH)


class LLMUsage(BaseModel):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class LLMResponse(BaseModel):
    """Normalized text-generation result — the same shape regardless of
    which provider produced it."""

    content: str
    model: str
    usage: LLMUsage | None = None


T = TypeVar("T", bound=BaseModel)


class StructuredLLMResponse(BaseModel, Generic[T]):
    """Normalized structured-generation result: `data` is already a
    validated instance of the caller's requested schema, not a raw JSON
    string the caller has to parse itself."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    data: T
    model: str
    usage: LLMUsage | None = None
