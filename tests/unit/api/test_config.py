"""Tests for explicit immutable API configuration."""

import os
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from lifelenz.analytics import AnalyticsError
from lifelenz.api import ApiConfigurationError, ApiSettings, load_api_settings
from lifelenz.application import ApplicationError
from lifelenz.repositories import RepositoryError

TEST_SECRET = "unit-only-secret-material-at-least-32-bytes"


def test_default_settings_are_deterministic_and_side_effect_free(tmp_path: Path) -> None:
    original = dict(os.environ)
    settings = load_api_settings({"LIFELENZ_JWT_SECRET": TEST_SECRET})

    assert settings == ApiSettings(
        "LifeLenz-AI",
        "0.1.0",
        "development",
        Path("data/lifelenz.db"),
        TEST_SECRET,
    )
    assert settings.api_prefix == "/api/v1"
    assert settings.docs_enabled is True
    assert not (tmp_path / "data").exists()
    assert dict(os.environ) == original


def test_explicit_mapping_is_used_without_mutation() -> None:
    environ = {
        "LIFELENZ_ENVIRONMENT": "staging",
        "LIFELENZ_DATABASE_PATH": "var/local.sqlite3",
        "LIFELENZ_API_PREFIX": "/service/v1",
        "LIFELENZ_DOCS_ENABLED": "No",
        "LIFELENZ_JWT_SECRET": TEST_SECRET,
    }
    before = dict(environ)

    settings = load_api_settings(environ)

    assert settings.environment == "staging"
    assert settings.database_path == Path("var/local.sqlite3")
    assert settings.api_prefix == "/service/v1"
    assert settings.docs_enabled is False
    assert environ == before


def test_process_environment_is_read_only_when_mapping_is_omitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIFELENZ_ENVIRONMENT", "process-test")
    monkeypatch.setenv("LIFELENZ_JWT_SECRET", TEST_SECRET)
    assert load_api_settings().environment == "process-test"
    assert load_api_settings({"LIFELENZ_JWT_SECRET": TEST_SECRET}).environment == "development"


@pytest.mark.parametrize("value", ["true", "TRUE", "1", "yes", "YES", "on", "On"])
def test_supported_true_values(value: str) -> None:
    assert (
        load_api_settings(
            {"LIFELENZ_DOCS_ENABLED": value, "LIFELENZ_JWT_SECRET": TEST_SECRET}
        ).docs_enabled
        is True
    )


@pytest.mark.parametrize("value", ["false", "FALSE", "0", "no", "NO", "off", "Off"])
def test_supported_false_values(value: str) -> None:
    assert (
        load_api_settings(
            {"LIFELENZ_DOCS_ENABLED": value, "LIFELENZ_JWT_SECRET": TEST_SECRET}
        ).docs_enabled
        is False
    )


@pytest.mark.parametrize(
    "environ",
    [
        {"LIFELENZ_ENVIRONMENT": ""},
        {"LIFELENZ_ENVIRONMENT": "   "},
        {"LIFELENZ_DATABASE_PATH": ""},
        {"LIFELENZ_DATABASE_PATH": "  "},
        {"LIFELENZ_DATABASE_PATH": ":memory:"},
        {"LIFELENZ_API_PREFIX": "api/v1"},
        {"LIFELENZ_API_PREFIX": "/api/v1/"},
        {"LIFELENZ_API_PREFIX": "/api v1"},
        {"LIFELENZ_DOCS_ENABLED": "sometimes"},
        {"LIFELENZ_DOCS_ENABLED": " true "},
        {"LIFELENZ_ENVIRONMENT": 123},
    ],
)
def test_invalid_environment_configuration_is_rejected(environ: object) -> None:
    if isinstance(environ, dict):
        environ = {"LIFELENZ_JWT_SECRET": TEST_SECRET, **environ}
    with pytest.raises(ApiConfigurationError):
        load_api_settings(environ)  # type: ignore[arg-type]


def test_jwt_secret_is_required_and_hidden_from_repr() -> None:
    with pytest.raises(ApiConfigurationError):
        load_api_settings({})
    settings = load_api_settings({"LIFELENZ_JWT_SECRET": TEST_SECRET})
    assert TEST_SECRET not in repr(settings)


@pytest.mark.parametrize(
    "changes",
    [
        {"application_name": ""},
        {"application_version": " "},
        {"environment": ""},
        {"database_path": ":memory:"},
        {"database_path": Path(":memory:")},
        {"api_prefix": "/bad\tprefix"},
        {"docs_enabled": 1},
    ],
)
def test_direct_settings_validation(changes: dict[str, object]) -> None:
    values: dict[str, object] = {
        "application_name": "LifeLenz-AI",
        "application_version": "0.1.0",
        "environment": "test",
        "database_path": Path("local.db"),
        "jwt_secret": TEST_SECRET,
    }
    values.update(changes)
    with pytest.raises(ApiConfigurationError):
        ApiSettings(**values)  # type: ignore[arg-type]


def test_settings_are_frozen_slotted_hashable_and_equal(tmp_path: Path) -> None:
    first = ApiSettings("LifeLenz-AI", "0.1.0", "test", tmp_path / "api.db", TEST_SECRET)
    second = ApiSettings("LifeLenz-AI", "0.1.0", "test", tmp_path / "api.db", TEST_SECRET)

    assert first == second
    assert hash(first) == hash(second)
    assert not hasattr(first, "__dict__")
    with pytest.raises(FrozenInstanceError):
        first.environment = "changed"  # type: ignore[misc]


def test_configuration_error_is_api_local_value_error() -> None:
    assert ApiConfigurationError.__bases__ == (ValueError,)
    assert not issubclass(ApiConfigurationError, ApplicationError)
    assert not issubclass(ApiConfigurationError, RepositoryError)
    assert not issubclass(ApiConfigurationError, AnalyticsError)
