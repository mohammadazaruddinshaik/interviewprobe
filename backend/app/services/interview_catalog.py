from annotated_types import Ge, Le, MaxLen, MinLen
from pydantic.fields import FieldInfo

from app.domain.enums import Difficulty
from app.domain.roles import ROLE_CATALOG
from app.schemas.interview import (
    CatalogDifficultyResponse,
    CatalogRangeResponse,
    CatalogRoleResponse,
    CatalogTopicResponse,
    CreateInterviewRequest,
    InterviewCatalogResponse,
)


def _bounds(field: FieldInfo, lower_type: type, upper_type: type, lower_attr: str, upper_attr: str) -> CatalogRangeResponse:
    """Read a field's min/max from CreateInterviewRequest's own constraints so the
    advertised range can never drift from what creation actually validates."""
    lower = next(getattr(m, lower_attr) for m in field.metadata if isinstance(m, lower_type))
    upper = next(getattr(m, upper_attr) for m in field.metadata if isinstance(m, upper_type))
    return CatalogRangeResponse(min=lower, max=upper)


def build_interview_catalog() -> InterviewCatalogResponse:
    """Project the existing domain catalog (ROLE_CATALOG), the Difficulty enum and the
    creation-request bounds into the API response. Static configuration: no DB, no Redis."""
    fields = CreateInterviewRequest.model_fields
    return InterviewCatalogResponse(
        roles=[
            CatalogRoleResponse(
                value=definition.role,
                label=definition.display_name,
                description=definition.description,
                topics=[
                    CatalogTopicResponse(value=t.topic, label=t.display_name, description=t.description)
                    for t in definition.topics
                ],
            )
            for definition in ROLE_CATALOG.values()
        ],
        difficulties=[CatalogDifficultyResponse(value=d) for d in Difficulty],
        question_limit=_bounds(fields["question_limit"], Ge, Le, "ge", "le"),
        topic_limit=_bounds(fields["topics"], MinLen, MaxLen, "min_length", "max_length"),
    )
