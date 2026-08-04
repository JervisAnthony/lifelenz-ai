"""Tests for request IDs and centralized safe exception translation."""

import asyncio
from collections.abc import Callable
from uuid import UUID

import httpx
import pytest
from fastapi import FastAPI, Request

from lifelenz.analytics import (
    AnalyticsValidationError,
    InsufficientBaselineDataError,
    InsufficientTrendDataError,
)
from lifelenz.api import ApiConfigurationError
from lifelenz.api.errors import _error_response, register_exception_handlers
from lifelenz.api.middleware import register_request_id_middleware, resolve_request_id
from lifelenz.application import (
    ApplicationValidationError,
    GoalNotFoundError,
    ProfileNotFoundError,
    WellnessRecordNotFoundError,
    WellnessSummaryUnavailableError,
)
from lifelenz.repositories import EntityNotFoundError, RepositoryPersistenceError


def get(app: FastAPI, path: str, *, headers: dict[str, str] | None = None) -> httpx.Response:
    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(path, headers=headers)

    return asyncio.run(send())


def error_app(exception_factory: Callable[[], Exception]) -> FastAPI:
    app = FastAPI()
    register_request_id_middleware(app)
    register_exception_handlers(app)

    async def fail() -> None:
        raise exception_factory()

    app.add_api_route("/error", fail, methods=["GET"])
    return app


@pytest.mark.parametrize(
    ("exception_factory", "status", "code"),
    [
        (lambda: ApplicationValidationError("private"), 400, "application_validation_error"),
        (lambda: ProfileNotFoundError("private"), 404, "profile_not_found"),
        (lambda: GoalNotFoundError("private"), 404, "goal_not_found"),
        (lambda: WellnessRecordNotFoundError("private"), 404, "wellness_record_not_found"),
        (
            lambda: WellnessSummaryUnavailableError("private"),
            404,
            "wellness_summary_unavailable",
        ),
        (lambda: EntityNotFoundError("private"), 404, "repository_entity_not_found"),
        (
            lambda: RepositoryPersistenceError(
                "unable to open C:\\private\\wellness.db; SELECT secret"
            ),
            503,
            "repository_persistence_error",
        ),
        (lambda: AnalyticsValidationError("private"), 500, "analytics_validation_error"),
        (lambda: InsufficientBaselineDataError("private"), 422, "insufficient_baseline_data"),
        (lambda: InsufficientTrendDataError("private"), 422, "insufficient_trend_data"),
        (lambda: ApiConfigurationError("private"), 500, "api_configuration_error"),
        (
            lambda: RuntimeError("secret traceback SELECT /private/path"),
            500,
            "internal_server_error",
        ),
    ],
)
def test_exception_mappings_are_stable_safe_json(
    exception_factory: Callable[[], Exception],
    status: int,
    code: str,
) -> None:
    response = get(error_app(exception_factory), "/error", headers={"X-Request-ID": "safe-123"})

    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/json")
    assert response.headers["X-Request-ID"] == "safe-123"
    assert response.json()["request_id"] == "safe-123"
    assert response.json()["error"]["code"] == code
    serialized = response.text.casefold()
    assert "traceback" not in serialized
    assert "select" not in serialized
    assert "private\\wellness.db" not in serialized


def test_persistence_and_internal_messages_are_exactly_generic() -> None:
    persistence = get(
        error_app(lambda: RepositoryPersistenceError("raw SQLite failure")),
        "/error",
    )
    internal = get(error_app(lambda: RuntimeError("private")), "/error")

    assert persistence.json()["error"]["message"] == (
        "The persistence service is temporarily unavailable."
    )
    assert internal.json()["error"]["message"] == "An unexpected server error occurred."


def test_request_validation_uses_neutral_error_without_request_body() -> None:
    app = FastAPI()
    register_request_id_middleware(app)
    register_exception_handlers(app)

    async def validate(value: int) -> int:
        return value

    app.add_api_route("/validate/{value}", validate, methods=["GET"])
    response = get(app, "/validate/not-an-integer", headers={"X-Request-ID": "validation-1"})

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "request_validation_error",
            "message": "Request validation failed.",
            "field": "path",
        },
        "request_id": "validation-1",
    }


@pytest.mark.parametrize(
    "value",
    [None, "", " ", "has space", "tab\tvalue", "é", "control\x7f", "x" * 129],
)
def test_invalid_request_ids_are_replaced_by_uuid4(value: str | None) -> None:
    resolved = resolve_request_id(value)
    assert UUID(resolved).version == 4
    assert resolved != value


@pytest.mark.parametrize("value", ["request-123", "!" * 128, "A_b.c:7"])
def test_valid_request_ids_are_preserved(value: str) -> None:
    assert resolve_request_id(value) == value


def test_generated_request_ids_are_request_local_and_not_in_success_body() -> None:
    app = FastAPI()
    register_request_id_middleware(app)

    async def state_value() -> dict[str, str]:
        return {"payload": "unchanged"}

    app.add_api_route("/success", state_value, methods=["GET"])
    first = get(app, "/success")
    second = get(app, "/success")

    assert UUID(first.headers["X-Request-ID"]).version == 4
    assert first.headers["X-Request-ID"] != second.headers["X-Request-ID"]
    assert first.json() == {"payload": "unchanged"}


def test_middleware_stores_accepted_identifier_in_request_state() -> None:
    app = FastAPI()
    register_request_id_middleware(app)

    async def state_value(request: Request) -> dict[str, str]:
        return {"request_id": request.state.request_id}

    app.add_api_route("/state", state_value, methods=["GET"])
    response = get(app, "/state", headers={"X-Request-ID": "state-123"})
    assert response.json() == {"request_id": "state-123"}
    assert response.headers["X-Request-ID"] == "state-123"


def test_error_helper_generates_request_id_when_middleware_state_is_absent() -> None:
    request = Request({"type": "http", "app": FastAPI(), "headers": []})
    response = _error_response(
        request,
        status_code=500,
        code="internal_server_error",
        message="An unexpected server error occurred.",
    )
    generated = response.headers["X-Request-ID"]
    assert UUID(generated).version == 4
    assert request.state.request_id == generated


def test_only_exception_not_base_exception_has_a_generic_handler() -> None:
    app = FastAPI()
    register_exception_handlers(app)
    assert Exception in app.exception_handlers
    assert BaseException not in app.exception_handlers
    assert KeyboardInterrupt not in app.exception_handlers
    assert SystemExit not in app.exception_handlers
