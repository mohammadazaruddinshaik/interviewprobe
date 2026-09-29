"""Task 8 — Resume Claim Investigation tests.

Covers the full investigation subsystem: models, prompts, investigator,
service-layer integration, persistence, and failure isolation. Evidence
collection only — never truth detection, never accusation.
"""

import uuid

import pytest

from app.domain.enums import (
    ClaimInvestigationStatus,
    Difficulty,
    InterviewStatus,
    InterviewTopic,
    InterviewTopicStatus,
    MessageRole,
    PlannedTopicPriority,
    QuestionType,
    ResumeExtractionStatus,
    ResumeRelevance,
    Role,
)
from app.investigation.investigator import ClaimInvestigator, LLMClaimInvestigator
from app.investigation.models import (
    ClaimInvestigation,
    ClaimInvestigationResult,
    InvestigationEvidence,
)
from app.investigation.prompts import (
    _format_claim,
    _format_evidence,
    build_investigation_messages,
)
from app.planning.models import InterviewPlan, PlannedTopic, build_claim_id
from app.resume.models import ResumeClaim, ResumeProfile
from tests.fakes import FakeInterviewRepository, FakeLLMProvider

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SESSION_ID = uuid.uuid4()

_CLAIM_RAG = ResumeClaim(claim="Built a RAG pipeline with Qdrant", category="project", source="experience")
_CLAIM_AGENTS = ResumeClaim(claim="Designed multi-agent orchestration system", category="project", source="experience")
_CLAIM_NO_TOPIC = ResumeClaim(claim="Published a paper on transformer architecture", category="research")

_CLAIM_RAG_ID = build_claim_id(_CLAIM_RAG)
_CLAIM_AGENTS_ID = build_claim_id(_CLAIM_AGENTS)
_CLAIM_NO_TOPIC_ID = build_claim_id(_CLAIM_NO_TOPIC)


def _make_plan(
    topics: list[PlannedTopic] | None = None,
) -> InterviewPlan:
    default_topics = [
        PlannedTopic(
            topic=InterviewTopic.RAG,
            competency_keys=["retrieval_augmented_generation"],
            priority=PlannedTopicPriority.HIGH,
            rationale="Core skill for RAG pipeline work",
            resume_relevance=ResumeRelevance.PRIMARY,
            related_claim_ids=[_CLAIM_RAG_ID],
            suggested_time_budget_minutes=15,
        ),
        PlannedTopic(
            topic=InterviewTopic.AI_AGENTS,
            competency_keys=["ai_agents"],
            priority=PlannedTopicPriority.MEDIUM,
            rationale="Agent orchestration experience",
            resume_relevance=ResumeRelevance.PRIMARY,
            related_claim_ids=[_CLAIM_AGENTS_ID],
            suggested_time_budget_minutes=10,
        ),
    ]
    return InterviewPlan(
        role=Role.AI_ENGINEER,
        plan_version=1,
        objectives=["Assess RAG and agent skills"],
        planned_topics=topics if topics is not None else default_topics,
    )


def _make_profile(claims: list[ResumeClaim] | None = None) -> ResumeProfile:
    return ResumeProfile(claims=claims if claims is not None else [_CLAIM_RAG, _CLAIM_AGENTS])


def _make_resume_record(profile: ResumeProfile | None = None):
    """Returns a simple namespace that mimics InterviewResume enough for
    _load_resume_profile (extraction_status, structured_profile)."""
    p = profile or _make_profile()

    class _FakeResume:
        extraction_status = ResumeExtractionStatus.READY
        structured_profile = p.model_dump(mode="json")

    return _FakeResume()


def _make_question(
    session_id: uuid.UUID = _SESSION_ID,
    seq: int = 1,
    topic: InterviewTopic = InterviewTopic.RAG,
    question_id: uuid.UUID | None = None,
) -> object:
    class _Q:
        pass

    q = _Q()
    q.id = question_id or uuid.uuid4()
    q.session_id = session_id
    q.sequence_number = seq
    q.topic = topic
    q.question_text = f"Tell me about {topic.value} — question {seq}"
    q.difficulty = Difficulty.MEDIUM
    q.question_type = QuestionType.INITIAL if seq == 1 else QuestionType.FOLLOW_UP
    q.agent_reason = None
    return q


