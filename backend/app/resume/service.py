import logging
import uuid

from sqlalchemy.orm import Session

from app.domain.enums import InterviewStatus, ResumeExtractionStatus
from app.llm.base import LLMProvider
from app.models.interview_resume import InterviewResume
from app.repositories.interview_repository import InterviewRepository
from app.resume.exceptions import EmptyResumeFileError, ResumeExtractionError, ResumeFileTooLargeError
from app.resume.extraction import ResumeFileKind, classify_resume_file, extract_resume_text
from app.resume.parser import LLMResumeParser
from app.resume.validator import validate_and_normalize_profile
from app.services.interview_service import InterviewNotFoundError, InvalidInterviewStateError

logger = logging.getLogger(__name__)

# A candidate-safe, generic message for every processing-phase failure
# (extraction OR structuring) — never the underlying exception's own
# message, which could be a raw library error, a provider error string,
# or otherwise not meant for an end user. The real cause is still logged
# server-side (see `_fail`).
_GENERIC_PROCESSING_ERROR = "This file couldn't be read. Please try another PDF or DOCX, or skip for now."

_ACCEPTABLE_SESSION_STATUSES = (InterviewStatus.CREATED, InterviewStatus.IN_PROGRESS)


class ResumeService:
    """Owns the optional resume upload pipeline end to end: validate the
    request, persist an `interview_resumes` row, extract text, parse it
    into a structured profile, and persist the outcome.

    Split into two halves with very different failure philosophies, per
    the Phase 2 brief:

    1. Request-level validation (`_validate_request`) — wrong file type,
       oversized, empty, unknown/completed session. These are things the
       CALLER got wrong; they raise before any row is created, and the API
       layer maps them to a normal 4xx error response (see
       app/api/routes/interviews.py, app/main.py).
    2. Processing (`_run_pipeline`) — extracting text and structuring it.
       These can fail on a perfectly validly-submitted file (a corrupted
       PDF, a scanned PDF with no text, a flaky LLM call). None of that is
       the caller's fault, and the candidate must never be dead-ended by
       it (Phase 2 brief, Step 12): every failure here is persisted as a
       normal FAILED row and returned as a normal 200 response, for the
       Setup page's existing "Couldn't read this resume" UI to render —
       never an exception that reaches the API layer as a 5xx.
    """

    def __init__(self, repository: InterviewRepository, llm_provider: LLMProvider, max_file_size_bytes: int):
        self.repository = repository
        self.parser = LLMResumeParser(llm_provider)
        self.max_file_size_bytes = max_file_size_bytes

    @property
    def _db(self) -> Session:
        return self.repository.session

    async def upload_resume(
        self, session_id: uuid.UUID, filename: str, content_type: str, data: bytes
    ) -> InterviewResume:
        kind = self._validate_request(session_id, filename, content_type, data)

        resume = self._create_resume_row(session_id, filename, content_type, data)
        await self._run_pipeline(resume, kind, data)
        return resume

    # ------------------------------------------------------------------
    # Request-level validation — raises, creates nothing
    # ------------------------------------------------------------------

    def _validate_request(
        self, session_id: uuid.UUID, filename: str, content_type: str, data: bytes
    ) -> ResumeFileKind:
        session = self.repository.get_session(session_id)
        if session is None:
            raise InterviewNotFoundError(f"Interview session {session_id} was not found.")
        if session.status not in _ACCEPTABLE_SESSION_STATUSES:
            raise InvalidInterviewStateError(
                f"Interview session {session_id} can no longer accept a resume "
                f"(current status: {session.status})."
            )

        if not data:
            raise EmptyResumeFileError("The uploaded file is empty.")
        if len(data) > self.max_file_size_bytes:
            max_mb = self.max_file_size_bytes / (1024 * 1024)
            raise ResumeFileTooLargeError(f"Resumes must be {max_mb:.0f}MB or smaller.")

        # Raises UnsupportedResumeFileTypeError itself if neither format matches.
        return classify_resume_file(filename, content_type, data)

    # ------------------------------------------------------------------
    # Row creation — replaces any existing resume for this session
    # (Step 7/Step 13: at most one resume per interview; a re-upload is a
    # first-class replace, not a rejected duplicate)
    # ------------------------------------------------------------------

    def _create_resume_row(
        self, session_id: uuid.UUID, filename: str, content_type: str, data: bytes
    ) -> InterviewResume:
        try:
            existing = self.repository.get_resume(session_id)
            if existing is not None:
                self.repository.delete_resume(existing)

            resume = InterviewResume(
                session_id=session_id,
                original_filename=filename[:255],
                content_type=content_type[:255] if content_type else "application/octet-stream",
                file_size=len(data),
                extraction_status=ResumeExtractionStatus.UPLOADED,
            )
            self.repository.create_resume(resume)
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise
        return resume

    # ------------------------------------------------------------------
    # Processing — never raises; always leaves `resume` READY or FAILED
    # ------------------------------------------------------------------

    async def _run_pipeline(self, resume: InterviewResume, kind: ResumeFileKind, data: bytes) -> None:
        try:
            self._set_status(resume, ResumeExtractionStatus.EXTRACTING)
            text = extract_resume_text(kind, data)
        except ResumeExtractionError as exc:
            self._fail(resume, str(exc), exc)
            return
        except Exception as exc:  # pragma: no cover - defense in depth
            self._fail(resume, _GENERIC_PROCESSING_ERROR, exc)
            return

        try:
            self._set_status(resume, ResumeExtractionStatus.PARSING, extracted_text=text)
            raw_profile = await self.parser.parse(text)
            profile = validate_and_normalize_profile(raw_profile)
        except Exception as exc:
            # Covers every LLM failure mode (timeout, rate limit, provider
            # unavailable, invalid/malformed structured response) and any
            # unexpected parsing error alike — all mean the same thing to
            # the candidate: this attempt didn't produce a usable profile.
            # The extracted text itself is preserved (set just above)
            # rather than discarded, per Step 3's "preserve the original
            # extracted text".
            self._fail(resume, _GENERIC_PROCESSING_ERROR, exc)
            return

        try:
            self.repository.update_resume(
                resume,
                extraction_status=ResumeExtractionStatus.READY,
                structured_profile=profile.model_dump(mode="json"),
                extraction_error=None,
            )
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise

    def _set_status(self, resume: InterviewResume, status: ResumeExtractionStatus, **extra) -> None:
        try:
            self.repository.update_resume(resume, extraction_status=status, **extra)
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise

    def _fail(self, resume: InterviewResume, candidate_message: str, cause: Exception) -> None:
        logger.warning(
            "resume_processing_failed session_id=%s resume_id=%s error=%s",
            resume.session_id,
            resume.id,
            repr(cause),
        )
        try:
            self.repository.update_resume(
                resume,
                extraction_status=ResumeExtractionStatus.FAILED,
                extraction_error=candidate_message,
            )
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise
