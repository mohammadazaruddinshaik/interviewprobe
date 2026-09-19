"""Task 21 — `app.evaluation.validator.validate_and_normalize`: pure,
deterministic backend validation of an LLM-proposed `EvaluationResult`.

Some cases here build an `EvaluationResult` via `model_construct` (which
skips Pydantic's own field validation) specifically to simulate a
structured-output value that slipped past `Field(ge=0, le=10)` — e.g. a
provider that doesn't enforce the schema as strictly as this project's own
`EvaluationResult(...)` constructor does. That is the only way to reach
`validate_and_normalize`'s own defensive score checks at all, since the
normal constructor already rejects out-of-range/non-finite scores itself.
"""

import math
import uuid

import pytest

from app.domain.enums import InterviewTopic
from app.evaluation.models import EvaluationResult, EvidenceItem
from app.evaluation.validator import (
    MAX_EVIDENCE_ITEMS,
    MAX_STRENGTHS,
    MAX_WEAKNESSES,
    validate_and_normalize,
)
from app.llm.exceptions import LLMInvalidResponseError


def valid_result(**overrides) -> EvaluationResult:
    defaults = dict(
        technical_knowledge_score=7.0,
        reasoning_score=6.0,
        depth_score=5.0,
        communication_score=8.0,
        overall_score=1.0,  # deliberately wrong on purpose in most tests below
        strengths=["Clear explanation of retrieval."],
        weaknesses=["Missed reranking trade-offs."],
        evidence=[],
    )
    defaults.update(overrides)
    return EvaluationResult(**defaults)


# ---------------------------------------------------------------------------
# Deterministic overall score
# ---------------------------------------------------------------------------


def test_overall_score_is_the_equal_weight_average_of_the_four_components():
    result = valid_result(
        technical_knowledge_score=8.0, reasoning_score=6.0, depth_score=4.0, communication_score=10.0
    )

    validated = validate_and_normalize(result, valid_question_ids=set())

    assert validated.overall_score == 7.0  # (8+6+4+10)/4


def test_overall_score_ignores_the_llms_own_proposal_entirely():
    result = valid_result(
        technical_knowledge_score=5.0, reasoning_score=5.0, depth_score=5.0, communication_score=5.0,
        overall_score=0.0,
    )

    validated = validate_and_normalize(result, valid_question_ids=set())

    assert validated.overall_score == 5.0
    assert validated.overall_score != result.overall_score


def test_overall_score_is_rounded_to_two_decimal_places():
    result = valid_result(
        technical_knowledge_score=7.0, reasoning_score=7.0, depth_score=8.0, communication_score=8.0
    )

    validated = validate_and_normalize(result, valid_question_ids=set())

    assert validated.overall_score == 7.5


# ---------------------------------------------------------------------------
# Score validation — out of range / non-finite
# ---------------------------------------------------------------------------


def test_score_above_ten_is_rejected():
    result = EvaluationResult.model_construct(
        technical_knowledge_score=15.0,
        reasoning_score=5.0,
        depth_score=5.0,
        communication_score=5.0,
        overall_score=5.0,
        strengths=[],
        weaknesses=[],
        evidence=[],
    )

    with pytest.raises(LLMInvalidResponseError):
        validate_and_normalize(result, valid_question_ids=set())


def test_negative_score_is_rejected():
    result = EvaluationResult.model_construct(
        technical_knowledge_score=5.0,
        reasoning_score=-1.0,
        depth_score=5.0,
        communication_score=5.0,
        overall_score=5.0,
        strengths=[],
        weaknesses=[],
        evidence=[],
    )

    with pytest.raises(LLMInvalidResponseError):
        validate_and_normalize(result, valid_question_ids=set())


def test_nan_score_is_rejected():
    result = EvaluationResult.model_construct(
        technical_knowledge_score=5.0,
        reasoning_score=5.0,
        depth_score=math.nan,
        communication_score=5.0,
        overall_score=5.0,
        strengths=[],
        weaknesses=[],
        evidence=[],
    )

    with pytest.raises(LLMInvalidResponseError):
        validate_and_normalize(result, valid_question_ids=set())


def test_infinite_score_is_rejected():
    result = EvaluationResult.model_construct(
        technical_knowledge_score=5.0,
        reasoning_score=5.0,
        depth_score=5.0,
        communication_score=math.inf,
        overall_score=5.0,
        strengths=[],
        weaknesses=[],
        evidence=[],
    )

    with pytest.raises(LLMInvalidResponseError):
        validate_and_normalize(result, valid_question_ids=set())


