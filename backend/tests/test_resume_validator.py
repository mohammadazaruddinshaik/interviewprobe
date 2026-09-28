"""Unit tests for app/resume/validator.py — pure normalization over an
already schema-valid `ResumeProfile`. No database, no LLM.
"""

from app.resume.models import (
    ResumeCandidateInfo,
    ResumeClaim,
    ResumeEducationEntry,
    ResumeProfile,
    ResumeProjectEntry,
)
from app.resume.validator import MAX_LIST_ITEMS, MAX_SKILLS, validate_and_normalize_profile


def test_trims_whitespace_from_every_string_field():
    profile = ResumeProfile(
        candidate=ResumeCandidateInfo(name="  Jane Doe  ", email=" jane@example.com "),
        summary="  Backend engineer.  ",
    )

    result = validate_and_normalize_profile(profile)

    assert result.candidate.name == "Jane Doe"
    assert result.candidate.email == "jane@example.com"
    assert result.summary == "Backend engineer."


def test_whitespace_only_fields_become_null():
    profile = ResumeProfile(candidate=ResumeCandidateInfo(name="   ", phone=""))

    result = validate_and_normalize_profile(profile)

    assert result.candidate.name is None
    assert result.candidate.phone is None


def test_drops_empty_skills_and_bounds_the_list():
    profile = ResumeProfile(skills=["Python", "  ", "", "Go"] + [f"Skill{i}" for i in range(100)])

    result = validate_and_normalize_profile(profile)

    assert "Python" in result.skills
    assert "  " not in result.skills
    assert "" not in result.skills
    assert len(result.skills) <= MAX_SKILLS


def test_bounds_education_entries():
    profile = ResumeProfile(
        education=[ResumeEducationEntry(institution=f"University {i}") for i in range(50)]
    )

    result = validate_and_normalize_profile(profile)

    assert len(result.education) <= MAX_LIST_ITEMS


def test_truncates_overly_long_string_fields():
    profile = ResumeProfile(summary="x" * 10_000)

    result = validate_and_normalize_profile(profile)

    assert len(result.summary) < 10_000


def test_drops_claims_with_no_claim_text():
    profile = ResumeProfile(
        claims=[
            ResumeClaim(claim="  ", category="technical"),
            ResumeClaim(claim="Built a RAG pipeline using Qdrant", category="technical"),
        ]
    )

    result = validate_and_normalize_profile(profile)

    assert len(result.claims) == 1
    assert result.claims[0].claim == "Built a RAG pipeline using Qdrant"


def test_never_labels_a_claim_true_or_false():
    # Structural guarantee, not a behavioral assertion: ResumeClaim simply
    # has no such field, so a validated claim can never carry one.
    assert "verified" not in ResumeClaim.model_fields
    assert "is_true" not in ResumeClaim.model_fields


def test_project_technologies_are_cleaned_and_bounded():
    profile = ResumeProfile(
        projects=[ResumeProjectEntry(name="Interview Bot", technologies=["Python", "  ", "FastAPI"])]
    )

    result = validate_and_normalize_profile(profile)

    assert result.projects[0].technologies == ["Python", "FastAPI"]


def test_an_entirely_empty_profile_normalizes_to_an_entirely_empty_profile():
    # No resume states everything — an empty response must stay
    # honestly empty, not be filled in with anything invented.
    result = validate_and_normalize_profile(ResumeProfile())

    assert result.candidate.name is None
    assert result.summary is None
    assert result.education == []
    assert result.experience == []
    assert result.projects == []
    assert result.skills == []
    assert result.certifications == []
    assert result.achievements == []
    assert result.claims == []
