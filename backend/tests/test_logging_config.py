"""Task 48 — production logging configuration
(app/core/logging_config.py). Verifies the actual observable behavior
(whether a logger would emit a record at a given severity, via
isEnabledFor()/getEffectiveLevel()) rather than exact printed text or
timestamps, since Python's logging machinery makes that check internally
before a record is ever formatted or handled — the same thing a real
production log line's presence/absence depends on."""

import logging

import pytest

from app.core.config import Settings
from app.core.logging_config import configure_logging, resolve_log_level


@pytest.fixture(autouse=True)
def _reset_app_logger_level():
    """`configure_logging()` mutates real, process-global logger state
    (the "app" logger and the root logger) — reset the "app" logger's
    level after every test so one test's configured level can never leak
    into another's."""
    yield
    logging.getLogger("app").setLevel(logging.NOTSET)


# ---------------------------------------------------------------------------
# resolve_log_level — deterministic string -> stdlib level mapping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value,expected",
    [
        ("DEBUG", logging.DEBUG),
        ("INFO", logging.INFO),
        ("WARNING", logging.WARNING),
        ("ERROR", logging.ERROR),
        ("CRITICAL", logging.CRITICAL),
        ("debug", logging.DEBUG),  # case-insensitive
        ("  info  ", logging.INFO),  # whitespace-tolerant
    ],
)
def test_resolve_log_level_maps_recognized_names(value, expected):
    assert resolve_log_level(value) == expected


@pytest.mark.parametrize("value", ["", "not-a-level", "VERBOSE", "trace", "123"])
def test_resolve_log_level_falls_back_to_info_for_anything_unrecognized(value):
    # Deterministic, not an exception — a typo'd LOG_LEVEL env var must
    # never prevent the application from starting.
    assert resolve_log_level(value) == logging.INFO


# ---------------------------------------------------------------------------
# Settings.log_level — default and environment override
# ---------------------------------------------------------------------------


def test_default_log_level_is_info():
    # Constructed directly (not the module-level `settings` singleton) so
    # this reflects the class default regardless of what this machine's
    # own backend/.env happens to set.
    assert Settings(_env_file=None).log_level == "INFO"


def test_log_level_is_overridable_via_environment(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    assert Settings(_env_file=None).log_level == "DEBUG"


# ---------------------------------------------------------------------------
# configure_logging — the actual, observable effect
# ---------------------------------------------------------------------------


def test_configuring_at_info_makes_app_loggers_emit_info(monkeypatch):
    from app.core.config import settings as live_settings

    monkeypatch.setattr(live_settings, "log_level", "INFO")
    configure_logging()

    app_logger = logging.getLogger("app.some.module")
    assert app_logger.isEnabledFor(logging.INFO) is True


def test_configuring_at_warning_suppresses_info_but_not_warning(monkeypatch):
    from app.core.config import settings as live_settings

    monkeypatch.setattr(live_settings, "log_level", "WARNING")
    configure_logging()

    app_logger = logging.getLogger("app.some.other.module")
    assert app_logger.isEnabledFor(logging.INFO) is False
    assert app_logger.isEnabledFor(logging.WARNING) is True  # higher severity still works


def test_configuring_at_error_suppresses_warning_but_not_error(monkeypatch):
    from app.core.config import settings as live_settings

    monkeypatch.setattr(live_settings, "log_level", "ERROR")
    configure_logging()

    app_logger = logging.getLogger("app.yet.another.module")
    assert app_logger.isEnabledFor(logging.WARNING) is False
    assert app_logger.isEnabledFor(logging.ERROR) is True


def test_an_invalid_configured_level_deterministically_behaves_as_info(monkeypatch):
    from app.core.config import settings as live_settings

    monkeypatch.setattr(live_settings, "log_level", "not-a-real-level")
    configure_logging()

    app_logger = logging.getLogger("app.some.module")
    assert app_logger.isEnabledFor(logging.INFO) is True
    assert app_logger.isEnabledFor(logging.DEBUG) is False


def test_third_party_loggers_stay_at_warning_even_when_app_is_at_info(monkeypatch):
    # The point of scoping to the "app" logger namespace rather than the
    # root logger: raising app.* verbosity must never also make
    # third-party library loggers (httpx, openai, qdrant_client, ...)
    # noisy in production logs.
    from app.core.config import settings as live_settings

    monkeypatch.setattr(live_settings, "log_level", "DEBUG")
    configure_logging()

    assert logging.getLogger("httpx").isEnabledFor(logging.INFO) is False
    assert logging.getLogger("httpx").isEnabledFor(logging.WARNING) is True


def test_configure_logging_does_not_affect_uvicorns_own_loggers(monkeypatch):
    # uvicorn's own loggers ("uvicorn", "uvicorn.error", "uvicorn.access")
    # configure themselves independently (uvicorn.config.LOGGING_CONFIG) —
    # this module must never touch them, so uvicorn's own logging setup
    # (and its non-propagation) is completely undisturbed.
    from app.core.config import settings as live_settings

    monkeypatch.setattr(live_settings, "log_level", "DEBUG")
    configure_logging()

    assert logging.getLogger("uvicorn").level == logging.NOTSET
    assert logging.getLogger("uvicorn.access").level == logging.NOTSET


# ---------------------------------------------------------------------------
# Application startup remains healthy
# ---------------------------------------------------------------------------


def test_app_imports_and_responds_to_health_after_logging_is_configured():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
