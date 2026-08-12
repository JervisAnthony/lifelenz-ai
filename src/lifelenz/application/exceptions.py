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


class AccountNotFoundError(ApplicationError):
    """Raised when an internal account lookup cannot find the requested identity."""


class AccountAlreadyExistsError(ApplicationError):
    """Raised when registration would reuse an existing canonical email."""


class InvalidCredentialsError(ApplicationError):
    """Raised for either an unknown email or an incorrect password."""


class InactiveAccountError(ApplicationError):
    """Raised when valid credentials reference a disabled account."""


class ProfileAccessDeniedError(ApplicationError):
    """Raised when the authenticated account does not own a profile."""


class ProfileAlreadyExistsError(ApplicationError):
    """Raised when primary-profile onboarding has already been completed."""


class ProfileNotConfiguredError(ApplicationError):
    """Raised when an authenticated account has no primary wellness profile."""
