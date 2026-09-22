from fastapi import APIRouter, Depends, Response

from app.api.deps import enforce_voice_stt_token_rate_limit, enforce_voice_tts_rate_limit, get_stt_auth_service, get_tts_service
from app.schemas.common import DataResponse
from app.schemas.voice import SttTokenResponse, TTSSynthesizeRequest
from app.voice.service import SttAuthService, TTSService

router = APIRouter()


@router.post("/tts")
async def synthesize_speech(
    body: TTSSynthesizeRequest,
    service: TTSService = Depends(get_tts_service),
    _rate_limit: None = Depends(enforce_voice_tts_rate_limit),
) -> Response:
    result = await service.synthesize(body.text)
    return Response(content=result.audio, media_type=result.content_type)


@router.post("/stt/token")
async def grant_stt_token(
    service: SttAuthService = Depends(get_stt_auth_service),
    _rate_limit: None = Depends(enforce_voice_stt_token_rate_limit),
) -> DataResponse[SttTokenResponse]:
    token = await service.grant_token()
    return DataResponse(data=SttTokenResponse(access_token=token.access_token, expires_in=token.expires_in))
