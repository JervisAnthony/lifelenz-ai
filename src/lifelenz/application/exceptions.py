"""Framework-independent exceptions raised by LifeLenz application services."""


class ApplicationError(Exception):
    """Base exception for expected application-service failures."""


class ApplicationValidationError(ApplicationError):
    """Raised when a service receives an invalid argument or dependency."""


class ProfileNotFoundError(ApplicationError):
    """Raised when a valid profile identifier does not exist."""


class GoalNotFoundError(ApplicationError):
    """Raised when a valid goal identifier does not exist."""


class WellnessRecordNotFoundError(ApplicationError):
    """Raised when a valid profile-and-record ownership pair does not exist."""


class WellnessSummaryUnavailableError(ApplicationError):
    """Raised when an existing profile has no extractable summary observations."""
