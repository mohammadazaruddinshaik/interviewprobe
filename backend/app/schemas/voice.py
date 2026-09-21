from typing import Literal

from pydantic import BaseModel, Field

from app.voice.models import MAX_TTS_TEXT_LENGTH


class TTSSynthesizeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TTS_TEXT_LENGTH)
    # "default" is the only accepted value for now — Task 40 deliberately
    # does not expose voice selection to the client. The backend maps it to
    # `settings.azure_speech_voice` internally; no Azure voice ID is ever
    # accepted from or echoed to the client.
    voice: Literal["default"] = "default"


class SttTokenResponse(BaseModel):
    """The public response shape for POST /voice/stt/token — deliberately
    just the two fields the browser needs to open its own streaming
    connection. No provider name, model, or other configuration detail is
    included; the client cannot select a model/provider through this
    response, and never sees the permanent Deepgram key."""

    access_token: str
    expires_in: int
