class ResumeServiceError(Exception):
    """Base class for resume domain errors the API layer maps to a stable
    HTTP response (see app/main.py's `_SERVICE_ERROR_STATUS_CODES`).

    Only raised for request-level problems — the file itself is not even
    a resume candidate worth attempting (wrong type, too large, empty) or
    the session isn't in a state that can accept one. Every subclass here
    is raised BEFORE any `interview_resumes` row is created, so a rejected
    request never leaves a dangling row behind.

    A failure that happens AFTER a row is created — extraction or
    structuring failing on a genuinely well-formed upload — is deliberately
    NOT one of these: see `ResumeExtractionError` and `ResumeService`,
    which persist that outcome as a normal FAILED row and return 200,
    since the request itself was valid and the candidate can just retry or
    skip (never a dead-end error page).
    """


class UnsupportedResumeFileTypeError(ResumeServiceError):
    """The upload isn't a PDF or DOCX — by extension, declared content
    type, or (most authoritatively) actual file signature. Covers a
    renamed file just as much as a genuinely wrong format: see
    `app.resume.extraction.classify_resume_file`."""


class ResumeFileTooLargeError(ResumeServiceError):
    pass


class EmptyResumeFileError(ResumeServiceError):
    pass


class ResumeExtractionError(Exception):
    """Raised by `app.resume.extraction` when a validly-typed file's
    content can't actually be read: corrupted PDF/DOCX, or a PDF with no
    extractable text (e.g. a scanned image with no text layer). Always
    caught by `ResumeService`, which persists it as a FAILED row rather
    than letting it become an unhandled 500 — never re-raised to the API
    layer directly.
    """
