import pytest
from pydantic import BaseModel, ValidationError

from app.llm.models import LLMMessage, LLMResponse, LLMUsage, StructuredLLMResponse


def test_valid_message_constructs():
    message = LLMMessage(role="user", content="Hello")

    assert message.role == "user"
    assert message.content == "Hello"


def test_all_valid_roles_accepted():
    for role in ("system", "user", "assistant"):
        LLMMessage(role=role, content="text")


def test_invalid_role_rejected():
    with pytest.raises(ValidationError):
        LLMMessage(role="not_a_role", content="text")


def test_empty_content_rejected():
    with pytest.raises(ValidationError):
        LLMMessage(role="user", content="")


def test_content_over_max_length_rejected():
    with pytest.raises(ValidationError):
        LLMMessage(role="user", content="x" * 32_001)


def test_content_at_max_length_accepted():
    message = LLMMessage(role="user", content="x" * 32_000)

    assert len(message.content) == 32_000


def test_llm_response_constructs_with_and_without_usage():
    without_usage = LLMResponse(content="hi", model="gpt-4o-mini")
    assert without_usage.usage is None

    with_usage = LLMResponse(
        content="hi",
        model="gpt-4o-mini",
        usage=LLMUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
    )
    assert with_usage.usage.total_tokens == 15


class ExampleOutput(BaseModel):
    answer: str
    score: float


def test_structured_response_holds_validated_data():
    response = StructuredLLMResponse[ExampleOutput](
        data=ExampleOutput(answer="42", score=0.9),
        model="gpt-4o-mini",
    )

    assert isinstance(response.data, ExampleOutput)
    assert response.data.answer == "42"
    assert response.data.score == 0.9
