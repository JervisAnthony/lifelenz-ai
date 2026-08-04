"""Strict public response schemas for API system endpoints and errors."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


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
