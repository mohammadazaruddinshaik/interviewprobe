import pytest
from pydantic import BaseModel

from app.llm.base import LLMProvider
from app.llm.models import LLMMessage, LLMResponse, StructuredLLMResponse


class ExampleOutput(BaseModel):
    answer: str
    score: float


class FakeLLMProvider(LLMProvider):
    """A minimal, fully-working fake implementing the LLMProvider interface
    end-to-end. This is what future tests for the Interview Agent (Task 14+)
    would use instead of a real provider — and it doubles here as proof the
    interface is genuinely implementable without any provider SDK."""

    def __init__(self, text_response: str = "fake answer", structured_response: BaseModel | None = None):
        super().__init__(provider_name="fake", model="fake-model-v1", timeout_seconds=5, max_retries=0)
        self._text_response = text_response
        self._structured_response = structured_response

    async def generate_text(self, messages: list[LLMMessage]) -> LLMResponse:
        return LLMResponse(content=self._text_response, model=self.model)

    async def generate_structured(self, messages: list[LLMMessage], output_schema):
        return StructuredLLMResponse(data=self._structured_response, model=self.model)


async def _call_any_provider(provider: LLMProvider, messages: list[LLMMessage]) -> str:
    """Stands in for future application code that depends only on
    `LLMProvider`, never a concrete provider class."""
    response = await provider.generate_text(messages)
    return response.content


@pytest.mark.asyncio
async def test_fake_provider_satisfies_the_interface_for_generic_caller_code():
    provider = FakeLLMProvider(text_response="42")

    result = await _call_any_provider(
        provider, [LLMMessage(role="user", content="What is the answer?")]
    )

    assert result == "42"


@pytest.mark.asyncio
async def test_fake_provider_returns_validated_structured_output():
    provider = FakeLLMProvider(structured_response=ExampleOutput(answer="42", score=1.0))

    result = await provider.generate_structured([LLMMessage(role="user", content="Hi")], ExampleOutput)

    assert isinstance(result.data, ExampleOutput)
    assert result.data.answer == "42"
    assert result.data.score == 1.0