def _make_message(
    session_id: uuid.UUID,
    question_id: uuid.UUID,
    role: MessageRole,
    content: str,
    seq: int,
) -> object:
    class _M:
        pass

    m = _M()
    m.id = uuid.uuid4()
    m.session_id = session_id
    m.question_id = question_id
    m.role = role
    m.content = content
    m.sequence_number = seq
    return m


class FakeClaimInvestigator(ClaimInvestigator):
    """In-memory investigator that returns a configurable result per claim_id."""

    def __init__(self, results: dict[str, ClaimInvestigationResult] | None = None, error: Exception | None = None):
        self._results = results or {}
        self._error = error
        self.calls: list[tuple[str, list[InvestigationEvidence]]] = []

    async def investigate(self, claim, claim_id, evidence):
        self.calls.append((claim_id, list(evidence)))
        if self._error is not None:
            raise self._error
        result = self._results.get(claim_id)
        if result is None:
            return ClaimInvestigationResult(
                claim_id=claim_id,
                status=ClaimInvestigationStatus.NOT_YET_ESTABLISHED,
                evidence_summary="No evidence assessed",
                rationale="Default fake response",
            )
        return result


# ===================================================================
# A. ClaimInvestigationStatus enum
# ===================================================================


class TestClaimInvestigationStatus:
    def test_has_exactly_four_values(self):
        assert set(ClaimInvestigationStatus) == {
            ClaimInvestigationStatus.SUPPORTED,
            ClaimInvestigationStatus.PARTIALLY_SUPPORTED,
            ClaimInvestigationStatus.LIMITED_EVIDENCE,
            ClaimInvestigationStatus.NOT_YET_ESTABLISHED,
        }

    def test_no_false_or_liar_value(self):
        names = {s.name for s in ClaimInvestigationStatus}
        assert "FALSE" not in names
        assert "LIAR" not in names
        assert "UNVERIFIED" not in names


# ===================================================================
# B. Investigation data models
# ===================================================================


class TestInvestigationEvidence:
    def test_frozen(self):
        ev = InvestigationEvidence(question_sequence=1, question_text="Q", answer_text="A")
        with pytest.raises(Exception):
            ev.question_sequence = 2

    def test_construction(self):
        ev = InvestigationEvidence(question_sequence=3, question_text="What?", answer_text="Something")
        assert ev.question_sequence == 3
        assert ev.question_text == "What?"
        assert ev.answer_text == "Something"


class TestClaimInvestigation:
    def test_defaults(self):
        inv = ClaimInvestigation(claim_id="claim_abc123")
        assert inv.status == ClaimInvestigationStatus.NOT_YET_ESTABLISHED
        assert inv.evidence_summary == ""
        assert inv.rationale == ""

    def test_extra_forbid(self):
        with pytest.raises(Exception):
            ClaimInvestigation(claim_id="claim_abc123", unknown_field="x")

    def test_claim_id_min_length(self):
        with pytest.raises(Exception):
            ClaimInvestigation(claim_id="")

    def test_roundtrip_serialization(self):
        inv = ClaimInvestigation(
            claim_id="claim_abc123",
            status=ClaimInvestigationStatus.SUPPORTED,
            evidence_summary="Candidate described chunking strategy in detail",
            rationale="Specific mention of recursive character splitting with overlap",
        )
        data = inv.model_dump(mode="json")
        restored = ClaimInvestigation.model_validate(data)
        assert restored == inv


class TestClaimInvestigationResult:
    def test_requires_nonempty_summary_and_rationale(self):
        with pytest.raises(Exception):
            ClaimInvestigationResult(
                claim_id="claim_abc123",
                status=ClaimInvestigationStatus.SUPPORTED,
                evidence_summary="",
                rationale="reason",
            )
        with pytest.raises(Exception):
            ClaimInvestigationResult(
                claim_id="claim_abc123",
                status=ClaimInvestigationStatus.SUPPORTED,
                evidence_summary="summary",
                rationale="",
            )

    def test_valid_construction(self):
        result = ClaimInvestigationResult(
            claim_id="claim_abc123",
            status=ClaimInvestigationStatus.PARTIALLY_SUPPORTED,
            evidence_summary="Some evidence found",
            rationale="Candidate mentioned Qdrant but not chunking strategy",
        )
        assert result.status == ClaimInvestigationStatus.PARTIALLY_SUPPORTED


# ===================================================================
# C. Prompt construction
# ===================================================================


