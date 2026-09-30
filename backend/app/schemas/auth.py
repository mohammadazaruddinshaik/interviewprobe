from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GoogleSignInRequest(BaseModel):
    credential: str = Field(min_length=1, max_length=8192)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: str
    avatar_url: str | None = None


class AuthUserResponse(BaseModel):
    user: UserResponse
