"""Backend validation for the LLM-proposed `ResumeProfile` (Step 5 of the
Phase 2 brief: "require structured output, validate the result, reject
malformed output, never treat unvalidated LLM JSON as trusted data").

Same principle as app/evaluation/validator.py: the LLM proposes, the
backend normalizes before anything is persisted. Pydantic already
guarantees the response is schema-shaped (see LLMResumeParser); this
module additionally bounds list sizes and string lengths so a technically
valid but unreasonable response (e.g. hundreds of skills, or a claim
thousands of characters long) can never be persisted as-is, and strips
whitespace-only "empty" values the schema's `str | None` typing alone
doesn't rule out.
"""

from app.resume.models import (
    ResumeCandidateInfo,
    ResumeClaim,
    ResumeEducationEntry,
    ResumeExperienceEntry,
    ResumeProfile,
    ResumeProjectEntry,
)

MAX_FIELD_LENGTH = 500
MAX_SUMMARY_LENGTH = 2_000
MAX_LIST_ITEMS = 30
MAX_SKILLS = 50
MAX_TECHNOLOGIES_PER_PROJECT = 20


def _clean_str(value: str | None, max_length: int = MAX_FIELD_LENGTH) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text[:max_length] if text else None


def _clean_str_list(values: list[str], max_items: int, max_length: int = MAX_FIELD_LENGTH) -> list[str]:
    cleaned: list[str] = []
    for value in values:
        text = (value or "").strip()
        if not text:
            continue
        cleaned.append(text[:max_length])
        if len(cleaned) >= max_items:
            break
    return cleaned


def _clean_candidate(candidate: ResumeCandidateInfo) -> ResumeCandidateInfo:
    return ResumeCandidateInfo(
        name=_clean_str(candidate.name, 200),
        email=_clean_str(candidate.email, 200),
        phone=_clean_str(candidate.phone, 50),
        location=_clean_str(candidate.location, 200),
    )


def _clean_education(entries: list[ResumeEducationEntry]) -> list[ResumeEducationEntry]:
    cleaned: list[ResumeEducationEntry] = []
    for entry in entries[:MAX_LIST_ITEMS]:
        cleaned.append(
            ResumeEducationEntry(
                institution=_clean_str(entry.institution, 200),
                degree=_clean_str(entry.degree, 200),
                field=_clean_str(entry.field, 200),
                start=_clean_str(entry.start, 50),
                end=_clean_str(entry.end, 50),
            )
        )
    return cleaned


def _clean_experience(entries: list[ResumeExperienceEntry]) -> list[ResumeExperienceEntry]:
    cleaned: list[ResumeExperienceEntry] = []
    for entry in entries[:MAX_LIST_ITEMS]:
        cleaned.append(
            ResumeExperienceEntry(
                company=_clean_str(entry.company, 200),
                title=_clean_str(entry.title, 200),
                start=_clean_str(entry.start, 50),
                end=_clean_str(entry.end, 50),
                description=_clean_str(entry.description, MAX_SUMMARY_LENGTH),
            )
        )
    return cleaned


def _clean_projects(entries: list[ResumeProjectEntry]) -> list[ResumeProjectEntry]:
    cleaned: list[ResumeProjectEntry] = []
    for entry in entries[:MAX_LIST_ITEMS]:
        cleaned.append(
            ResumeProjectEntry(
                name=_clean_str(entry.name, 200),
                description=_clean_str(entry.description, MAX_SUMMARY_LENGTH),
                technologies=_clean_str_list(entry.technologies, MAX_TECHNOLOGIES_PER_PROJECT, 100),
            )
        )
    return cleaned


def _clean_claims(entries: list[ResumeClaim]) -> list[ResumeClaim]:
    cleaned: list[ResumeClaim] = []
    for entry in entries[:MAX_LIST_ITEMS]:
        claim_text = _clean_str(entry.claim, MAX_FIELD_LENGTH)
        if not claim_text:
            # A claim with no actual claim text is not a claim — dropped
            # rather than persisted as a hollow entry.
            continue
        cleaned.append(
            ResumeClaim(
                claim=claim_text,
                category=_clean_str(entry.category, 100),
                source=_clean_str(entry.source, 200),
                evidence=_clean_str(entry.evidence, MAX_SUMMARY_LENGTH),
            )
        )
    return cleaned


def validate_and_normalize_profile(profile: ResumeProfile) -> ResumeProfile:
    """Turn an LLM-proposed `ResumeProfile` into one safe to persist:
    trimmed, bounded, and with whitespace-only values dropped to null/
    empty. Never raises — an oversized or slightly malformed-content
    response is trimmed down rather than treated as an all-or-nothing
    failure (unlike evaluation scores, no field here is load-bearing
    enough that a bad value should fail the whole upload)."""
    return ResumeProfile(
        candidate=_clean_candidate(profile.candidate),
        summary=_clean_str(profile.summary, MAX_SUMMARY_LENGTH),
        education=_clean_education(profile.education),
        experience=_clean_experience(profile.experience),
        projects=_clean_projects(profile.projects),
        skills=_clean_str_list(profile.skills, MAX_SKILLS, 100),
        certifications=_clean_str_list(profile.certifications, MAX_LIST_ITEMS, 200),
        achievements=_clean_str_list(profile.achievements, MAX_LIST_ITEMS, MAX_FIELD_LENGTH),
        claims=_clean_claims(profile.claims),
    )
