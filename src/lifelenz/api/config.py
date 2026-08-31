"""Explicit immutable configuration for the LifeLenz HTTP API."""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

_DEFAULT_APPLICATION_NAME = "LifeLenz-AI"
try:
    _APPLICATION_VERSION = version("lifelenz-ai")
except PackageNotFoundError:  # pragma: no cover - source trees are installed for tests
    _APPLICATION_VERSION = "0.1.0"

_TRUE_VALUES = frozenset({"true", "1", "yes", "on"})
_FALSE_VALUES = frozenset({"false", "0", "no", "off"})
_PRODUCTION_ENVIRONMENT = "production"
_PRODUCTION_MINIMUM_SECRET_BYTES = 48


class ApiConfigurationError(ValueError):
    """Raised when API startup configuration is invalid or unusable."""


@dataclass(frozen=True, slots=True)
class ApiSettings:
    """Immutable settings used to construct one independent API application."""

    application_name: str
    application_version: str
    environment: str
    database_path: Path
    jwt_secret: str = field(repr=False)
    api_prefix: str = "/api/v1"
    docs_enabled: bool = True
    jwt_issuer: str = "lifelenz-api"
    jwt_audience: str = "lifelenz-clients"
    access_token_minutes: int = 30

    def __post_init__(self) -> None:
        _require_nonblank_text(self.application_name, "application_name")
        _require_nonblank_text(self.application_version, "application_version")
        environment = _require_nonblank_text(self.environment, "environment")
        if environment != environment.strip():
            raise ApiConfigurationError("environment must not contain surrounding whitespace")
        if not isinstance(self.database_path, Path):
            raise ApiConfigurationError("database_path must be a pathlib.Path")
        if str(self.database_path) == ":memory:":
            raise ApiConfigurationError("database_path must identify a durable SQLite file")
        if type(self.jwt_secret) is not str or not self.jwt_secret:
            raise ApiConfigurationError("jwt_secret must be a nonblank string")
        secret_length = len(self.jwt_secret.encode("utf-8"))
        if not 32 <= secret_length <= 4096:
            raise ApiConfigurationError("jwt_secret must contain between 32 and 4096 UTF-8 bytes")
        _validate_api_prefix(self.api_prefix)
        if type(self.docs_enabled) is not bool:
            raise ApiConfigurationError("docs_enabled must be a boolean")
        _require_nonblank_text(self.jwt_issuer, "jwt_issuer")
        _require_nonblank_text(self.jwt_audience, "jwt_audience")
        if type(self.access_token_minutes) is not int or not 5 <= self.access_token_minutes <= 1440:
            raise ApiConfigurationError(
                "access_token_minutes must be an integer from 5 through 1440"
            )
        if environment.casefold() == _PRODUCTION_ENVIRONMENT:
            _validate_production_settings(
                database_path=self.database_path,
                docs_enabled=self.docs_enabled,
                secret_length=secret_length,
            )


def _validate_production_settings(
    *, database_path: Path, docs_enabled: bool, secret_length: int
) -> None:
    if docs_enabled:
        raise ApiConfigurationError("production requires docs_enabled=false")
    if not database_path.is_absolute():
        raise ApiConfigurationError("production requires an absolute database_path")
    if secret_length < _PRODUCTION_MINIMUM_SECRET_BYTES:
        raise ApiConfigurationError("production jwt_secret must contain at least 48 UTF-8 bytes")


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


def _environment_value(environ: Mapping[str, str], name: str, default: str | None = None) -> str:
    value = environ.get(name, default)
    if type(value) is not str:
        raise ApiConfigurationError(f"{name} must be configured as a string")
    return value


def _parse_boolean(value: str) -> bool:
    normalized = value.casefold()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    raise ApiConfigurationError("LIFELENZ_DOCS_ENABLED must be a supported boolean value")


def _parse_access_token_minutes(value: str) -> int:
    try:
        if not value or value.strip() != value:
            raise ValueError
        return int(value)
    except ValueError as error:
        raise ApiConfigurationError("LIFELENZ_ACCESS_TOKEN_MINUTES must be an integer") from error


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
    jwt_secret = _environment_value(source, "LIFELENZ_JWT_SECRET")
    return ApiSettings(
        application_name=_DEFAULT_APPLICATION_NAME,
        application_version=_APPLICATION_VERSION,
        environment=environment,
        database_path=Path(database_value),
        jwt_secret=jwt_secret,
        api_prefix=api_prefix,
        docs_enabled=_parse_boolean(docs_value),
        jwt_issuer=_environment_value(source, "LIFELENZ_JWT_ISSUER", "lifelenz-api"),
        jwt_audience=_environment_value(source, "LIFELENZ_JWT_AUDIENCE", "lifelenz-clients"),
        access_token_minutes=_parse_access_token_minutes(
            _environment_value(source, "LIFELENZ_ACCESS_TOKEN_MINUTES", "30")
        ),
    )
