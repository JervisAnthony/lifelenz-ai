"""Deterministic metadata, liveness, and readiness route behavior."""

from typing import Annotated

from fastapi import APIRouter, Depends

from lifelenz.api.config import ApiSettings
from lifelenz.api.dependencies import check_database_readiness, get_api_settings
from lifelenz.api.schemas import (
    ApiErrorResponse,
    ApiMetadataResponse,
    HealthResponse,
    ReadinessResponse,
)

SettingsDependency = Annotated[ApiSettings, Depends(get_api_settings)]


def api_metadata(settings: SettingsDependency) -> ApiMetadataResponse:
    """Return deterministic public API metadata without infrastructure details."""
    return ApiMetadataResponse(
        name=settings.application_name,
        version=settings.application_version,
        environment=settings.environment,
        api_version="v1",
        documentation_url="/docs" if settings.docs_enabled else None,
    )


def health(settings: SettingsDependency) -> HealthResponse:
    """Report process liveness without consulting storage or application services."""
    return HealthResponse(
        status="ok",
        service=settings.application_name,
        version=settings.application_version,
    )


def readiness(settings: SettingsDependency) -> ReadinessResponse:
    """Report readiness after verifying durable SQLite schema availability."""
    return ReadinessResponse(
        status="ready",
        database="available",
        schema_version=check_database_readiness(settings),
    )


def create_system_router(*, operation_prefix: str, include_metadata_slash: bool) -> APIRouter:
    """Build a fresh system router with stable unique operation identifiers."""
    router = APIRouter(tags=["system"])
    router.add_api_route(
        "/" if include_metadata_slash else "",
        api_metadata,
        methods=["GET"],
        response_model=ApiMetadataResponse,
        operation_id=f"{operation_prefix}_metadata",
        summary="API metadata",
    )
    router.add_api_route(
        "/health",
        health,
        methods=["GET"],
        response_model=HealthResponse,
        operation_id=f"{operation_prefix}_health",
        summary="Liveness probe",
    )
    router.add_api_route(
        "/ready",
        readiness,
        methods=["GET"],
        response_model=ReadinessResponse,
        responses={503: {"model": ApiErrorResponse}},
        operation_id=f"{operation_prefix}_readiness",
        summary="Readiness probe",
    )
    return router
