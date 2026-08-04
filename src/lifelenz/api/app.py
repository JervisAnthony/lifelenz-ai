"""FastAPI application factory for the LifeLenz HTTP boundary."""

from pathlib import Path

from fastapi import FastAPI

from lifelenz.api.config import ApiConfigurationError, ApiSettings, load_api_settings
from lifelenz.api.dependencies import build_api_container
from lifelenz.api.errors import register_exception_handlers
from lifelenz.api.middleware import register_request_id_middleware
from lifelenz.api.routes import create_v1_router
from lifelenz.api.routes.system import create_system_router

_DESCRIPTION = "A versioned API foundation for structured, non-diagnostic personal wellness data."


def _prepare_database_parent(database_path: Path) -> None:
    if database_path.exists() and database_path.is_dir():
        raise ApiConfigurationError("database_path must identify a file")
    try:
        database_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise ApiConfigurationError("database parent directory could not be created") from error


def create_app(settings: ApiSettings | None = None) -> FastAPI:
    """Construct and return one independently configured FastAPI application."""
    resolved = load_api_settings() if settings is None else settings
    if type(resolved) is not ApiSettings:
        raise ApiConfigurationError("settings must be an ApiSettings instance")
    _prepare_database_parent(resolved.database_path)
    container = build_api_container(resolved)
    docs_url = "/docs" if resolved.docs_enabled else None
    redoc_url = "/redoc" if resolved.docs_enabled else None
    openapi_url = "/openapi.json" if resolved.docs_enabled else None
    app = FastAPI(
        title=f"{resolved.application_name} API",
        version=resolved.application_version,
        description=_DESCRIPTION,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
    )
    app.state.settings = resolved
    app.state.container = container
    register_request_id_middleware(app)
    register_exception_handlers(app)
    app.include_router(create_system_router(operation_prefix="root", include_metadata_slash=True))
    if resolved.api_prefix == "/":
        app.include_router(create_system_router(operation_prefix="v1", include_metadata_slash=True))
    else:
        app.include_router(create_v1_router(), prefix=resolved.api_prefix)
    return app