class TestFormatClaim:
    def test_contains_claim_id_and_text(self):
        result = _format_claim(_CLAIM_RAG, _CLAIM_RAG_ID)
        assert _CLAIM_RAG_ID in result
        assert _CLAIM_RAG.claim in result

    def test_includes_category_when_present(self):
        result = _format_claim(_CLAIM_RAG, _CLAIM_RAG_ID)
        assert "project" in result

    def test_includes_source_when_present(self):
        result = _format_claim(_CLAIM_RAG, _CLAIM_RAG_ID)
        assert "experience" in result

    def test_marks_as_untrusted(self):
        result = _format_claim(_CLAIM_RAG, _CLAIM_RAG_ID)
        assert "unverified" in result.lower() or "untrusted" in result.lower()


class TestFormatEvidence:
    def test_no_evidence(self):
        result = _format_evidence([])
        assert "none" in result.lower()

    def test_formats_qa_pairs(self):
        evidence = [
            InvestigationEvidence(question_sequence=1, question_text="What is RAG?", answer_text="Retrieval then generation"),
            InvestigationEvidence(question_sequence=2, question_text="How did you chunk?", answer_text="Recursive splitting"),
        ]
        result = _format_evidence(evidence)
        assert "Turn 1" in result
        assert "Turn 2" in result
        assert "What is RAG?" in result
        assert "Recursive splitting" in result

    def test_marks_answers_as_untrusted(self):
        evidence = [InvestigationEvidence(question_sequence=1, question_text="Q", answer_text="A")]
        result = _format_evidence(evidence)
        assert "untrusted" in result.lower()


class TestBuildInvestigationMessages:
    def test_returns_system_and_user_messages(self):
        evidence = [InvestigationEvidence(question_sequence=1, question_text="Q", answer_text="A")]
        messages = build_investigation_messages(_CLAIM_RAG, _CLAIM_RAG_ID, evidence)
        assert len(messages) == 2
        assert messages[0].role == "system"
        assert messages[1].role == "user"

    def test_system_message_contains_status_definitions(self):
        messages = build_investigation_messages(_CLAIM_RAG, _CLAIM_RAG_ID, [])
        system_content = messages[0].content
        assert "SUPPORTED" in system_content
        assert "PARTIALLY_SUPPORTED" in system_content
        assert "LIMITED_EVIDENCE" in system_content
        assert "NOT_YET_ESTABLISHED" in system_content

    def test_system_message_contains_assessment_criteria(self):
        messages = build_investigation_messages(_CLAIM_RAG, _CLAIM_RAG_ID, [])
        system_content = messages[0].content
        assert "technical specificity" in system_content
        assert "implementation details" in system_content

    def test_system_message_rejects_style_based_assessment(self):
        messages = build_investigation_messages(_CLAIM_RAG, _CLAIM_RAG_ID, [])
        system_content = messages[0].content
        assert "writing style" in system_content.lower()
        assert "confidence" in system_content.lower()

    def test_system_message_contains_injection_defense(self):
        messages = build_investigation_messages(_CLAIM_RAG, _CLAIM_RAG_ID, [])
        system_content = messages[0].content
        assert "ignore previous" in system_content.lower()

    def test_user_message_contains_claim_and_evidence(self):
        evidence = [InvestigationEvidence(question_sequence=1, question_text="Q", answer_text="A")]
        messages = build_investigation_messages(_CLAIM_RAG, _CLAIM_RAG_ID, evidence)
        user_content = messages[1].content
        assert _CLAIM_RAG.claim in user_content
        assert "Turn 1" in user_content


# ===================================================================
# D. Investigator
# ===================================================================


class TestLLMClaimInvestigator:
    @pytest.mark.asyncio
    async def test_calls_llm_with_structured_output(self):
        expected = ClaimInvestigationResult(
            claim_id=_CLAIM_RAG_ID,
            status=ClaimInvestigationStatus.SUPPORTED,
            evidence_summary="Candidate described pipeline architecture",
            rationale="Mentioned Qdrant, chunking, and reranking",
        )
        fake_llm = FakeLLMProvider(structured_responses={"ClaimInvestigationResult": expected})
        investigator = LLMClaimInvestigator(fake_llm)

        evidence = [InvestigationEvidence(question_sequence=1, question_text="Q", answer_text="A")]
        result = await investigator.investigate(_CLAIM_RAG, _CLAIM_RAG_ID, evidence)

        assert result == expected
        assert len(fake_llm.calls) == 1
        assert fake_llm.calls[0][0] == "ClaimInvestigationResult"

    @pytest.mark.asyncio
    async def test_propagates_llm_error(self):
        fake_llm = FakeLLMProvider(error=RuntimeError("LLM unavailable"))
        investigator = LLMClaimInvestigator(fake_llm)

        evidence = [InvestigationEvidence(question_sequence=1, question_text="Q", answer_text="A")]
        with pytest.raises(RuntimeError, match="LLM unavailable"):
            await investigator.investigate(_CLAIM_RAG, _CLAIM_RAG_ID, evidence)


