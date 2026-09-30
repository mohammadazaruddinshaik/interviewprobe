from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_dashboard_service
from app.models.user import User
from app.schemas.common import DataResponse
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard_service import DashboardService

router = APIRouter()


@router.get(
    "",
    response_model=DataResponse[DashboardResponse],
    responses={401: {"description": "Not authenticated (missing, expired or revoked session)."}},
)
def get_dashboard(
    _user: User = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service),
) -> DataResponse[DashboardResponse]:
    # No parameters of any kind: the authenticated session is the only scope.
    return DataResponse(data=service.get_dashboard())
