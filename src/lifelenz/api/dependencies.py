"""Explicit per-application repository and service composition."""

import sqlite3
from dataclasses import dataclass

from fastapi import Request

from lifelenz.api.config import ApiConfigurationError, ApiSettings
from lifelenz.application import (
    GoalService,
    ProfileService,
    WellnessRecordService,
    WellnessSummaryService,
)
from lifelenz.repositories import (
    GoalRepository,
    ProfileRepository,
    RepositoryPersistenceError,
    SQLiteGoalRepository,
    SQLiteProfileRepository,
    SQLiteWellnessRecordRepository,
    WellnessRecordRepository,
)

_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class ApiContainer:
    """Immutable repositories and services owned by one API application."""

    settings: ApiSettings
    profile_repository: ProfileRepository
    goal_repository: GoalRepository
    wellness_record_repository: WellnessRecordRepository
    profile_service: ProfileService
    goal_service: GoalService
    wellness_record_service: WellnessRecordService
    wellness_summary_service: WellnessSummaryService


def build_api_container(settings: ApiSettings) -> ApiContainer:
    """Build fresh SQLite repositories and application services for one app."""
    if type(settings) is not ApiSettings:
        raise ApiConfigurationError("settings must be an ApiSettings instance")
    profile_repository = SQLiteProfileRepository(settings.database_path)
    goal_repository = SQLiteGoalRepository(settings.database_path)
    record_repository = SQLiteWellnessRecordRepository(settings.database_path)
    return ApiContainer(
        settings=settings,
        profile_repository=profile_repository,
        goal_repository=goal_repository,
        wellness_record_repository=record_repository,
        profile_service=ProfileService(profile_repository),
        goal_service=GoalService(profile_repository, goal_repository),
        wellness_record_service=WellnessRecordService(profile_repository, record_repository),
        wellness_summary_service=WellnessSummaryService(profile_repository, record_repository),
    )


def get_api_settings(request: Request) -> ApiSettings:
    """Return validated settings stored on the current application."""
    settings = getattr(request.app.state, "settings", None)
    if type(settings) is not ApiSettings:
        raise ApiConfigurationError("API settings are not configured")
    return settings


def get_api_container(request: Request) -> ApiContainer:
    """Return the immutable dependency container stored on the current app."""
    container = getattr(request.app.state, "container", None)
    if type(container) is not ApiContainer:
        raise ApiConfigurationError("API dependencies are not configured")
    return container


def check_database_readiness(settings: ApiSettings) -> int:
    """Verify the configured SQLite database exposes supported schema metadata."""
    connection: sqlite3.Connection | None = None
    try:
        database_uri = f"{settings.database_path.resolve().as_uri()}?mode=rw"
        connection = sqlite3.connect(database_uri, timeout=5.0, uri=True)
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT value FROM schema_metadata WHERE key = ?",
            ("schema_version",),
        ).fetchone()
        if row is None:
            raise ValueError("schema version metadata is missing")
        version = int(row["value"])
        if version != _SCHEMA_VERSION:
            raise ValueError("schema version is unsupported")
        return version
    except (sqlite3.Error, TypeError, ValueError) as error:
        raise RepositoryPersistenceError(
            "The configured persistence service is not ready"
        ) from error
    finally:
        if connection is not None:
            connection.close()
