"""Unit tests for app/resume/extraction.py — file classification and
deterministic PDF/DOCX text extraction. No database, no LLM, no FastAPI:
pure functions over bytes.
"""

import pytest

from app.resume.exceptions import ResumeExtractionError, UnsupportedResumeFileTypeError
from app.resume.extraction import classify_resume_file, extract_resume_text
from tests.fakes import make_test_docx_bytes, make_test_pdf_bytes, make_test_pdf_with_no_text_bytes

# ---------------------------------------------------------------------------
# classify_resume_file
# ---------------------------------------------------------------------------


def test_classifies_a_real_pdf_as_pdf():
    data = make_test_pdf_bytes()
    assert classify_resume_file("resume.pdf", "application/pdf", data) == "pdf"


def test_classifies_a_real_docx_as_docx():
    data = make_test_docx_bytes()
    assert (
        classify_resume_file(
            "resume.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            data,
        )
        == "docx"
    )


def test_classifies_by_signature_even_with_no_filename_or_content_type_hint():
    data = make_test_pdf_bytes()
    assert classify_resume_file("", "", data) == "pdf"


def test_rejects_a_renamed_file_whose_signature_does_not_match_its_extension():
    # A plain text file renamed to resume.pdf — this is exactly the "do
    # not accept arbitrary files just because they have a renamed
    # extension" requirement.
    data = b"This is just plain text, not a real PDF."
    with pytest.raises(UnsupportedResumeFileTypeError):
        classify_resume_file("resume.pdf", "application/pdf", data)


def test_rejects_a_zip_that_is_not_actually_a_docx_package():
    # Real ZIP magic bytes, but no word/document.xml inside — e.g. a
    # renamed plain .zip or .xlsx pretending to be a .docx.
    data = b"PK\x03\x04" + b"\x00" * 200
    with pytest.raises(UnsupportedResumeFileTypeError):
        classify_resume_file("resume.docx", "application/vnd.openxmlformats", data)


def test_rejects_an_unsupported_file_type_entirely():
    with pytest.raises(UnsupportedResumeFileTypeError):
        classify_resume_file("resume.exe", "application/octet-stream", b"MZ\x90\x00" + b"\x00" * 100)


def test_rejects_empty_bytes():
    with pytest.raises(UnsupportedResumeFileTypeError):
        classify_resume_file("resume.pdf", "application/pdf", b"")


# ---------------------------------------------------------------------------
# extract_resume_text — PDF
# ---------------------------------------------------------------------------


def test_extracts_real_text_from_a_pdf():
    data = make_test_pdf_bytes("Experienced backend engineer")
    text = extract_resume_text("pdf", data)
    assert "Experienced backend engineer" in text


def test_pdf_extraction_normalizes_excess_blank_lines():
    data = make_test_pdf_bytes("Line one\n\n\n\n\nLine two")
    # The hand-built test PDF only ever produces a single Tj line, so this
    # asserts on the normalizer directly via a realistic multi-line input.
    from app.resume.extraction import _normalize_whitespace

    normalized = _normalize_whitespace("Line one\n\n\n\n\nLine two")
    assert normalized == "Line one\n\nLine two"


def test_corrupted_pdf_raises_extraction_error():
    with pytest.raises(ResumeExtractionError):
        extract_resume_text("pdf", b"%PDF-1.4\nnot really a valid pdf body")


def test_pdf_with_no_extractable_text_raises_extraction_error():
    # The scanned-PDF case: structurally valid, but no text layer.
    data = make_test_pdf_with_no_text_bytes()
    with pytest.raises(ResumeExtractionError, match="No readable text"):
        extract_resume_text("pdf", data)


# ---------------------------------------------------------------------------
# extract_resume_text — DOCX
# ---------------------------------------------------------------------------


def test_extracts_real_text_from_a_docx():
    data = make_test_docx_bytes("Led a team of five engineers")
    text = extract_resume_text("docx", data)
    assert "Led a team of five engineers" in text


def test_corrupted_docx_raises_extraction_error():
    with pytest.raises(ResumeExtractionError):
        extract_resume_text("docx", b"PK\x03\x04" + b"\x00" * 50)
