"""Tests for explicit API repository and service composition."""

import sqlite3
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
from fastapi import FastAPI, Request

from lifelenz.api import ApiConfigurationError, ApiContainer, ApiSettings
from lifelenz.api.dependencies import (
    build_api_container,
    get_api_container,
    get_api_settings,
)
from lifelenz.domain import ProfileId, WellnessProfile
from lifelenz.repositories import RepositoryPersistenceError

TEST_SECRET = "unit-only-secret-material-at-least-32-bytes"


def settings(path: Path) -> ApiSettings:
    return ApiSettings("LifeLenz-AI", "0.1.0", "test", path, TEST_SECRET)


def request_for(app: FastAPI) -> Request:
    return Request({"type": "http", "app": app, "headers": []})


def test_container_wires_all_repositories_services_and_one_schema(tmp_path: Path) -> None:
    container = build_api_container(settings(tmp_path / "api.db"))

    assert isinstance(container, ApiContainer)
    for repository, methods in (
        (container.profile_repository, ("save", "get", "exists", "list_all", "remove")),
        (
            container.goal_repository,
            ("save", "get", "exists", "list_for_profile", "list_all", "remove"),
        ),
        (
            container.wellness_record_repository,
            (
                "save",
                "get",
                "exists",
                "list_for_profile",
                "list_in_time_range",
                "list_by_type",
                "list_by_type_in_time_range",
                "remove",
            ),
        ),
    ):
        assert all(callable(getattr(repository, method, None)) for method in methods)
    assert container.profile_service is not None
    assert container.goal_service is not None
    assert container.wellness_record_service is not None
    assert container.wellness_summary_service is not None
    connection = sqlite3.connect(tmp_path / "api.db")
    try:
        assert {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        } >= {"wellness_profiles", "wellness_goals", "wellness_records"}
    finally:
        connection.close()


def test_container_is_frozen_slotted_and_independent(tmp_path: Path) -> None:
    configured = settings(tmp_path / "shared.db")
    first = build_api_container(configured)
    second = build_api_container(configured)

    assert not hasattr(first, "__dict__")
    assert first.profile_repository is not second.profile_repository
    assert first.profile_service is not second.profile_service
    with pytest.raises(FrozenInstanceError):
        first.settings = configured  # type: ignore[misc]


def test_independent_builds_share_only_configured_durable_data(tmp_path: Path) -> None:
    profile = WellnessProfile(ProfileId("40000000-0000-4000-8000-000000000001"), "UTC")
    first = build_api_container(settings(tmp_path / "shared.db"))
    first.profile_repository.save(profile)
    second = build_api_container(settings(tmp_path / "shared.db"))
    isolated = build_api_container(settings(tmp_path / "isolated.db"))

    assert second.profile_repository.get(profile.profile_id) == profile
    assert isolated.profile_repository.list_all() == ()


def test_builder_does_not_create_missing_parent(tmp_path: Path) -> None:
    parent = tmp_path / "missing"
    with pytest.raises(RepositoryPersistenceError):
        build_api_container(settings(parent / "api.db"))
    assert not parent.exists()


def test_builder_rejects_invalid_settings() -> None:
    with pytest.raises(ApiConfigurationError):
        build_api_container(None)  # type: ignore[arg-type]


def test_request_dependencies_require_explicit_app_state(tmp_path: Path) -> None:
    app = FastAPI()
    request = request_for(app)
    with pytest.raises(ApiConfigurationError):
        get_api_settings(request)
    with pytest.raises(ApiConfigurationError):
        get_api_container(request)

    configured = settings(tmp_path / "api.db")
    container = build_api_container(configured)
    app.state.settings = configured
    app.state.container = container
    assert get_api_settings(request) is configured
    assert get_api_container(request) is container
