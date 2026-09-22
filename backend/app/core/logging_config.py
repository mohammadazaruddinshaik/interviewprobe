import logging

from app.core.config import settings

# Task 48: the one place application logging is configured. Root cause of
# the Task 44 audit finding this closes — nothing in the codebase ever
# called logging.basicConfig()/dictConfig(), and uvicorn's own logging
# setup (uvicorn.config.LOGGING_CONFIG) only configures its own three
# loggers ("uvicorn", "uvicorn.error", "uvicorn.access") with their own
# handlers; it never touches the root logger. Every `app.*` logger in this
# codebase (app.llm.base, app.workflows.interview.nodes, app.voice.base,
# app.knowledge.retrieval_service, app.api.deps, app.api.routes.interviews,
# app.evaluation.service) has no handler and no level of its own, so it
# fell back to the root logger's default (WARNING, no handler) — INFO
# records were silently dropped before ever reaching stdout/stderr.

_VALID_LEVEL_NAMES = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

# A plain, single-line, timestamp | level | logger | message format —
# enough to diagnose a production issue from Render's stdout/stderr
# capture without building a structured/JSON logging pipeline nothing else
# in this codebase uses.
_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
_LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def resolve_log_level(value: str) -> int:
    """Normalizes an arbitrary LOG_LEVEL string to a stdlib logging level
    constant. Deterministically falls back to INFO for anything
    unrecognized (wrong case is fine — it's upper-cased first) rather than
    raising, so a typo'd env var can never prevent the application from
    starting."""
    normalized = value.strip().upper()
    if normalized not in _VALID_LEVEL_NAMES:
        return logging.INFO
    return getattr(logging, normalized)


def configure_logging() -> None:
    """Called once, at import time, from app.main — before the ASGI app
    object uvicorn loads starts serving requests.

    Two deliberately separate levels:
      - The root logger (and therefore every third-party library logger
        that doesn't set its own level — httpx, openai, qdrant_client,
        redis, the Azure SDK, etc.) stays at WARNING, so this doesn't
        flood production logs with chatty library-level INFO noise.
      - Only the "app" logger namespace (every app.* logger in this
        codebase is a child of it, since they're all created via
        `logging.getLogger(__name__)`) is raised to `settings.log_level`
        (INFO by default) — exactly the "useful application logs, not
        lots of new logging" scope this task asked for.

    `logging.basicConfig` is what actually attaches a StreamHandler (to
    stderr) with the format above to the root logger; without a handler
    somewhere in the propagation chain, records below WARNING are dropped
    by Python's handler-of-last-resort even once a logger's own level
    allows them through.
    """
    logging.basicConfig(level=logging.WARNING, format=_LOG_FORMAT, datefmt=_LOG_DATE_FORMAT)
    logging.getLogger("app").setLevel(resolve_log_level(settings.log_level))
