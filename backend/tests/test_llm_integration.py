"""Optional, genuinely-real LLM provider integration test.

Gated behind `RUN_LLM_INTEGRATION_TESTS=true` (and a real `LLM_API_KEY`)
so the default test suite never makes network calls to OpenAI/Gemini or
requires credentials. Skips cleanly, with the real reason, when not
explicitly enabled — this never fakes a pass; if a real call wasn't made,
the test result says so.
"""

import os

import pytest

from app.core.config import settings
from app.llm.factory import get_llm_provider, reset_llm_provider_cache
from app.llm.models import LLMMessage

RUN_INTEGRATION = os.environ.get("RUN_LLM_INTEGRATION_TESTS", "").lower() == "true"

pytestmark = pytest.mark.skipif(
    not RUN_INTEGRATION,
    reason="RUN_LLM_INTEGRATION_TESTS is not set to 'true' — skipping real LLM provider calls.",
)


@pytest.fixture(autouse=True)
def _reset_cache():
    reset_llm_provider_cache()
    yield
    reset_llm_provider_cache()


@pytest.mark.asyncio
async def test_real_provider_generate_text():
    if not settings.llm_api_key:
        pytest.skip(
            f"LLM_API_KEY is not configured for provider '{settings.llm_provider}'; "
            "cannot perform a genuine provider call."
        )

    provider = get_llm_provider()

    response = await provider.generate_text(
        [LLMMessage(role="user", content="Reply with exactly the single word: pong")]
    )

    assert response.content
    assert response.model
