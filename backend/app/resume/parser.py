"""Structured resume parsing — deliberately separate from extraction
(app/resume/extraction.py). Extraction always produces plain text from a
file; parsing turns that text into a `ResumeProfile`. `ResumeParser` is a
provider-neutral interface (mirrors `LLMProvider` in app/llm/base.py) so a
non-LLM implementation could replace `LLMResumeParser` later without
touching `ResumeService` or the API layer at all.
"""

from abc import ABC, abstractmethod

from app.llm.base import LLMProvider
from app.resume.models import ResumeProfile
from app.resume.prompts import build_resume_parsing_messages


class ResumeParser(ABC):
    @abstractmethod
    async def parse(self, extracted_text: str) -> ResumeProfile: ...


class LLMResumeParser(ResumeParser):
    """The only implementation today: one structured LLM call over the
    extracted text, via the same provider-neutral `LLMProvider.
    generate_structured` every other structured-output call in this
    project uses (see app.evaluation.service.EvaluationService for the
    sibling pattern). `generate_structured` already guarantees `.data` is
    a schema-valid `ResumeProfile` or raises `LLMInvalidResponseError` —
    malformed output never reaches this class's caller as unvalidated
    data (see app/llm/providers/openai.py's `message.parsed is None`
    check). `ResumeService` layers its own additional content-level
    normalization on top (app.resume.validator) before anything is
    persisted.
    """

    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider

    async def parse(self, extracted_text: str) -> ResumeProfile:
        messages = build_resume_parsing_messages(extracted_text)
        response = await self.llm_provider.generate_structured(messages, ResumeProfile)
        return response.data
