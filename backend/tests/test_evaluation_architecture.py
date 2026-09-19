"""Task 21 — structural guarantees for the evaluation engine:

* the evaluation layer never imports Qdrant or a provider SDK directly
* it depends only on the existing `LLMProvider` abstraction
* it never depends on Redis
* it never mutates interview-lifecycle fields (status, current question,
  topics, ...) — its only durable mutation is the `evaluations` row
* no new PostgreSQL schema (no new Alembic migration) was introduced
"""

import ast
import importlib
import inspect
from pathlib import Path

EVALUATION_PACKAGE_ROOT = Path(importlib.import_module("app.evaluation").__file__).parent


def _evaluation_module_files() -> list[Path]:
    return sorted(EVALUATION_PACKAGE_ROOT.rglob("*.py"))


def _imported_module_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module)
    return roots


def test_evaluation_package_never_imports_qdrant():
    for path in _evaluation_module_files():
        imports = _imported_module_roots(path)
        assert not any(module.startswith("qdrant_client") for module in imports), (
            f"{path.name} must not import the Qdrant SDK"
        )
        assert not any(module.startswith("app.knowledge") for module in imports), (
            f"{path.name} must not depend on the knowledge/RAG layer — evaluation grades a "
            "finished transcript, it does not retrieve or ground anything"
        )


def test_evaluation_package_never_imports_a_provider_sdk_directly():
    for path in _evaluation_module_files():
        imports = _imported_module_roots(path)
        forbidden_roots = {"openai", "google", "genai"}
        assert not (imports & forbidden_roots), (
            f"{path.name} must not import an LLM provider SDK directly — only through "
            "app.llm.base.LLMProvider"
        )


def test_evaluation_service_depends_on_the_llm_provider_abstraction():
    from app.evaluation import service

    imports = _imported_module_roots(EVALUATION_PACKAGE_ROOT / "service.py")
    assert "app.llm.base" in imports
    assert hasattr(service.EvaluationService, "get_or_create_evaluation")


def test_evaluation_package_never_imports_redis():
    for path in _evaluation_module_files():
        imports = _imported_module_roots(path)
        assert not any(module.startswith("redis") or module.startswith("app.redis") for module in imports), (
            f"{path.name} must not depend on Redis — evaluation has no runtime-coordination need"
        )


def test_evaluation_service_never_calls_langgraph_or_the_interview_workflow():
    # Checks actual imports (via AST), not a raw substring search — the
    # module's own docstring *describes* this invariant in prose, which
    # would otherwise false-positive here.
    imports = _imported_module_roots(EVALUATION_PACKAGE_ROOT / "service.py")
    assert not any(module.startswith("langgraph") for module in imports)
    assert not any(module.startswith("app.workflows") for module in imports)


def test_evaluation_service_never_mutates_interview_lifecycle_fields():
    # The service's only repository writes should be reads plus
    # `create_evaluation` — never `update_session` (status/current
    # question number/version) or any topic-status mutation.
    source = inspect.getsource(importlib.import_module("app.evaluation.service"))
    assert "update_session" not in source
    assert "update_topic_status" not in source
    assert "TopicProgressionService" not in source
    assert "apply_transition" not in source
    assert "apply_initial_progression" not in source


def test_evaluation_service_only_persists_the_evaluations_table():
    source = inspect.getsource(importlib.import_module("app.evaluation.service"))
    # `create_evaluation`/`get_evaluation` (repository reads/writes to the
    # `evaluations` table) — no `create_question`, `create_message`, or
    # `create_topic(s)` call.
    assert "create_question" not in source
    assert "create_message" not in source
    assert "create_topic" not in source


def test_no_new_alembic_migration_was_introduced_for_evaluation():
    # The `evaluations` table already existed before Task 21 (see
    # d00c8abb5098_create_interview_questions_messages_.py); this task
    # adds no PostgreSQL schema at all. Confirmed by the project's known,
    # unchanged migration set and head.
    migrations_dir = Path(__file__).resolve().parent.parent / "alembic" / "versions"
    revision_files = sorted(p.name for p in migrations_dir.glob("*.py"))
    assert revision_files == [
        "538fb309b1be_create_interview_topics_table.py",
        "a451a0225842_create_interview_sessions_table.py",
        "d00c8abb5098_create_interview_questions_messages_.py",
    ]


def test_evaluation_result_and_context_are_plain_pydantic_models():
    from app.evaluation.models import EvaluationContext, EvaluationResult

    for model in (EvaluationResult, EvaluationContext):
        for field_name, field_info in model.model_fields.items():
            module = getattr(field_info.annotation, "__module__", "") or ""
            assert "qdrant" not in module.lower()
            assert "openai" not in module.lower()