# ===================================================================
# E. Claim ID determinism
# ===================================================================


class TestClaimIdDeterminism:
    def test_same_claim_same_id(self):
        a = build_claim_id(_CLAIM_RAG)
        b = build_claim_id(ResumeClaim(claim="Built a RAG pipeline with Qdrant", category="project", source="experience"))
        assert a == b

    def test_different_claims_different_ids(self):
        assert _CLAIM_RAG_ID != _CLAIM_AGENTS_ID

    def test_claim_id_format(self):
        assert _CLAIM_RAG_ID.startswith("claim_")
        assert len(_CLAIM_RAG_ID) == len("claim_") + 12


# ===================================================================
# F. Repository persistence (via FakeInterviewRepository)
# ===================================================================


class TestFakeRepositoryInvestigationPersistence:
    def test_load_empty_by_default(self):
        repo = FakeInterviewRepository()
        result = repo.load_claim_investigations(_SESSION_ID)
        assert result == []

    def test_save_and_load_roundtrip(self):
        repo = FakeInterviewRepository()
        investigations = [
            ClaimInvestigation(
                claim_id=_CLAIM_RAG_ID,
                status=ClaimInvestigationStatus.SUPPORTED,
                evidence_summary="Good evidence",
                rationale="Detailed explanation",
            ),
        ]
        repo.save_claim_investigations(_SESSION_ID, investigations)
        loaded = repo.load_claim_investigations(_SESSION_ID)
        assert len(loaded) == 1
        assert loaded[0].claim_id == _CLAIM_RAG_ID
        assert loaded[0].status == ClaimInvestigationStatus.SUPPORTED

    def test_save_overwrites_previous(self):
        repo = FakeInterviewRepository()
        repo.save_claim_investigations(
            _SESSION_ID,
            [ClaimInvestigation(claim_id=_CLAIM_RAG_ID)],
        )
        repo.save_claim_investigations(
            _SESSION_ID,
            [
                ClaimInvestigation(
                    claim_id=_CLAIM_RAG_ID,
                    status=ClaimInvestigationStatus.PARTIALLY_SUPPORTED,
                    evidence_summary="Updated",
                    rationale="New evidence",
                ),
            ],
        )
        loaded = repo.load_claim_investigations(_SESSION_ID)
        assert len(loaded) == 1
        assert loaded[0].status == ClaimInvestigationStatus.PARTIALLY_SUPPORTED


# ===================================================================
# G. Service-layer integration (_investigate_relevant_claims)
# ===================================================================

# The service method is async and uses self.investigator, self.repository,
# self._load_resume_profile. We test it by constructing an InterviewService
# with fakes.


def _build_service(
    plan=None,
    resume=None,
    questions=None,
    messages=None,
    investigator=None,
):
    """Build an InterviewService with a FakeInterviewRepository and no
    workflow (investigation never touches the graph)."""
    from unittest.mock import MagicMock

    from app.services.interview_service import InterviewService

    repo = FakeInterviewRepository(
        plan=plan,
        resume=resume,
        questions=questions or [],
        messages=messages or [],
    )

    workflow = MagicMock()
    service = InterviewService(
        repository=repo,
        workflow=workflow,
        planner=None,
        investigator=investigator,
    )
    return service, repo


