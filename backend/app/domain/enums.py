from enum import StrEnum


class Role(StrEnum):
    AI_ENGINEER = "AI_ENGINEER"
    FRONTEND_DEVELOPER = "FRONTEND_DEVELOPER"
    BACKEND_DEVELOPER = "BACKEND_DEVELOPER"
    JAVA_DEVELOPER = "JAVA_DEVELOPER"
    SDE = "SDE"
    SDE_INTERN = "SDE_INTERN"
    FULL_STACK_DEVELOPER = "FULL_STACK_DEVELOPER"


class Difficulty(StrEnum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class InterviewStatus(StrEnum):
    CREATED = "CREATED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class InterviewTopic(StrEnum):
    # AI Engineer — existing, unchanged (already used throughout the
    # workflow/tests). New roles below add their own topics rather than
    # repurposing or renaming any of these.
    LLM_FUNDAMENTALS = "LLM_FUNDAMENTALS"
    RAG = "RAG"
    EMBEDDINGS_VECTOR_DB = "EMBEDDINGS_VECTOR_DB"
    AI_AGENTS = "AI_AGENTS"
    LLM_EVALUATION = "LLM_EVALUATION"
    AI_SYSTEM_DESIGN = "AI_SYSTEM_DESIGN"

    # Frontend Developer
    JAVASCRIPT = "JAVASCRIPT"
    REACT = "REACT"
    CSS = "CSS"
    WEB_PERFORMANCE = "WEB_PERFORMANCE"
    BROWSER_FUNDAMENTALS = "BROWSER_FUNDAMENTALS"

    # Backend Developer
    BACKEND_RUNTIME = "BACKEND_RUNTIME"
    REST_APIS = "REST_APIS"
    DATABASES = "DATABASES"
    CACHING = "CACHING"
    SYSTEM_DESIGN = "SYSTEM_DESIGN"

    # Java Developer
    CORE_JAVA = "CORE_JAVA"
    OOP = "OOP"
    COLLECTIONS = "COLLECTIONS"
    CONCURRENCY = "CONCURRENCY"
    JVM = "JVM"
    SPRING = "SPRING"

    # SDE / SDE Intern (also reused by Full Stack Developer's catalog entry)
    DATA_STRUCTURES_ALGORITHMS = "DATA_STRUCTURES_ALGORITHMS"


class QuestionType(StrEnum):
    INITIAL = "INITIAL"
    FOLLOW_UP = "FOLLOW_UP"
    CLARIFICATION = "CLARIFICATION"
    DEEP_DIVE = "DEEP_DIVE"
    CHALLENGE = "CHALLENGE"
    TOPIC_TRANSITION = "TOPIC_TRANSITION"


class MessageRole(StrEnum):
    INTERVIEWER = "INTERVIEWER"
    CANDIDATE = "CANDIDATE"
    SYSTEM = "SYSTEM"


class InterviewTopicStatus(StrEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class ResumeExtractionStatus(StrEnum):
    """An uploaded resume's processing state (`interview_resumes.status`).

    Upload processing runs synchronously within the upload request today,
    so a client only ever observes UPLOADED transiently before the same
    response settles on READY or FAILED — but every intermediate state is
    still persisted at each step (not just the final one), so a row never
    misrepresents an in-flight/crashed attempt as one that never started,
    and an async worker can pick these up unchanged later without a status
    model migration.
    """

    UPLOADED = "UPLOADED"
    EXTRACTING = "EXTRACTING"
    PARSING = "PARSING"
    READY = "READY"
    FAILED = "FAILED"


class CompetencyRequirement(StrEnum):
    """Whether a role competency (app/domain/competencies.py) is core
    coverage for the role or may be skipped by a plan when time is short."""

    REQUIRED = "REQUIRED"
    OPTIONAL = "OPTIONAL"


class PlannedTopicPriority(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ClaimInvestigationStatus(StrEnum):
    """Evidence-based assessment of a resume claim from interview evidence.

    These are internal evidence-collection statuses, never exposed to the
    candidate. They describe what evidence exists, not whether a claim is
    true or false — deliberately, there is no FALSE or LIAR value."""

    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    LIMITED_EVIDENCE = "LIMITED_EVIDENCE"
    NOT_YET_ESTABLISHED = "NOT_YET_ESTABLISHED"


class ResumeRelevance(StrEnum):
    """How strongly a planned topic is driven by candidate-reported resume
    claims. PRIMARY: the topic is planned mainly to probe specific claims.
    SUPPORTING: claims add context to a topic the role needs anyway. NONE:
    pure role coverage, no resume link."""

    NONE = "NONE"
    SUPPORTING = "SUPPORTING"
    PRIMARY = "PRIMARY"
