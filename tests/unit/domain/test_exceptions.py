"""Tests for shared LifeLenz domain validation exceptions."""

import pytest

from lifelenz.domain.exceptions import (
    DomainValidationError,
    InvalidIdentifierError,
    InvalidNumericValueError,
    InvalidTimeRangeError,
    InvalidTimestampError,
)

SPECIFIC_EXCEPTIONS = (
    InvalidIdentifierError,
    InvalidNumericValueError,
    InvalidTimestampError,
    InvalidTimeRangeError,
)


def test_specific_exceptions_inherit_from_domain_validation_error() -> None:
    """All focused validation failures share one catchable base type."""
    assert all(
        issubclass(exception_type, DomainValidationError) for exception_type in SPECIFIC_EXCEPTIONS
    )
    assert issubclass(DomainValidationError, ValueError)


@pytest.mark.parametrize("exception_type", SPECIFIC_EXCEPTIONS)
def test_specific_exceptions_preserve_human_readable_messages(
    exception_type: type[DomainValidationError],
) -> None:
    """Specific exceptions retain the context supplied at the validation site."""
    error = exception_type("field has an invalid value")

    assert str(error) == "field has an invalid value"


@pytest.mark.parametrize("exception_type", SPECIFIC_EXCEPTIONS)
def test_specific_exceptions_can_be_caught_through_base_type(
    exception_type: type[DomainValidationError],
) -> None:
    """Callers may handle all domain validation failures consistently."""
    with pytest.raises(DomainValidationError, match="invalid domain value"):
        raise exception_type("invalid domain value")
