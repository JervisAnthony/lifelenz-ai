"""Public application-service API for LifeLenz use cases."""

from lifelenz.application.authenticated_goals import AuthenticatedGoalService
from lifelenz.application.authenticated_profile import AuthenticatedProfileService
from lifelenz.application.authenticated_records import AuthenticatedWellnessRecordService
from lifelenz.application.authenticated_summary import AuthenticatedWellnessSummaryService
from lifelenz.application.authentication import AuthenticationService
from lifelenz.application.exceptions import (
    AccountAlreadyExistsError,
    AccountNotFoundError,
    ApplicationError,
    ApplicationValidationError,
    GoalNotFoundError,
    InactiveAccountError,
    InvalidCredentialsError,
    ProfileAccessDeniedError,
    ProfileAlreadyExistsError,
    ProfileNotConfiguredError,
    ProfileNotFoundError,
    WellnessRecordNotFoundError,
    WellnessSummaryUnavailableError,
)
from lifelenz.application.ownership import ProfileOwnershipService
from lifelenz.application.services import GoalService, ProfileService, WellnessRecordService
from lifelenz.application.summaries import (
    MetricWellnessSummary,
    WellnessSummary,
    WellnessSummaryService,
)

__all__ = [
    "AccountAlreadyExistsError",
    "AccountNotFoundError",
    "ApplicationError",
    "ApplicationValidationError",
    "AuthenticatedGoalService",
    "AuthenticatedProfileService",
    "AuthenticatedWellnessRecordService",
    "AuthenticatedWellnessSummaryService",
    "AuthenticationService",
    "GoalNotFoundError",
    "GoalService",
    "InactiveAccountError",
    "InvalidCredentialsError",
    "MetricWellnessSummary",
    "ProfileAccessDeniedError",
    "ProfileAlreadyExistsError",
    "ProfileNotConfiguredError",
    "ProfileNotFoundError",
    "ProfileOwnershipService",
    "ProfileService",
    "WellnessRecordNotFoundError",
    "WellnessRecordService",
    "WellnessSummary",
    "WellnessSummaryService",
    "WellnessSummaryUnavailableError",
]
