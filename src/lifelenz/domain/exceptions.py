"""Exceptions raised when LifeLenz domain values violate their invariants."""


class DomainValidationError(ValueError):
    """Base exception for invalid LifeLenz domain values."""


class InvalidIdentifierError(DomainValidationError):
    """Raised when a domain identifier is empty or malformed."""


class InvalidTimestampError(DomainValidationError):
    """Raised when a required timestamp is invalid or timezone-naive."""


class InvalidTimeRangeError(DomainValidationError):
    """Raised when a time range has invalid or incorrectly ordered bounds."""


class InvalidNumericValueError(DomainValidationError):
    """Raised when a numeric value violates a domain constraint."""
