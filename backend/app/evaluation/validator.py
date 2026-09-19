"""Backend validation for the LLM's proposed `EvaluationResult`.

Core principle (same as Task 15's decision validator): the LLM proposes,
the backend validates. This module is pure and deterministic — no LLM
calls, no database, no Redis, no Qdrant — and is the single place that
enforces:

* component scores are finite numbers in [0, 10] (or the whole result is
  rejected — see below)
* `overall_score` is always the backend's deterministic average of the
  four component scores, never the LLM's own proposal
* strengths/weaknesses are non-empty, trimmed, and bounded in count
* evidence items are non-empty and reference only real question IDs from
  this interview — an unknown or malformed question_id is normalized
  away, never persisted as an invented reference
"""

import math
from uuid import UUID

from app.evaluation.models import EvaluationResult, EvidenceItem, ValidatedEvaluation
from app.llm.exceptions import LLMInvalidResponseError

MAX_STRENGTHS = 10
MAX_WEAKNESSES = 10
MAX_EVIDENCE_ITEMS = 10
MAX_STRING_LENGTH = 500

_SCORE_FIELDS = (
    "technical_knowledge_score",
    "reasoning_score",
    "depth_score",
    "communication_score",
)


def _validated_score(field_name: str, value: float) -> float:
    # A non-finite or out-of-range component score means the structured
    # response can't be trusted at all — unlike strengths/weaknesses/
    # evidence below, there is no safe way to "drop" a bad score and keep
    # going, so this raises the existing `LLMInvalidResponseError` (Task
    # 18/20 already map it to a stable API error) rather than persisting
    # a misleading number.
    if not math.isfinite(value):
        raise LLMInvalidResponseError(f"Evaluation field '{field_name}' is not a finite number.")
    if not (0.0 <= value <= 10.0):
        raise LLMInvalidResponseError(f"Evaluation field '{field_name}' is out of the 0-10 range.")
    return round(float(value), 2)


def _clean_strings(values: list[str], max_items: int) -> list[str]:
    cleaned: list[str] = []
    for value in values:
        text = (value or "").strip()
        if not text:
            continue
        cleaned.append(text[:MAX_STRING_LENGTH])
        if len(cleaned) >= max_items:
            break
    return cleaned


def _normalize_question_id(raw: str | None, valid_question_ids: set[UUID]) -> str | None:
    if not raw:
        return None
    try:
        parsed = UUID(raw)
    except (ValueError, AttributeError, TypeError):
        return None
    if parsed not in valid_question_ids:
        return None
    return str(parsed)


def _clean_evidence(items: list[EvidenceItem], valid_question_ids: set[UUID], max_items: int) -> list[dict]:
    cleaned: list[dict] = []
    for item in items:
        if len(cleaned) >= max_items:
            break
        claim = (item.claim or "").strip()
        evidence_text = (item.evidence or "").strip()
        if not claim or not evidence_text:
            continue
        entry: dict = {"claim": claim[:MAX_STRING_LENGTH], "evidence": evidence_text[:MAX_STRING_LENGTH]}
        question_id = _normalize_question_id(item.question_id, valid_question_ids)
        if question_id is not None:
            entry["question_id"] = question_id
        if item.topic is not None:
            entry["topic"] = item.topic.value
        cleaned.append(entry)
    return cleaned


def validate_and_normalize(result: EvaluationResult, valid_question_ids: set[UUID]) -> ValidatedEvaluation:
    """Turn an LLM-proposed `EvaluationResult` into a `ValidatedEvaluation`
    safe to persist. Raises `LLMInvalidResponseError` only for the
    component scores; everything else degrades gracefully (bad items are
    dropped, never a reason to fail the whole evaluation)."""
    scores = {field: _validated_score(field, getattr(result, field)) for field in _SCORE_FIELDS}
    overall_score = round(sum(scores.values()) / len(scores), 2)

    return ValidatedEvaluation(
        **scores,
        overall_score=overall_score,
        strengths=_clean_strings(result.strengths, MAX_STRENGTHS),
        weaknesses=_clean_strings(result.weaknesses, MAX_WEAKNESSES),
        evidence=_clean_evidence(result.evidence, valid_question_ids, MAX_EVIDENCE_ITEMS),
    )
