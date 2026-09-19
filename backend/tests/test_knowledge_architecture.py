"""Structural guarantees for the knowledge/RAG foundation (Task 19) and its
integration into question generation (Task 20):

* the knowledge layer has no FastAPI/InterviewService dependency
* the knowledge layer never mutates interview state
* the LangGraph interview workflow depends on `KnowledgeRetrievalService`
  (Task 20) but never calls the Qdrant SDK, or the concrete
  `QdrantKnowledgeStore`, directly
* `InterviewService` still never depends on the knowledge layer at all —
  that boundary lives entirely inside `InterviewWorkflow`
* raw Qdrant response objects never leak outside the store module
"""

import ast
import importlib
import inspect
from pathlib import Path

KNOWLEDGE_PACKAGE_ROOT = Path(importlib.import_module("app.knowledge").__file__).parent


def _knowledge_module_files() -> list[Path]:
    return sorted(KNOWLEDGE_PACKAGE_ROOT.rglob("*.py"))


def test_knowledge_package_does_not_import_fastapi():
    for path in _knowledge_module_files():
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module] if node.module else []
            else:
                continue
            assert not any(name and name.startswith("fastapi") for name in names), (
                f"{path.relative_to(KNOWLEDGE_PACKAGE_ROOT.parent.parent)} must not import FastAPI"
            )


def _imported_module_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module)
    return roots


def test_knowledge_package_does_not_import_interview_service():
    # Checks actual imports (via AST), not a raw substring search — several
    # of these modules' docstrings *describe* this very invariant in
    # prose, which would otherwise false-positive here.
    for path in _knowledge_module_files():
        imports = _imported_module_roots(path)
        assert not any("interview_service" in module for module in imports), (
            f"{path.name} must not depend on InterviewService — the knowledge layer answers "
            "'what knowledge exists', never 'what did this candidate do'"
        )


def test_knowledge_package_has_no_interview_session_or_sqlalchemy_dependency():
    for path in _knowledge_module_files():
        source = path.read_text()
        assert "sqlalchemy" not in source.lower(), f"{path.name} must not depend on SQLAlchemy/PostgreSQL"
        assert "interview_session" not in source.lower(), f"{path.name} must not reference interview session state"


def test_knowledge_retrieval_service_has_no_mutation_methods():
    from app.knowledge.retrieval_service import KnowledgeRetrievalService

    public_methods = [name for name in dir(KnowledgeRetrievalService) if not name.startswith("_")]

    assert public_methods == ["search"]


def _module_source_path(module) -> Path:
    return Path(inspect.getsourcefile(module))


def test_langgraph_workflow_never_imports_the_qdrant_sdk_or_concrete_store():
    # Task 20: the workflow now legitimately depends on
    # `KnowledgeRetrievalService` (and its provider-neutral models/
    # exceptions) — that is the whole point of the integration. What it
    # must never do is reach past that abstraction: no `qdrant_client`
    # import, and no import of the concrete `QdrantKnowledgeStore`.
    from app.workflows.interview import decision_validator, graph, nodes, routing

    for module in (nodes, graph, routing, decision_validator):
        imports = _imported_module_roots(_module_source_path(module))
        assert not any(name.startswith("qdrant_client") for name in imports), (
            f"{module.__name__} must not import the Qdrant SDK directly"
        )
        assert not any(name == "app.knowledge.store.qdrant" for name in imports), (
            f"{module.__name__} must depend on KnowledgeRetrievalService, not the concrete QdrantKnowledgeStore"
        )


def test_langgraph_workflow_depends_on_the_retrieval_service_abstraction():
    # The positive counterpart to the test above — confirms the intended
    # dependency actually exists, so a future refactor that accidentally
    # removes retrieval entirely wouldn't silently pass either check.
    from app.workflows.interview import nodes

    imports = _imported_module_roots(_module_source_path(nodes))
    assert "app.knowledge.retrieval_service" in imports


def test_interview_service_never_imports_knowledge_layer():
    # Task 20: InterviewService still only ever knows about
    # `InterviewWorkflow` — the knowledge-retrieval boundary lives
    # entirely inside the workflow, never in the service layer.
    from app.services import interview_service

    source = inspect.getsource(interview_service)

    assert "app.knowledge" not in source, "InterviewService must not depend on the knowledge layer directly"


def test_qdrant_sdk_is_only_imported_inside_the_store_module():
    for path in _knowledge_module_files():
        if path.name == "qdrant.py":
            continue
        imports = _imported_module_roots(path)
        assert not any(module.startswith("qdrant_client") for module in imports), (
            f"{path.name} must not import the Qdrant SDK directly — only app/knowledge/store/qdrant.py may"
        )


def test_knowledge_search_result_fields_are_plain_types_not_sdk_objects():
    from app.knowledge.models import KnowledgeSearchResult

    for field_name, field_info in KnowledgeSearchResult.model_fields.items():
        annotation = field_info.annotation
        module = getattr(annotation, "__module__", "")
        assert "qdrant" not in module.lower(), f"KnowledgeSearchResult.{field_name} leaks a Qdrant SDK type"
