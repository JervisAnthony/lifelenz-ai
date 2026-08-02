"""Tests for reusable datetime and numeric validation helpers."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta, timezone, tzinfo

import pytest

from lifelenz.domain.exceptions import InvalidNumericValueError, InvalidTimestampError
from lifelenz.domain.validation import (
    require_in_range,
    require_non_negative,
    require_positive,
    require_timezone_aware_datetime,
)


class MissingOffsetTimezone(tzinfo):
    """Timezone stub that cannot provide a usable UTC offset."""

    def utcoffset(self, value: datetime | None) -> None:
        """Return no offset regardless of the supplied datetime."""
        return None

    def dst(self, value: datetime | None) -> None:
        """Return no daylight-saving offset."""
        return None

    def tzname(self, value: datetime | None) -> str:
        """Return a descriptive timezone name."""
        return "missing-offset"


class InvalidOffsetTimezone(tzinfo):
    """Timezone stub whose offset violates datetime's supported range."""

    def utcoffset(self, value: datetime | None) -> timedelta:
        """Return an invalid offset that datetime will reject."""
        return timedelta(hours=25)

    def dst(self, value: datetime | None) -> None:
        """Return no daylight-saving offset."""
        return None

    def tzname(self, value: datetime | None) -> str:
        """Return a descriptive timezone name."""
        return "invalid-offset"


def test_timezone_validator_returns_utc_datetime_unchanged() -> None:
    """A UTC timestamp passes without conversion or replacement."""
    timestamp = datetime(2026, 8, 2, 12, 30, tzinfo=UTC)

    assert require_timezone_aware_datetime(timestamp) is timestamp


def test_timezone_validator_accepts_fixed_offset_datetime() -> None:
    """A non-UTC fixed offset is also usable timezone information."""
    timestamp = datetime(2026, 8, 2, 12, 30, tzinfo=timezone(timedelta(hours=-4)))

    assert require_timezone_aware_datetime(timestamp, field_name="observed_at") is timestamp


def test_timezone_validator_rejects_naive_datetime_with_field_name() -> None:
    """Naive timestamps fail with the caller's field name in the message."""
    timestamp = datetime(2026, 8, 2, 12, 30)

    with pytest.raises(InvalidTimestampError, match=r"recorded_at.*timezone-aware"):
        require_timezone_aware_datetime(timestamp, field_name="recorded_at")


def test_timezone_validator_rejects_timezone_without_offset() -> None:
    """A tzinfo object alone is insufficient when its UTC offset is unusable."""
    timestamp = datetime(2026, 8, 2, 12, 30, tzinfo=MissingOffsetTimezone())

    with pytest.raises(InvalidTimestampError, match="usable UTC offset"):
        require_timezone_aware_datetime(timestamp)


def test_timezone_validator_wraps_malformed_offset_as_domain_error() -> None:
    """Invalid UTC offset implementations do not leak datetime exceptions."""
    timestamp = datetime(2026, 8, 2, 12, 30, tzinfo=InvalidOffsetTimezone())

    with pytest.raises(InvalidTimestampError, match="usable UTC offset"):
        require_timezone_aware_datetime(timestamp, field_name="observed_at")


def test_timezone_validator_rejects_non_datetime_value() -> None:
    """Malformed timestamp inputs produce the domain-specific exception."""
    with pytest.raises(InvalidTimestampError, match=r"observed_at.*datetime.*None"):
        require_timezone_aware_datetime(None, field_name="observed_at")  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [0, 3, 2.5])
def test_require_non_negative_accepts_zero_and_positive_values(value: int | float) -> None:
    """Non-negative integers and floats are returned without conversion."""
    result = require_non_negative(value, field_name="amount")

    assert result is value


@pytest.mark.parametrize("value", [1, 3.5])
def test_require_positive_accepts_values_above_zero(value: int | float) -> None:
    """Positive integers and floats are returned without conversion."""
    result = require_positive(value, field_name="amount")

    assert result is value


@pytest.mark.parametrize("value", [-1, -0.01])
def test_require_non_negative_rejects_values_below_zero(value: int | float) -> None:
    """Negative values fail with their field and invalid value visible."""
    with pytest.raises(InvalidNumericValueError, match=rf"amount.*{value!r}"):
        require_non_negative(value, field_name="amount")


@pytest.mark.parametrize("value", [0, -1, -0.01])
def test_require_positive_rejects_zero_and_negative_values(value: int | float) -> None:
    """The positive contract uses an exclusive zero boundary."""
    with pytest.raises(InvalidNumericValueError, match=rf"amount.*{value!r}"):
        require_positive(value, field_name="amount")


@pytest.mark.parametrize("value", [-2, 5, 8.5, 10])
def test_require_in_range_accepts_values_at_and_within_inclusive_bounds(
    value: int | float,
) -> None:
    """Both range boundaries and intermediate numeric types are accepted."""
    result = require_in_range(value, -2, 10, field_name="score")

    assert result is value


@pytest.mark.parametrize("value", [-2.01, 10.01])
def test_require_in_range_rejects_values_outside_bounds(value: float) -> None:
    """Values immediately below or above the inclusive range fail."""
    with pytest.raises(InvalidNumericValueError, match=rf"score.*inclusive.*{value!r}"):
        require_in_range(value, -2, 10, field_name="score")


def test_require_in_range_rejects_inverted_bounds() -> None:
    """An invalid range definition is reported explicitly."""
    with pytest.raises(InvalidNumericValueError, match=r"minimum bound.*maximum bound"):
        require_in_range(5, 10, 0)


@pytest.mark.parametrize(
    "validator",
    [
        require_non_negative,
        require_positive,
    ],
)
def test_single_value_numeric_helpers_reject_booleans(
    validator: Callable[..., int | float],
) -> None:
    """Boolean values never pass as integers."""
    with pytest.raises(InvalidNumericValueError, match=r"flag.*excluding bool.*True"):
        validator(True, field_name="flag")


def test_range_helper_rejects_boolean_value_and_bounds() -> None:
    """The range value and both bounds apply the same bool exclusion."""
    with pytest.raises(InvalidNumericValueError, match=r"flag.*excluding bool"):
        require_in_range(True, 0, 1, field_name="flag")
    with pytest.raises(InvalidNumericValueError, match=r"minimum bound.*excluding bool"):
        require_in_range(1, False, 2)
    with pytest.raises(InvalidNumericValueError, match=r"maximum bound.*excluding bool"):
        require_in_range(1, 0, True)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_numeric_helpers_reject_non_finite_floats(value: float) -> None:
    """NaN and infinite values cannot satisfy domain numeric constraints."""
    with pytest.raises(InvalidNumericValueError, match=r"measurement.*finite"):
        require_non_negative(value, field_name="measurement")
