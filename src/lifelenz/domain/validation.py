"""Reusable validation helpers for LifeLenz domain values."""

from datetime import datetime
from math import isfinite

from lifelenz.domain.exceptions import InvalidNumericValueError, InvalidTimestampError


def require_timezone_aware_datetime(
    value: datetime,
    *,
    field_name: str = "timestamp",
) -> datetime:
    """Return an aware datetime unchanged or raise ``InvalidTimestampError``.

    A usable timezone must provide a UTC offset. The function never attaches,
    infers, or converts a timezone.
    """
    if not isinstance(value, datetime):
        raise InvalidTimestampError(f"{field_name} must be a datetime; got {value!r}")
    if value.tzinfo is None:
        raise InvalidTimestampError(
            f"{field_name} must be timezone-aware with a usable UTC offset; got {value!r}"
        )
    try:
        utc_offset = value.utcoffset()
    except (TypeError, ValueError, OverflowError) as error:
        raise InvalidTimestampError(
            f"{field_name} must be timezone-aware with a usable UTC offset; got {value!r}"
        ) from error
    if utc_offset is None:
        raise InvalidTimestampError(
            f"{field_name} must be timezone-aware with a usable UTC offset; got {value!r}"
        )
    return value


def require_non_negative(
    value: int | float,
    *,
    field_name: str = "value",
) -> int | float:
    """Return a finite number greater than or equal to zero unchanged.

    Raises:
        InvalidNumericValueError: If the value is bool, non-numeric, non-finite,
            or below zero.
    """
    validated_value = _require_finite_number(value, field_name=field_name)
    if validated_value < 0:
        raise InvalidNumericValueError(
            f"{field_name} must be non-negative; got {validated_value!r}"
        )
    return validated_value


def require_positive(
    value: int | float,
    *,
    field_name: str = "value",
) -> int | float:
    """Return a finite number greater than zero unchanged.

    Raises:
        InvalidNumericValueError: If the value is bool, non-numeric, non-finite,
            or not greater than zero.
    """
    validated_value = _require_finite_number(value, field_name=field_name)
    if validated_value <= 0:
        raise InvalidNumericValueError(f"{field_name} must be positive; got {validated_value!r}")
    return validated_value


def require_in_range(
    value: int | float,
    minimum: int | float,
    maximum: int | float,
    *,
    field_name: str = "value",
) -> int | float:
    """Return a finite number within the inclusive bounds unchanged.

    Raises:
        InvalidNumericValueError: If a value or bound is invalid, the minimum
            exceeds the maximum, or the value is outside the inclusive range.
    """
    validated_value = _require_finite_number(value, field_name=field_name)
    validated_minimum = _require_finite_number(minimum, field_name="minimum bound")
    validated_maximum = _require_finite_number(maximum, field_name="maximum bound")

    if validated_minimum > validated_maximum:
        raise InvalidNumericValueError(
            "minimum bound must not exceed maximum bound; "
            f"got {validated_minimum!r} and {validated_maximum!r}"
        )
    if not validated_minimum <= validated_value <= validated_maximum:
        raise InvalidNumericValueError(
            f"{field_name} must be between {validated_minimum!r} and "
            f"{validated_maximum!r}, inclusive; got {validated_value!r}"
        )
    return validated_value


def _require_finite_number(
    value: int | float,
    *,
    field_name: str,
) -> int | float:
    """Return an int or finite float after rejecting bool explicitly."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidNumericValueError(
            f"{field_name} must be an int or float, excluding bool; got {value!r}"
        )
    if isinstance(value, float) and not isfinite(value):
        raise InvalidNumericValueError(f"{field_name} must be finite; got {value!r}")
    return value
