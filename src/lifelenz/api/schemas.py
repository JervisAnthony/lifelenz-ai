"""Strict public response schemas for API system endpoints and errors."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr


class _StrictResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ApiMetadataResponse(_StrictResponseModel):
    """Deterministic metadata describing the running API surface."""

    name: str
    version: str
    environment: str
    api_version: str
    documentation_url: str | None


class HealthResponse(_StrictResponseModel):
    """Database-independent liveness response."""

    status: Literal["ok"]
    service: str
    version: str


class ReadinessResponse(_StrictResponseModel):
    """Successful durable-storage readiness response."""

    status: Literal["ready"]
    database: Literal["available"]
    schema_version: int


class ApiErrorDetail(_StrictResponseModel):
    """Stable public error code and safe human-readable description."""

    code: str
    message: str
    field: str | None = None


class ApiErrorResponse(_StrictResponseModel):
    """Consistent API error envelope with request correlation."""

    error: ApiErrorDetail
    request_id: str


PasswordSecret = Annotated[SecretStr, Field(min_length=12, max_length=256)]


class RegisterRequest(_StrictResponseModel):
    """Strict registration input whose password stays representation-safe."""

    email: EmailStr
    password: PasswordSecret


class LoginRequest(_StrictResponseModel):
    """Strict credential input whose password stays representation-safe."""

    email: EmailStr
    password: PasswordSecret


class UserAccountResponse(_StrictResponseModel):
    """Safe account representation without credentials or profile content."""

    user_id: UUID
    email: str
    is_active: bool


class AccessTokenResponse(_StrictResponseModel):
    """Short-lived bearer access token without refresh or claim details."""

    access_token: str
    token_type: Literal["bearer"]
    expires_in: int


class CurrentUserResponse(_StrictResponseModel):
    """Authenticated account identity and owned profile identifiers only."""

    user_id: UUID
    email: str
    is_active: bool
    profile_ids: tuple[UUID, ...]