# ---------------------------------------------------------------------------
# Strengths / weaknesses
# ---------------------------------------------------------------------------


def test_empty_and_blank_strengths_are_dropped():
    result = valid_result(strengths=["Good communication.", "", "   ", "Solid fundamentals."])

    validated = validate_and_normalize(result, valid_question_ids=set())

    assert validated.strengths == ["Good communication.", "Solid fundamentals."]


def test_strengths_are_trimmed_and_capped_at_the_maximum_count():
    result = valid_result(strengths=[f"strength {i}" for i in range(MAX_STRENGTHS + 5)])

    validated = validate_and_normalize(result, valid_question_ids=set())

    assert len(validated.strengths) == MAX_STRENGTHS


def test_weaknesses_are_cleaned_the_same_way_as_strengths():
    result = valid_result(weaknesses=["", "Needs more depth on caching."])

    validated = validate_and_normalize(result, valid_question_ids=set())

    assert validated.weaknesses == ["Needs more depth on caching."]


def test_weaknesses_capped_at_maximum_count():
    result = valid_result(weaknesses=[f"weakness {i}" for i in range(MAX_WEAKNESSES + 3)])

    validated = validate_and_normalize(result, valid_question_ids=set())

    assert len(validated.weaknesses) == MAX_WEAKNESSES


# ---------------------------------------------------------------------------
# Evidence — unknown/malformed question IDs handled safely, never fabricated
# ---------------------------------------------------------------------------


def test_evidence_with_a_known_question_id_keeps_the_reference():
    question_id = uuid.uuid4()
    result = valid_result(
        evidence=[
            EvidenceItem(
                question_id=str(question_id),
                topic=InterviewTopic.DATABASES,
                claim="Understood indexing trade-offs.",
                evidence="Explained that indexes speed up reads but slow down writes.",
            )
        ]
    )

    validated = validate_and_normalize(result, valid_question_ids={question_id})

    assert len(validated.evidence) == 1
    assert validated.evidence[0]["question_id"] == str(question_id)
    assert validated.evidence[0]["topic"] == "DATABASES"


def test_evidence_with_an_unknown_question_id_drops_only_the_reference():
    unrelated_id = uuid.uuid4()
    result = valid_result(
        evidence=[
            EvidenceItem(
                question_id=str(unrelated_id),
                claim="Understood indexing trade-offs.",
                evidence="Explained the read/write trade-off.",
            )
        ]
    )

    # `unrelated_id` is not in the interview's real question IDs.
    validated = validate_and_normalize(result, valid_question_ids={uuid.uuid4()})

    assert len(validated.evidence) == 1  # claim/evidence text preserved
    assert "question_id" not in validated.evidence[0]  # invented reference dropped, not persisted


def test_evidence_with_a_malformed_question_id_string_is_normalized_safely():
    result = valid_result(
        evidence=[
            EvidenceItem(question_id="not-a-uuid", claim="A claim.", evidence="Some evidence.")
        ]
    )

    validated = validate_and_normalize(result, valid_question_ids={uuid.uuid4()})

    assert len(validated.evidence) == 1
    assert "question_id" not in validated.evidence[0]


def test_evidence_with_empty_claim_or_evidence_text_is_dropped():
    # Whitespace-only text passes `EvidenceItem`'s own `min_length=1` (it
    # has non-zero length) but must still be treated as empty after
    # stripping — this is exactly the defensive check `validate_and_normalize`
    # exists to apply on top of the schema-level constraint.
    result = valid_result(
        evidence=[
            EvidenceItem(claim="   ", evidence="Some evidence."),
            EvidenceItem(claim="A claim.", evidence="   "),
            EvidenceItem(claim="A real claim.", evidence="Real evidence."),
        ]
    )

    validated = validate_and_normalize(result, valid_question_ids=set())

    assert len(validated.evidence) == 1
    assert validated.evidence[0]["claim"] == "A real claim."


def test_evidence_capped_at_maximum_count():
    result = valid_result(
        evidence=[EvidenceItem(claim=f"claim {i}", evidence=f"evidence {i}") for i in range(MAX_EVIDENCE_ITEMS + 4)]
    )

    validated = validate_and_normalize(result, valid_question_ids=set())

    assert len(validated.evidence) == MAX_EVIDENCE_ITEMS


def test_empty_evidence_list_is_handled_safely():
    result = valid_result(evidence=[])

    validated = validate_and_normalize(result, valid_question_ids=set())

    assert validated.evidence == []
