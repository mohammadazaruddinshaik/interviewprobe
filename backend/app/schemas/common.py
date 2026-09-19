from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class DataResponse(BaseModel, Generic[T]):
    data: T


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
