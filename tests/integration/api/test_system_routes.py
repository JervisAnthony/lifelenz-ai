"""Integration tests for deterministic system routes and readiness failures."""

import asyncio
import sqlite3
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from fastapi import FastAPI

from lifelenz.api import ApiSettings, create_app


def settings(path: Path, **changes: object) -> ApiSettings:
    values: dict[str, object] = {
        "application_name": "LifeLenz-AI",
        "application_version": "0.1.0",
        "environment": "integration",
        "database_path": path,
    }
    values.update(changes)
    return ApiSettings(**values)  # type: ignore[arg-type]


def get(
    app: FastAPI,
    path: str,
    *,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(path, headers=headers)

    return asyncio.run(send())


@pytest.mark.parametrize("path", ["/", "/api/v1"])
def test_metadata_routes_are_deterministic_and_private(path: str, tmp_path: Path) -> None:
    app = create_app(settings(tmp_path / "metadata.db"))
    response = get(app, path, headers={"X-Request-ID": "metadata-request"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "metadata-request"
    assert response.json() == {
        "name": "LifeLenz-AI",
        "version": "0.1.0",
        "environment": "integration",
        "api_version": "v1",
        "documentation_url": "/docs",
    }
    serialized = response.text.casefold()
    assert not any(
        value in serialized
        for value in ("timestamp", "database_path", "record_count", "profile_count", "hostname")
    )


def test_root_and_versioned_metadata_are_equivalent_and_docs_can_be_hidden(tmp_path: Path) -> None:
    app = create_app(settings(tmp_path / "metadata.db", docs_enabled=False))
    root = get(app, "/")
    versioned = get(app, "/api/v1")
    assert root.json() == versioned.json()
    assert root.json()["documentation_url"] is None


@pytest.mark.parametrize("path", ["/health", "/api/v1/health"])
def test_liveness_is_storage_independent(path: str, tmp_path: Path) -> None:
    database = tmp_path / "health.db"
    app = create_app(settings(database))
    database.unlink()
    database.mkdir()

    response = get(app, path)
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "LifeLenz-AI", "version": "0.1.0"}
    assert UUID(response.headers["X-Request-ID"]).version == 4
    assert "database" not in response.text.casefold()
    assert get(app, "/ready").status_code == 503


@pytest.mark.parametrize("path", ["/ready", "/api/v1/ready"])
def test_readiness_reports_supported_schema_without_details(path: str, tmp_path: Path) -> None:
    app = create_app(settings(tmp_path / "ready.db"))
    response = get(app, path)

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "available", "schema_version": 1}
    serialized = response.text.casefold()
    assert "schema_metadata" not in serialized
    assert str(tmp_path).casefold() not in serialized
    assert "record_count" not in serialized


@pytest.mark.parametrize("version", ["2", "invalid"])
def test_readiness_version_failures_are_generic_and_liveness_survives(
    version: str,
    tmp_path: Path,
) -> None:
    database = tmp_path / "version.db"
    app = create_app(settings(database))
    connection = sqlite3.connect(database)
    try:
        connection.execute(
            "UPDATE schema_metadata SET value = ? WHERE key = ?",
            (version, "schema_version"),
        )
        connection.commit()
    finally:
        connection.close()

    response = get(app, "/ready", headers={"X-Request-ID": "ready-failure"})
    assert response.status_code == 503
    assert response.headers["X-Request-ID"] == "ready-failure"
    assert response.json() == {
        "error": {
            "code": "repository_persistence_error",
            "message": "The persistence service is temporarily unavailable.",
            "field": None,
        },
        "request_id": "ready-failure",
    }
    assert get(app, "/health").status_code == 200


def test_missing_metadata_and_corrupt_database_fail_without_disclosure(tmp_path: Path) -> None:
    for mode in ("missing", "corrupt"):
        database = tmp_path / f"{mode}.db"
        app = create_app(settings(database))
        if mode == "missing":
            connection = sqlite3.connect(database)
            try:
                connection.execute("DELETE FROM schema_metadata")
                connection.commit()
            finally:
                connection.close()
        else:
            database.write_bytes(b"not a sqlite database")

        response = get(app, "/api/v1/ready")
        assert response.status_code == 503
        serialized = response.text.casefold()
        assert "sqlite" not in serialized
        assert "select" not in serialized
        assert str(database).casefold() not in serialized


def test_readiness_does_not_recreate_a_missing_database(tmp_path: Path) -> None:
    database = tmp_path / "removed.db"
    app = create_app(settings(database))
    database.unlink()

    response = get(app, "/ready")
    assert response.status_code == 503
    assert not database.exists()
    assert get(app, "/health").status_code == 200
