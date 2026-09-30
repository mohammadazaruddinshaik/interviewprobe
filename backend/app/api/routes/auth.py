from fastapi import APIRouter, Depends, Request, Response, status

from app.api.deps import get_auth_service, get_current_user, get_google_verifier
from app.auth.google import GoogleIdentityVerifier
from app.auth.service import AuthService, IssuedSession
from app.core.config import settings
from app.models.user import User
from app.schemas.auth import AuthUserResponse, GoogleSignInRequest, UserResponse
from app.schemas.common import DataResponse

router = APIRouter()

_UNAUTHENTICATED = {401: {"description": "Not authenticated (missing, expired or revoked session)."}}


def _set_session_cookie(response: Response, issued: IssuedSession) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=issued.raw_token,
        max_age=settings.session_lifetime_seconds,
        expires=issued.expires_at,
        path="/",
        secure=settings.effective_session_cookie_secure,
        httponly=True,
        samesite=settings.session_cookie_samesite,
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        secure=settings.effective_session_cookie_secure,
        httponly=True,
        samesite=settings.session_cookie_samesite,
    )


@router.post(
    "/google",
    response_model=DataResponse[AuthUserResponse],
    responses={401: {"description": "The Google credential failed verification."}},
)
def sign_in_with_google(
    payload: GoogleSignInRequest,
    response: Response,
    verifier: GoogleIdentityVerifier = Depends(get_google_verifier),
    auth_service: AuthService = Depends(get_auth_service),
) -> DataResponse[AuthUserResponse]:
    # Plain `def`: Google verification performs a blocking HTTP fetch of
    # Google's signing certs, so FastAPI runs this in its threadpool.
    identity = verifier.verify(payload.credential)
    user, issued = auth_service.sign_in(identity)
    _set_session_cookie(response, issued)
    return DataResponse(data=AuthUserResponse(user=UserResponse.model_validate(user)))


@router.get("/me", response_model=DataResponse[AuthUserResponse], responses=_UNAUTHENTICATED)
def get_me(current_user: User = Depends(get_current_user)) -> DataResponse[AuthUserResponse]:
    return DataResponse(data=AuthUserResponse(user=UserResponse.model_validate(current_user)))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> Response:
    auth_service.logout(request.cookies.get(settings.session_cookie_name))
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_session_cookie(response)
    return response
