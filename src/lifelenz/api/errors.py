"""Centralized safe exception translation for the HTTP boundary."""

from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from lifelenz.analytics import (
    AnalyticsValidationError,
    InsufficientBaselineDataError,
    InsufficientTrendDataError,
)
from lifelenz.api.config import ApiConfigurationError
from lifelenz.api.middleware import REQUEST_ID_HEADER
from lifelenz.api.schemas import ApiErrorDetail, ApiErrorResponse
from lifelenz.application import (
    ApplicationValidationError,
    GoalNotFoundError,
    ProfileNotFoundError,
    WellnessRecordNotFoundError,
    WellnessSummaryUnavailableError,
)
from lifelenz.repositories import EntityNotFoundError, RepositoryPersistenceError

type _Handler = Callable[[Request, Exception], Awaitable[JSONResponse]]


def _request_id(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    if type(request_id) is not str:
        request_id = str(uuid4())
        request.state.request_id = request_id
    return request_id


def _error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    field: str | None = None,
) -> JSONResponse:
    request_id = _request_id(request)
    payload = ApiErrorResponse(
        error=ApiErrorDetail(code=code, message=message, field=field),
        request_id=request_id,
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json"),
        headers={REQUEST_ID_HEADER: request_id},
    )


def _handler(status_code: int, code: str, message: str) -> _Handler:
    async def handle(request: Request, exception: Exception) -> JSONResponse:
        return _error_response(
            request,
            status_code=status_code,
            code=code,
            message=message,
        )

    return handle


async def _request_validation_handler(
    request: Request,
    exception: Exception,
) -> JSONResponse:
    field = None
    if isinstance(exception, RequestValidationError) and exception.errors():
        location = exception.errors()[0].get("loc", ())
        safe_parts = [str(part) for part in location if part in {"path", "query", "header"}]
        field = ".".join(safe_parts) or None
    return _error_response(
        request,
        status_code=422,
        code="request_validation_error",
        message="Request validation failed.",
        field=field,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register explicit stable mappings for expected and unexpected failures."""
    mappings: tuple[tuple[type[Exception], _Handler], ...] = (
        (RequestValidationError, _request_validation_handler),
        (
            ApplicationValidationError,
            _handler(400, "application_validation_error", "The request is invalid."),
        ),
        (ProfileNotFoundError, _handler(404, "profile_not_found", "The profile was not found.")),
        (GoalNotFoundError, _handler(404, "goal_not_found", "The goal was not found.")),
        (
            WellnessRecordNotFoundError,
            _handler(404, "wellness_record_not_found", "The wellness record was not found."),
        ),
        (
            WellnessSummaryUnavailableError,
            _handler(404, "wellness_summary_unavailable", "The wellness summary is unavailable."),
        ),
        (
            EntityNotFoundError,
            _handler(404, "repository_entity_not_found", "The requested entity was not found."),
        ),
        (
            RepositoryPersistenceError,
            _handler(
                503,
                "repository_persistence_error",
                "The persistence service is temporarily unavailable.",
            ),
        ),
        (
            AnalyticsValidationError,
            _handler(500, "analytics_validation_error", "An internal analytics error occurred."),
        ),
        (
            InsufficientBaselineDataError,
            _handler(422, "insufficient_baseline_data", "Insufficient baseline data."),
        ),
        (
            InsufficientTrendDataError,
            _handler(422, "insufficient_trend_data", "Insufficient trend data."),
        ),
        (
            ApiConfigurationError,
            _handler(500, "api_configuration_error", "The API is not configured correctly."),
        ),
        (
            Exception,
            _handler(500, "internal_server_error", "An unexpected server error occurred."),
        ),
    )
    for exception_type, handler in mappings:
        app.add_exception_handler(exception_type, handler)  # type: ignore[arg-type]
