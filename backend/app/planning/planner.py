"""The provider-neutral Interview Planner.

    InterviewPlanningInput
            ↓
       InterviewPlanner
            ↓
      structured LLM output
            ↓
        InterviewPlan
            ↓
    validate_interview_plan()
            ↓
       validated plan

Follows the same pattern as `LLMResumeParser` (app/resume/parser.py):
a provider-neutral interface (`InterviewPlanner`) with an LLM-backed
implementation (`LLMInterviewPlanner`). Depends only on the existing
`LLMProvider` abstraction — never on OpenAI or Gemini SDKs directly.

Not connected to InterviewService, LangGraph, interview_topics, Redis,
or PostgreSQL. Independently callable and testable.
"""

from abc import ABC, abstractmethod

from app.llm.base import LLMProvider
from app.planning.models import InterviewPlan, InterviewPlanningInput
from app.planning.prompts import build_planning_messages
from app.planning.validator import InvalidInterviewPlanError, validate_interview_plan


class InterviewPlanner(ABC):
    """Provider-neutral interface for interview plan generation."""

    @abstractmethod
    async def plan(self, planning_input: InterviewPlanningInput) -> InterviewPlan: ...


class LLMInterviewPlanner(InterviewPlanner):
    """The LLM-backed implementation: one structured `generate_structured`
    call, followed by cross-object validation.

    `generate_structured` already guarantees `.data` is a schema-valid
    `InterviewPlan` (Pydantic structural validation runs during parsing)
    or raises `LLMInvalidResponseError`. This class then runs the
    cross-object `validate_interview_plan` check — which catches
    invariants Pydantic alone cannot (unknown claim IDs, time budget
    overflow, role mismatch between input and output).

    If cross-object validation fails, the error is re-raised as
    `InvalidInterviewPlanError` with a descriptive message — the caller
    sees a domain exception, never a raw provider error or Pydantic
    internal. `LLMError` subclasses (timeout, rate limit, provider
    unavailable) propagate unchanged through the existing exception
    hierarchy.
    """

    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider

    async def plan(self, planning_input: InterviewPlanningInput) -> InterviewPlan:
        messages = build_planning_messages(planning_input)
        response = await self.llm_provider.generate_structured(messages, InterviewPlan)
        interview_plan = response.data
        validate_interview_plan(planning_input, interview_plan)
        return interview_plan
