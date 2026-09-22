"""Task 22 — structural guarantees for the result/report layer:

* ResultService never imports Qdrant, a provider SDK, Redis, or LangGraph
* the result route uses dependency injection (no manual repository
  construction inside the route)
* ResultQuestionResponse/InterviewResultResponse never expose internal
  fields such as `agent_reason`
* no new PostgreSQL schema (no new Alembic migration) was introduced
"""

import ast
import inspect
from pathlib import Path

RESULT_SERVICE_PATH = Path(inspect.getsourcefile(__import__("app.services.result_service", fromlist=["x"])))
ROUTES_PATH = Path(inspect.getsourcefile(__import__("app.api.routes.interviews", fromlist=["x"])))


def _imported_module_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module)
    return roots


def test_result_service_never_imports_qdrant_or_the_knowledge_layer():
    imports = _imported_module_roots(RESULT_SERVICE_PATH)
    assert not any(module.startswith("qdrant_client") for module in imports)
    assert not any(module.startswith("app.knowledge") for module in imports)


def test_result_service_never_imports_a_provider_sdk_directly():
    imports = _imported_module_roots(RESULT_SERVICE_PATH)
    assert not (imports & {"openai", "google", "genai"})


def test_result_service_never_imports_redis():
    imports = _imported_module_roots(RESULT_SERVICE_PATH)
    assert not any(module.startswith("redis") or module.startswith("app.redis") for module in imports)


def test_result_service_never_imports_langgraph_or_the_interview_workflow():
    imports = _imported_module_roots(RESULT_SERVICE_PATH)
    assert not any(module.startswith("langgraph") for module in imports)
    assert not any(module.startswith("app.workflows") for module in imports)


def test_result_service_does_not_call_the_llm_provider_directly():
    # ResultService reuses EvaluationService's LLM call — it never holds
    # or calls an `LLMProvider` itself.
    imports = _imported_module_roots(RESULT_SERVICE_PATH)
    assert "app.llm.base" not in imports
    assert "app.llm.factory" not in imports


def test_result_service_reuses_evaluation_service():
    imports = _imported_module_roots(RESULT_SERVICE_PATH)
    assert "app.evaluation.service" in imports


def test_result_service_has_a_single_focused_public_method():
    from app.services.result_service import ResultService

    public_methods = [
        name for name in vars(ResultService) if not name.startswith("_") and callable(getattr(ResultService, name))
    ]
    assert public_methods == ["get_result"]


def test_result_route_uses_dependency_injection():
    source = ROUTES_PATH.read_text()
    # The route function itself never constructs InterviewRepository/
    # ResultService/EvaluationService directly — only via Depends(...).
    assert "Depends(get_result_service)" in source
    result_route_start = source.index("async def get_interview_result")
    result_route_body = source[result_route_start : result_route_start + 2500]
    assert "InterviewRepository(" not in result_route_body
    assert "ResultService(" not in result_route_body


def test_result_schemas_never_expose_agent_reason_or_internal_fields():
    from app.schemas.interview import InterviewResultResponse, ResultInterviewResponse, ResultQuestionResponse

    for model in (InterviewResultResponse, ResultInterviewResponse, ResultQuestionResponse):
        field_names = set(model.model_fields.keys())
        assert "agent_reason" not in field_names
        assert "rationale" not in field_names
        assert "prompt" not in field_names


def test_no_new_alembic_migration_was_introduced_for_the_result_layer():
    migrations_dir = Path(__file__).resolve().parent.parent / "alembic" / "versions"
    revision_files = sorted(p.name for p in migrations_dir.glob("*.py"))
    assert revision_files == [
        "373850180458_add_unique_constraint_on_session_.py",
        "538fb309b1be_create_interview_topics_table.py",
        "a451a0225842_create_interview_sessions_table.py",
        "d00c8abb5098_create_interview_questions_messages_.py",
    ]
