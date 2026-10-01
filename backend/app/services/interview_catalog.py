from app.domain.roles import ROLE_CATALOG
from app.schemas.interview import CatalogRoleResponse, InterviewCatalogResponse


def build_interview_catalog() -> InterviewCatalogResponse:
    """Project the role catalog (ROLE_CATALOG) into the public response. Candidate-facing information is the
    role list only: difficulty, topics and the question ceiling are planner decisions, and the topic /
    competency catalog behind them stays internal to the planner. Static: no DB, no Redis."""
    return InterviewCatalogResponse(
        roles=[
            CatalogRoleResponse(
                value=definition.role,
                label=definition.display_name,
                description=definition.description,
            )
            for definition in ROLE_CATALOG.values()
        ],
    )
