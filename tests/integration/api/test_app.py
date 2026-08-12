"""Integration tests for application-factory isolation and OpenAPI configuration."""

import asyncio
import sqlite3
import subprocess
import sys
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

import lifelenz.analytics
import lifelenz.api
import lifelenz.application
import lifelenz.domain
import lifelenz.repositories
from lifelenz.api import ApiConfigurationError, ApiContainer, ApiSettings, create_app

TEST_SECRET = "integration-only-secret-material-32-bytes"


def settings(path: Path, **changes: object) -> ApiSettings:
    values: dict[str, object] = {
        "application_name": "LifeLenz-AI",
        "application_version": "0.1.0",
        "environment": "test",
        "database_path": path,
        "jwt_secret": TEST_SECRET,
    }
    values.update(changes)
    return ApiSettings(**values)  # type: ignore[arg-type]


def get(app: FastAPI, path: str) -> httpx.Response:
    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(path)

    return asyncio.run(send())


def test_factory_constructs_metadata_state_parent_and_sqlite_schema(tmp_path: Path) -> None:
    database = tmp_path / "nested" / "lifelenz.db"
    configured = settings(database)
    app = create_app(configured)

    assert isinstance(app, FastAPI)
    assert app.title == "LifeLenz-AI API"
    assert app.version == "0.1.0"
    assert app.description
    assert "medical" not in app.description.casefold()
    assert app.state.settings is configured
    assert isinstance(app.state.container, ApiContainer)
    assert database.is_file()
    connection = sqlite3.connect(database)
    try:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
    finally:
        connection.close()
    assert tables >= {"schema_metadata", "wellness_profiles", "wellness_goals", "wellness_records"}
    assert app.state.container.profile_repository.list_all() == ()
    assert app.state.container.goal_repository.list_all() == ()


def test_factory_calls_are_independent_and_reopening_same_database_succeeds(tmp_path: Path) -> None:
    shared = settings(tmp_path / "shared.db")
    first = create_app(shared)
    second = create_app(shared)
    isolated = create_app(settings(tmp_path / "isolated.db"))

    assert first is not second
    assert first.state.container is not second.state.container
    assert first.state.container.profile_repository is not second.state.container.profile_repository
    assert isolated.state.settings.database_path != shared.database_path
    assert len(first.openapi()["paths"]) == 12
    assert len(second.openapi()["paths"]) == 12


def test_importing_api_modules_has_no_filesystem_or_application_side_effect(tmp_path: Path) -> None:
    script = (
        "import lifelenz.api; import lifelenz.api.app as module; assert not hasattr(module, 'app')"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert tuple(tmp_path.iterdir()) == ()


def test_docs_openapi_and_operation_ids_are_configured(tmp_path: Path) -> None:
    app = create_app(settings(tmp_path / "docs.db"))
    schema = app.openapi()

    assert get(app, "/docs").status_code == 200
    assert get(app, "/redoc").status_code == 200
    assert get(app, "/openapi.json").status_code == 200
    assert schema["info"]["title"] == "LifeLenz-AI API"
    assert schema["info"]["version"] == "0.1.0"
    assert schema["info"]["description"]
    assert set(schema["paths"]) == {
        "/",
        "/health",
        "/ready",
        "/api/v1",
        "/api/v1/health",
        "/api/v1/ready",
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/me",
        "/api/v1/profile",
        "/api/v1/records",
        "/api/v1/records/{record_id}",
    }
    operation_ids = [
        operation["operationId"] for path in schema["paths"].values() for operation in path.values()
    ]
    assert len(operation_ids) == len(set(operation_ids))
    serialized = str(schema).casefold()
    assert "bearerauth" in serialized
    assert str(tmp_path).casefold() not in serialized
    assert not any(
        word in serialized for word in ("sqliteprofilerepository", "password_hash", "oauth2")
    )


def test_docs_can_be_disabled_completely(tmp_path: Path) -> None:
    app = create_app(settings(tmp_path / "no-docs.db", docs_enabled=False))
    assert app.docs_url is None
    assert app.redoc_url is None
    assert app.openapi_url is None
    assert get(app, "/docs").status_code == 404
    assert get(app, "/redoc").status_code == 404
    assert get(app, "/openapi.json").status_code == 404


def test_custom_prefix_replaces_default_versioned_paths(tmp_path: Path) -> None:
    app = create_app(settings(tmp_path / "custom.db", api_prefix="/service/v1"))
    assert get(app, "/service/v1").status_code == 200
    assert get(app, "/service/v1/health").status_code == 200
    assert get(app, "/service/v1/ready").status_code == 200
    assert get(app, "/api/v1").status_code == 404


def test_root_prefix_is_accepted_without_factory_failure(tmp_path: Path) -> None:
    app = create_app(settings(tmp_path / "root-prefix.db", api_prefix="/"))
    assert get(app, "/").status_code == 200
    assert get(app, "/health").status_code == 200
    assert get(app, "/ready").status_code == 200


def test_invalid_factory_settings_and_directory_target_fail_clearly(tmp_path: Path) -> None:
    with pytest.raises(ApiConfigurationError):
        create_app(None if False else object())  # type: ignore[arg-type]
    with pytest.raises(ApiConfigurationError):
        create_app(settings(tmp_path))


def test_database_parent_creation_failure_is_configuration_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise OSError("private path failure")

    monkeypatch.setattr(Path, "mkdir", fail)
    with pytest.raises(ApiConfigurationError, match="parent directory") as captured:
        create_app(settings(tmp_path / "missing" / "api.db"))
    assert isinstance(captured.value.__cause__, OSError)


def test_public_api_and_existing_exports_are_exact() -> None:
    assert lifelenz.api.__all__ == [
        "ApiConfigurationError",
        "ApiContainer",
        "ApiSettings",
        "create_app",
        "load_api_settings",
    ]
    assert len(lifelenz.domain.__all__) == 48
    assert len(lifelenz.repositories.__all__) == 19
    assert len(lifelenz.analytics.__all__) == 11
    assert len(lifelenz.application.__all__) == 23
    assert not hasattr(lifelenz.api, "ApiErrorResponse")
    assert not hasattr(lifelenz.api, "create_v1_router")
    assert not hasattr(lifelenz.api, "register_exception_handlers")


def test_core_packages_remain_framework_independent() -> None:
    root = Path(__file__).parents[3] / "src" / "lifelenz"
    for package in ("domain", "repositories", "analytics", "application"):
        source = "\n".join(path.read_text() for path in (root / package).glob("*.py"))
        lowered = source.casefold()
        assert "lifelenz.api" not in lowered
        assert "fastapi" not in lowered
        assert "pydantic" not in lowered
    application_source = "\n".join(path.read_text() for path in (root / "application").glob("*.py"))
    assert "SQLiteProfileRepository" not in application_source
