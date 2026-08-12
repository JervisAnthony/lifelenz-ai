"""Tests for strict system and error response schemas."""

import pytest
from pydantic import ValidationError

import lifelenz.api.schemas as schemas
from lifelenz.api.schemas import (
    ApiErrorDetail,
    ApiErrorResponse,
    ApiMetadataResponse,
    HealthResponse,
    ReadinessResponse,
)


def test_metadata_schema_serializes_exact_public_shape() -> None:
    response = ApiMetadataResponse(
        name="LifeLenz-AI",
        version="0.1.0",
        environment="test",
        api_version="v1",
        documentation_url="/docs",
    )
    without_docs = response.model_copy(update={"documentation_url": None})

    assert response.model_dump() == {
        "name": "LifeLenz-AI",
        "version": "0.1.0",
        "environment": "test",
        "api_version": "v1",
        "documentation_url": "/docs",
    }
    assert without_docs.documentation_url is None


def test_health_and_readiness_literals_are_strict() -> None:
    assert HealthResponse(status="ok", service="LifeLenz-AI", version="0.1.0").model_dump() == {
        "status": "ok",
        "service": "LifeLenz-AI",
        "version": "0.1.0",
    }
    assert ReadinessResponse(
        status="ready", database="available", schema_version=2
    ).model_dump() == {"status": "ready", "database": "available", "schema_version": 2}
    with pytest.raises(ValidationError):
        HealthResponse(status="ready", service="service", version="1")  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        ReadinessResponse(status="ready", database="down", schema_version=2)  # type: ignore[arg-type]


def test_error_schemas_require_request_id_and_preserve_optional_field() -> None:
    detail = ApiErrorDetail(code="invalid", message="Invalid request.")
    with_field = ApiErrorDetail(code="invalid", message="Invalid request.", field="query.limit")
    response = ApiErrorResponse(error=detail, request_id="request-123")

    assert detail.field is None
    assert with_field.field == "query.limit"
    assert response.model_dump(mode="json") == {
        "error": {"code": "invalid", "message": "Invalid request.", "field": None},
        "request_id": "request-123",
    }
    with pytest.raises(ValidationError):
        ApiErrorResponse(error=detail)  # type: ignore[call-arg]


@pytest.mark.parametrize(
    ("model", "values"),
    [
        (
            ApiMetadataResponse,
            {
                "name": "name",
                "version": "1",
                "environment": "test",
                "api_version": "v1",
                "documentation_url": None,
                "timestamp": "now",
            },
        ),
        (HealthResponse, {"status": "ok", "service": "name", "version": "1", "path": "db"}),
        (
            ReadinessResponse,
            {"status": "ready", "database": "available", "schema_version": 2, "sql": "SELECT"},
        ),
        (
            ApiErrorDetail,
            {"code": "error", "message": "message", "traceback": "secret"},
        ),
    ],
)
def test_schemas_reject_unexpected_fields(model: object, values: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        model(**values)  # type: ignore[operator]


def test_no_premature_resource_schema_exists() -> None:
    names = set(vars(schemas))
    assert not {"ProfileResponse", "GoalResponse", "RecordResponse", "SummaryResponse"} & names