class TestInvestigateRelevantClaims:
    """Tests for InterviewService._investigate_relevant_claims."""

    @pytest.mark.asyncio
    async def test_skips_when_no_investigator(self):
        service, repo = _build_service(investigator=None)
        question = _make_question()
        await service._investigate_relevant_claims(_SESSION_ID, question)
        assert repo.load_claim_investigations(_SESSION_ID) == []

    @pytest.mark.asyncio
    async def test_skips_when_no_plan(self):
        investigator = FakeClaimInvestigator()
        service, repo = _build_service(plan=None, investigator=investigator)
        question = _make_question()
        await service._investigate_relevant_claims(_SESSION_ID, question)
        assert len(investigator.calls) == 0

    @pytest.mark.asyncio
    async def test_skips_when_topic_has_no_related_claims(self):
        plan = _make_plan(
            topics=[
                PlannedTopic(
                    topic=InterviewTopic.RAG,
                    competency_keys=["retrieval_augmented_generation"],
                    priority=PlannedTopicPriority.HIGH,
                    rationale="General RAG coverage",
                    resume_relevance=ResumeRelevance.NONE,
                    related_claim_ids=[],
                    suggested_time_budget_minutes=15,
                ),
            ]
        )
        investigator = FakeClaimInvestigator()
        service, _ = _build_service(plan=plan, investigator=investigator)
        question = _make_question(topic=InterviewTopic.RAG)
        await service._investigate_relevant_claims(_SESSION_ID, question)
        assert len(investigator.calls) == 0

    @pytest.mark.asyncio
    async def test_skips_when_no_resume_profile(self):
        plan = _make_plan()
        investigator = FakeClaimInvestigator()
        service, _ = _build_service(plan=plan, resume=None, investigator=investigator)
        question = _make_question(topic=InterviewTopic.RAG)
        await service._investigate_relevant_claims(_SESSION_ID, question)
        assert len(investigator.calls) == 0

    @pytest.mark.asyncio
    async def test_skips_when_question_topic_not_in_plan(self):
        plan = _make_plan()
        investigator = FakeClaimInvestigator()
        resume = _make_resume_record()
        service, _ = _build_service(plan=plan, resume=resume, investigator=investigator)
        question = _make_question(topic=InterviewTopic.LLM_FUNDAMENTALS)
        await service._investigate_relevant_claims(_SESSION_ID, question)
        assert len(investigator.calls) == 0

    @pytest.mark.asyncio
    async def test_investigates_claim_for_answered_question_topic(self):
        plan = _make_plan()
        resume = _make_resume_record()
        q1 = _make_question(topic=InterviewTopic.RAG, seq=1)
        m1_interviewer = _make_message(_SESSION_ID, q1.id, MessageRole.INTERVIEWER, q1.question_text, 1)
        m1_candidate = _make_message(_SESSION_ID, q1.id, MessageRole.CANDIDATE, "I used Qdrant with HNSW indexing", 2)

        investigator = FakeClaimInvestigator()
        service, repo = _build_service(
            plan=plan,
            resume=resume,
            questions=[q1],
            messages=[m1_interviewer, m1_candidate],
            investigator=investigator,
        )
        await service._investigate_relevant_claims(_SESSION_ID, q1)

        assert len(investigator.calls) == 1
        call_claim_id, call_evidence = investigator.calls[0]
        assert call_claim_id == _CLAIM_RAG_ID
        assert len(call_evidence) == 1
        assert call_evidence[0].answer_text == "I used Qdrant with HNSW indexing"

    @pytest.mark.asyncio
    async def test_persists_investigation_result(self):
        plan = _make_plan()
        resume = _make_resume_record()
        q1 = _make_question(topic=InterviewTopic.RAG, seq=1)
        m1 = _make_message(_SESSION_ID, q1.id, MessageRole.CANDIDATE, "Answer", 2)

        result = ClaimInvestigationResult(
            claim_id=_CLAIM_RAG_ID,
            status=ClaimInvestigationStatus.SUPPORTED,
            evidence_summary="Described pipeline in detail",
            rationale="Mentioned specific components",
        )
        investigator = FakeClaimInvestigator(results={_CLAIM_RAG_ID: result})
        service, repo = _build_service(
            plan=plan,
            resume=resume,
            questions=[q1],
            messages=[m1],
            investigator=investigator,
        )
        await service._investigate_relevant_claims(_SESSION_ID, q1)

        saved = repo.load_claim_investigations(_SESSION_ID)
        assert len(saved) == 1
        assert saved[0].claim_id == _CLAIM_RAG_ID
        assert saved[0].status == ClaimInvestigationStatus.SUPPORTED

    @pytest.mark.asyncio
    async def test_multi_turn_evidence_accumulation(self):
        plan = _make_plan()
        resume = _make_resume_record()
        q1 = _make_question(topic=InterviewTopic.RAG, seq=1)
        q2 = _make_question(topic=InterviewTopic.RAG, seq=2)
        m1 = _make_message(_SESSION_ID, q1.id, MessageRole.CANDIDATE, "First answer", 2)
        m2 = _make_message(_SESSION_ID, q2.id, MessageRole.CANDIDATE, "Second answer", 4)

        investigator = FakeClaimInvestigator()
        service, repo = _build_service(
            plan=plan,
            resume=resume,
            questions=[q1, q2],
            messages=[m1, m2],
            investigator=investigator,
        )
        await service._investigate_relevant_claims(_SESSION_ID, q2)

        assert len(investigator.calls) == 1
        _, evidence = investigator.calls[0]
        assert len(evidence) == 2
        assert evidence[0].answer_text == "First answer"
        assert evidence[1].answer_text == "Second answer"

    @pytest.mark.asyncio
    async def test_cross_topic_evidence_gathering(self):
        """When a claim appears in multiple topics, evidence from ALL
        topics is gathered."""
        shared_plan = _make_plan(
            topics=[
                PlannedTopic(
                    topic=InterviewTopic.RAG,
                    competency_keys=["retrieval_augmented_generation"],
                    priority=PlannedTopicPriority.HIGH,
                    rationale="RAG probe",
                    resume_relevance=ResumeRelevance.PRIMARY,
                    related_claim_ids=[_CLAIM_RAG_ID],
                    suggested_time_budget_minutes=15,
                ),
                PlannedTopic(
                    topic=InterviewTopic.AI_AGENTS,
                    competency_keys=["ai_agents"],
                    priority=PlannedTopicPriority.MEDIUM,
                    rationale="Agents probe — also linked to RAG claim",
                    resume_relevance=ResumeRelevance.PRIMARY,
                    related_claim_ids=[_CLAIM_RAG_ID, _CLAIM_AGENTS_ID],
                    suggested_time_budget_minutes=10,
                ),
            ]
        )
        resume = _make_resume_record()
        q_rag = _make_question(topic=InterviewTopic.RAG, seq=1)
        q_agents = _make_question(topic=InterviewTopic.AI_AGENTS, seq=2)
        m_rag = _make_message(_SESSION_ID, q_rag.id, MessageRole.CANDIDATE, "RAG answer", 2)
        m_agents = _make_message(_SESSION_ID, q_agents.id, MessageRole.CANDIDATE, "Agent answer", 4)

        investigator = FakeClaimInvestigator()
        service, _ = _build_service(
            plan=shared_plan,
            resume=resume,
            questions=[q_rag, q_agents],
            messages=[m_rag, m_agents],
            investigator=investigator,
        )
        await service._investigate_relevant_claims(_SESSION_ID, q_agents)

        rag_call = next((c for c in investigator.calls if c[0] == _CLAIM_RAG_ID), None)
        assert rag_call is not None
        _, rag_evidence = rag_call
        assert len(rag_evidence) == 2
        texts = {e.answer_text for e in rag_evidence}
        assert "RAG answer" in texts
        assert "Agent answer" in texts

    @pytest.mark.asyncio
    async def test_only_investigates_claims_for_answered_topic(self):
        """If the question is on RAG, only RAG-linked claims are investigated,
        not AI_AGENTS-only claims."""
        plan = _make_plan()
        resume = _make_resume_record()
        q1 = _make_question(topic=InterviewTopic.RAG, seq=1)
        m1 = _make_message(_SESSION_ID, q1.id, MessageRole.CANDIDATE, "Answer", 2)

        investigator = FakeClaimInvestigator()
        service, _ = _build_service(
            plan=plan, resume=resume, questions=[q1], messages=[m1], investigator=investigator
        )
        await service._investigate_relevant_claims(_SESSION_ID, q1)

        investigated_ids = [c[0] for c in investigator.calls]
        assert _CLAIM_RAG_ID in investigated_ids
        assert _CLAIM_AGENTS_ID not in investigated_ids

    @pytest.mark.asyncio
    async def test_skips_claim_with_no_evidence(self):
        """If no candidate answers exist for a claim's topics, skip it."""
        plan = _make_plan()
        resume = _make_resume_record()
        q1 = _make_question(topic=InterviewTopic.RAG, seq=1)

        investigator = FakeClaimInvestigator()
        service, _ = _build_service(
            plan=plan, resume=resume, questions=[q1], messages=[], investigator=investigator
        )
        await service._investigate_relevant_claims(_SESSION_ID, q1)
        assert len(investigator.calls) == 0

    @pytest.mark.asyncio
    async def test_failure_isolation_logs_and_continues(self):
        """Investigation errors must not propagate — they are logged and
        the main answer flow continues."""
        plan = _make_plan()
        resume = _make_resume_record()
        q1 = _make_question(topic=InterviewTopic.RAG, seq=1)
        m1 = _make_message(_SESSION_ID, q1.id, MessageRole.CANDIDATE, "Answer", 2)

        investigator = FakeClaimInvestigator(error=RuntimeError("LLM boom"))
        service, repo = _build_service(
            plan=plan, resume=resume, questions=[q1], messages=[m1], investigator=investigator
        )
        await service._investigate_relevant_claims(_SESSION_ID, q1)
        assert repo.load_claim_investigations(_SESSION_ID) == []

    @pytest.mark.asyncio
    async def test_preserves_existing_investigations_for_other_claims(self):
        """When investigating one claim, existing investigations for other
        claims are preserved."""
        plan = _make_plan(
            topics=[
                PlannedTopic(
                    topic=InterviewTopic.RAG,
                    competency_keys=["retrieval_augmented_generation"],
                    priority=PlannedTopicPriority.HIGH,
                    rationale="RAG probe",
                    resume_relevance=ResumeRelevance.PRIMARY,
                    related_claim_ids=[_CLAIM_RAG_ID],
                    suggested_time_budget_minutes=15,
                ),
            ]
        )
        resume = _make_resume_record()
        q1 = _make_question(topic=InterviewTopic.RAG, seq=1)
        m1 = _make_message(_SESSION_ID, q1.id, MessageRole.CANDIDATE, "Answer", 2)

        investigator = FakeClaimInvestigator()
        service, repo = _build_service(
            plan=plan, resume=resume, questions=[q1], messages=[m1], investigator=investigator
        )
        repo.save_claim_investigations(
            _SESSION_ID,
            [
                ClaimInvestigation(
                    claim_id=_CLAIM_AGENTS_ID,
                    status=ClaimInvestigationStatus.PARTIALLY_SUPPORTED,
                    evidence_summary="Prior agents evidence",
                    rationale="Prior reason",
                ),
            ],
        )

        await service._investigate_relevant_claims(_SESSION_ID, q1)

        saved = repo.load_claim_investigations(_SESSION_ID)
        ids = {inv.claim_id for inv in saved}
        assert _CLAIM_AGENTS_ID in ids
        assert _CLAIM_RAG_ID in ids

    @pytest.mark.asyncio
    async def test_updates_existing_investigation_on_new_evidence(self):
        """A second investigation of the same claim overwrites with new result."""
        plan = _make_plan()
        resume = _make_resume_record()
        q1 = _make_question(topic=InterviewTopic.RAG, seq=1)
        q2 = _make_question(topic=InterviewTopic.RAG, seq=2)
        m1 = _make_message(_SESSION_ID, q1.id, MessageRole.CANDIDATE, "First", 2)
        m2 = _make_message(_SESSION_ID, q2.id, MessageRole.CANDIDATE, "Second deeper", 4)

        first_result = ClaimInvestigationResult(
            claim_id=_CLAIM_RAG_ID,
            status=ClaimInvestigationStatus.LIMITED_EVIDENCE,
            evidence_summary="Vague initial answer",
            rationale="Not enough detail yet",
        )
        second_result = ClaimInvestigationResult(
            claim_id=_CLAIM_RAG_ID,
            status=ClaimInvestigationStatus.SUPPORTED,
            evidence_summary="Detailed follow-up answer",
            rationale="Concrete architecture described",
        )

        investigator1 = FakeClaimInvestigator(results={_CLAIM_RAG_ID: first_result})
        service, repo = _build_service(
            plan=plan,
            resume=resume,
            questions=[q1],
            messages=[m1],
            investigator=investigator1,
        )
        await service._investigate_relevant_claims(_SESSION_ID, q1)

        saved1 = repo.load_claim_investigations(_SESSION_ID)
        assert saved1[0].status == ClaimInvestigationStatus.LIMITED_EVIDENCE

        investigator2 = FakeClaimInvestigator(results={_CLAIM_RAG_ID: second_result})
        service.investigator = investigator2
        repo._messages = [m1, m2]
        repo.questions = [q1, q2]
        await service._investigate_relevant_claims(_SESSION_ID, q2)

        saved2 = repo.load_claim_investigations(_SESSION_ID)
        rag_inv = next(inv for inv in saved2 if inv.claim_id == _CLAIM_RAG_ID)
        assert rag_inv.status == ClaimInvestigationStatus.SUPPORTED

    @pytest.mark.asyncio
    async def test_does_not_investigate_interviewer_messages(self):
        """Only CANDIDATE messages are gathered as evidence, never
        INTERVIEWER messages."""
        plan = _make_plan()
        resume = _make_resume_record()
        q1 = _make_question(topic=InterviewTopic.RAG, seq=1)
        m_interviewer = _make_message(_SESSION_ID, q1.id, MessageRole.INTERVIEWER, "The question", 1)
        m_candidate = _make_message(_SESSION_ID, q1.id, MessageRole.CANDIDATE, "My answer", 2)

        investigator = FakeClaimInvestigator()
        service, _ = _build_service(
            plan=plan,
            resume=resume,
            questions=[q1],
            messages=[m_interviewer, m_candidate],
            investigator=investigator,
        )
        await service._investigate_relevant_claims(_SESSION_ID, q1)

        assert len(investigator.calls) == 1
        _, evidence = investigator.calls[0]
        assert len(evidence) == 1
        assert evidence[0].answer_text == "My answer"

    @pytest.mark.asyncio
    async def test_evidence_contains_correct_question_text(self):
        """Evidence items carry the question text, not just the answer."""
        plan = _make_plan()
        resume = _make_resume_record()
        q1 = _make_question(topic=InterviewTopic.RAG, seq=1)
        m1 = _make_message(_SESSION_ID, q1.id, MessageRole.CANDIDATE, "Answer", 2)

        investigator = FakeClaimInvestigator()
        service, _ = _build_service(
            plan=plan, resume=resume, questions=[q1], messages=[m1], investigator=investigator
        )
        await service._investigate_relevant_claims(_SESSION_ID, q1)

        _, evidence = investigator.calls[0]
        assert evidence[0].question_text == q1.question_text
        assert evidence[0].question_sequence == 1

    @pytest.mark.asyncio
    async def test_claim_id_mismatch_skips_claim(self):
        """If the plan references a claim_id that doesn't match any resume
        claim, it's silently skipped."""
        bad_plan = _make_plan(
            topics=[
                PlannedTopic(
                    topic=InterviewTopic.RAG,
                    competency_keys=["retrieval_augmented_generation"],
                    priority=PlannedTopicPriority.HIGH,
                    rationale="RAG probe",
                    resume_relevance=ResumeRelevance.PRIMARY,
                    related_claim_ids=["claim_doesnotexist"],
                    suggested_time_budget_minutes=15,
                ),
            ]
        )
        resume = _make_resume_record()
        q1 = _make_question(topic=InterviewTopic.RAG, seq=1)
        m1 = _make_message(_SESSION_ID, q1.id, MessageRole.CANDIDATE, "Answer", 2)

        investigator = FakeClaimInvestigator()
        service, _ = _build_service(
            plan=bad_plan, resume=resume, questions=[q1], messages=[m1], investigator=investigator
        )
        await service._investigate_relevant_claims(_SESSION_ID, q1)
        assert len(investigator.calls) == 0

    @pytest.mark.asyncio
    async def test_resume_extraction_not_ready_skips(self):
        """If the resume exists but extraction_status is not READY, skip."""

        class _NotReadyResume:
            extraction_status = ResumeExtractionStatus.FAILED
            structured_profile = None

        investigator = FakeClaimInvestigator()
        service, _ = _build_service(
            plan=_make_plan(),
            resume=_NotReadyResume(),
            investigator=investigator,
        )
        q1 = _make_question(topic=InterviewTopic.RAG, seq=1)
        await service._investigate_relevant_claims(_SESSION_ID, q1)
        assert len(investigator.calls) == 0

    @pytest.mark.asyncio
    async def test_resume_with_no_claims_skips(self):
        """If the resume profile has no claims, skip investigation."""
        resume = _make_resume_record(profile=_make_profile(claims=[]))
        investigator = FakeClaimInvestigator()
        service, _ = _build_service(
            plan=_make_plan(), resume=resume, investigator=investigator
        )
        q1 = _make_question(topic=InterviewTopic.RAG, seq=1)
        await service._investigate_relevant_claims(_SESSION_ID, q1)
        assert len(investigator.calls) == 0
