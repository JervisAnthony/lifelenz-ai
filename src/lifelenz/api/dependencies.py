"""Explicit per-application repository and service composition."""

import sqlite3
from dataclasses import dataclass
from datetime import timedelta
from typing import Annotated

from fastapi import Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from lifelenz.api.config import ApiConfigurationError, ApiSettings
from lifelenz.application import (
    AccountNotFoundError,
    AuthenticatedGoalService,
    AuthenticatedProfileService,
    AuthenticatedWellnessCsvImportService,
    AuthenticatedWellnessRecordService,
    AuthenticatedWellnessSummaryService,
    AuthenticationService,
    GoalService,
    InactiveAccountError,
    ProfileOwnershipService,
    ProfileService,
    WellnessRecordService,
    WellnessSummaryService,
)
from lifelenz.identity import UserAccount
from lifelenz.repositories import (
    GoalRepository,
    ProfileOwnershipRepository,
    ProfileRepository,
    RepositoryPersistenceError,
    SQLiteGoalRepository,
    SQLiteProfileOwnershipRepository,
    SQLiteProfileRepository,
    SQLiteUserAccountRepository,
    SQLiteWellnessRecordRepository,
    UserAccountRepository,
    WellnessRecordRepository,
)
from lifelenz.security import (
    Argon2PasswordHasher,
    JwtAccessTokenService,
    TokenValidationError,
)

_SCHEMA_VERSION = 2
_BEARER_SCHEME = HTTPBearer(
    auto_error=False,
    scheme_name="BearerAuth",
    description="LifeLenz short-lived bearer access token",
)


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
    user_account_repository: UserAccountRepository
    profile_ownership_repository: ProfileOwnershipRepository
    password_hasher: Argon2PasswordHasher
    access_token_service: JwtAccessTokenService
    authentication_service: AuthenticationService
    profile_ownership_service: ProfileOwnershipService
    authenticated_profile_service: AuthenticatedProfileService
    authenticated_wellness_record_service: AuthenticatedWellnessRecordService
    authenticated_wellness_csv_import_service: AuthenticatedWellnessCsvImportService
    authenticated_goal_service: AuthenticatedGoalService
    authenticated_wellness_summary_service: AuthenticatedWellnessSummaryService


def build_api_container(settings: ApiSettings) -> ApiContainer:
    """Build fresh SQLite repositories and application services for one app."""
    if type(settings) is not ApiSettings:
        raise ApiConfigurationError("settings must be an ApiSettings instance")
    profile_repository = SQLiteProfileRepository(settings.database_path)
    goal_repository = SQLiteGoalRepository(settings.database_path)
    record_repository = SQLiteWellnessRecordRepository(settings.database_path)
    account_repository = SQLiteUserAccountRepository(settings.database_path)
    ownership_repository = SQLiteProfileOwnershipRepository(settings.database_path)
    password_hasher = Argon2PasswordHasher()
    token_service = JwtAccessTokenService(
        secret=settings.jwt_secret,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        access_token_lifetime=timedelta(minutes=settings.access_token_minutes),
    )
    profile_service = ProfileService(profile_repository)
    record_service = WellnessRecordService(profile_repository, record_repository)
    ownership_service = ProfileOwnershipService(ownership_repository)
    authenticated_profile_service = AuthenticatedProfileService(
        profile_service,
        ownership_service,
    )
    authenticated_record_service = AuthenticatedWellnessRecordService(
        authenticated_profile_service,
        record_service,
    )
    goal_service = GoalService(profile_repository, goal_repository)
    summary_service = WellnessSummaryService(profile_repository, record_repository)
    return ApiContainer(
        settings=settings,
        profile_repository=profile_repository,
        goal_repository=goal_repository,
        wellness_record_repository=record_repository,
        profile_service=profile_service,
        goal_service=goal_service,
        wellness_record_service=record_service,
        wellness_summary_service=summary_service,
        user_account_repository=account_repository,
        profile_ownership_repository=ownership_repository,
        password_hasher=password_hasher,
        access_token_service=token_service,
        authentication_service=AuthenticationService(account_repository, password_hasher),
        profile_ownership_service=ownership_service,
        authenticated_profile_service=authenticated_profile_service,
        authenticated_wellness_record_service=authenticated_record_service,
        authenticated_wellness_csv_import_service=AuthenticatedWellnessCsvImportService(
            authenticated_record_service,
        ),
        authenticated_goal_service=AuthenticatedGoalService(
            authenticated_profile_service,
            goal_service,
        ),
        authenticated_wellness_summary_service=AuthenticatedWellnessSummaryService(
            authenticated_profile_service,
            summary_service,
        ),
    )


def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(_BEARER_SCHEME)],
) -> UserAccount:
    """Authenticate a bearer subject against the authoritative active account."""
    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise TokenValidationError("access token is missing or invalid")
    container = get_api_container(request)
    claims = container.access_token_service.decode_token(credentials.credentials)
    try:
        account = container.authentication_service.get_account(claims.subject)
    except AccountNotFoundError as error:
        raise TokenValidationError("access token subject is invalid") from error
    if not account.is_active:
        raise InactiveAccountError("account is inactive")
    return account


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
