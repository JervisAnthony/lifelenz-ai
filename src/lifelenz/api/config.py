"""Explicit immutable configuration for the LifeLenz HTTP API."""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

_DEFAULT_APPLICATION_NAME = "LifeLenz-AI"
try:
    _APPLICATION_VERSION = version("lifelenz-ai")
except PackageNotFoundError:  # pragma: no cover - source trees are installed for tests
    _APPLICATION_VERSION = "0.1.0"

_TRUE_VALUES = frozenset({"true", "1", "yes", "on"})
_FALSE_VALUES = frozenset({"false", "0", "no", "off"})


class ApiConfigurationError(ValueError):
    """Raised when API startup configuration is invalid or unusable."""


@dataclass(frozen=True, slots=True)
class ApiSettings:
    """Immutable settings used to construct one independent API application."""

    application_name: str
    application_version: str
    environment: str
    database_path: Path
    api_prefix: str = "/api/v1"
    docs_enabled: bool = True

    def __post_init__(self) -> None:
        _require_nonblank_text(self.application_name, "application_name")
        _require_nonblank_text(self.application_version, "application_version")
        _require_nonblank_text(self.environment, "environment")
        if not isinstance(self.database_path, Path):
            raise ApiConfigurationError("database_path must be a pathlib.Path")
        if str(self.database_path) == ":memory:":
            raise ApiConfigurationError("database_path must identify a durable SQLite file")
        _validate_api_prefix(self.api_prefix)
        if type(self.docs_enabled) is not bool:
            raise ApiConfigurationError("docs_enabled must be a boolean")


def _require_nonblank_text(value: object, name: str) -> str:
    if type(value) is not str or not value.strip():
        raise ApiConfigurationError(f"{name} must be a nonblank string")
    return value


def _validate_api_prefix(value: object) -> str:
    prefix = _require_nonblank_text(value, "api_prefix")
    if not prefix.startswith("/"):
        raise ApiConfigurationError("api_prefix must begin with '/'")
    if prefix != "/" and prefix.endswith("/"):
        raise ApiConfigurationError("api_prefix must not end with '/'")
    if any(character.isspace() for character in prefix):
        raise ApiConfigurationError("api_prefix must not contain whitespace")
    return prefix


def _environment_value(environ: Mapping[str, str], name: str, default: str) -> str:
    value = environ.get(name, default)
    if type(value) is not str:
        raise ApiConfigurationError(f"{name} must be a string")
    return value


def _parse_boolean(value: str) -> bool:
    normalized = value.casefold()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    raise ApiConfigurationError("LIFELENZ_DOCS_ENABLED must be a supported boolean value")


def load_api_settings(environ: Mapping[str, str] | None = None) -> ApiSettings:
    """Load validated settings from a supplied mapping or an environment snapshot."""
    source: Mapping[str, str] = dict(os.environ) if environ is None else environ
    environment = _environment_value(source, "LIFELENZ_ENVIRONMENT", "development")
    database_value = _environment_value(
        source,
        "LIFELENZ_DATABASE_PATH",
        "./data/lifelenz.db",
    )
    if not database_value.strip():
        raise ApiConfigurationError("LIFELENZ_DATABASE_PATH must not be blank")
    api_prefix = _environment_value(source, "LIFELENZ_API_PREFIX", "/api/v1")
    docs_value = _environment_value(source, "LIFELENZ_DOCS_ENABLED", "true")
    return ApiSettings(
        application_name=_DEFAULT_APPLICATION_NAME,
        application_version=_APPLICATION_VERSION,
        environment=environment,
        database_path=Path(database_value),
        api_prefix=api_prefix,
        docs_enabled=_parse_boolean(docs_value),
    )
