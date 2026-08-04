"""Immutable values for descriptive personal baseline analytics."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from math import isfinite

from lifelenz.analytics.exceptions import AnalyticsValidationError
from lifelenz.domain import (
    MeasurementUnit,
    MetricIdentifier,
    ProfileId,
    RecordId,
    TimeRange,
)
from lifelenz.domain.taxonomy import DEFAULT_UNIT_BY_METRIC


def _require_type(value: object, expected_type: type, *, field_name: str) -> None:
    """Require an existing typed value without coercion."""
    if not isinstance(value, expected_type):
        raise AnalyticsValidationError(
            f"{field_name} must be a {expected_type.__name__}; got {value!r}"
        )


def _require_finite_number(value: object, *, field_name: str) -> int | float:
    """Return a plain finite integer or float without changing its value."""
    if type(value) not in (int, float):
        raise AnalyticsValidationError(
            f"{field_name} must be a plain int or float, excluding bool; got {value!r}"
        )
    if type(value) is float and not isfinite(value):
        raise AnalyticsValidationError(f"{field_name} must be finite; got {value!r}")
    return value


def _require_finite_float(value: object, *, field_name: str) -> float:
    """Return a finite float after strict type validation."""
    if type(value) is not float:
        raise AnalyticsValidationError(f"{field_name} must be a float; got {value!r}")
    if not isfinite(value):
        raise AnalyticsValidationError(f"{field_name} must be finite; got {value!r}")
    return value


def _require_aware_datetime(value: object, *, field_name: str) -> datetime:
    """Return an exact aware datetime without timezone conversion."""
    if type(value) is not datetime:
        raise AnalyticsValidationError(
            f"{field_name} must be a timezone-aware datetime; got {value!r}"
        )
    if value.tzinfo is None:
        raise AnalyticsValidationError(
            f"{field_name} must be a timezone-aware datetime; got {value!r}"
        )
    try:
        offset = value.utcoffset()
    except (TypeError, ValueError, OverflowError) as error:
        raise AnalyticsValidationError(
            f"{field_name} must have a usable UTC offset; got {value!r}"
        ) from error
    if offset is None:
        raise AnalyticsValidationError(f"{field_name} must have a usable UTC offset; got {value!r}")
    return value


def _require_canonical_unit(
    metric: MetricIdentifier,
    unit: object,
) -> MeasurementUnit:
    """Require the taxonomy's canonical unit for ``metric``."""
    _require_type(unit, MeasurementUnit, field_name="unit")
    canonical_unit = DEFAULT_UNIT_BY_METRIC[metric]
    if unit is not canonical_unit:
        raise AnalyticsValidationError(
            f"unit must be {canonical_unit.value!r} for metric {metric.value!r}; got {unit!r}"
        )
    return unit


@dataclass(frozen=True, slots=True)
class MetricSample:
    """One canonical numeric observation traced to an immutable source record.

    The metadata timestamp is preserved without conversion. The sample carries
    no health interpretation, target, trend, or population comparison.
    """

    profile_id: ProfileId
    metric: MetricIdentifier
    value: int | float
    unit: MeasurementUnit
    observed_at: datetime
    source_record_id: RecordId

    def __post_init__(self) -> None:
        """Validate exact identifiers, canonical units, value, and timestamp."""
        _require_type(self.profile_id, ProfileId, field_name="profile_id")
        _require_type(self.metric, MetricIdentifier, field_name="metric")
        _require_finite_number(self.value, field_name="value")
        _require_canonical_unit(self.metric, self.unit)
        _require_aware_datetime(self.observed_at, field_name="observed_at")
        _require_type(self.source_record_id, RecordId, field_name="source_record_id")


@dataclass(frozen=True, slots=True)
class PersonalBaseline:
    """A descriptive summary of one profile's matching canonical observations.

    Statistics use population standard deviation and retain an optional requested
    filtering range. They do not express health status, trends, recommendations,
    correlations, or predictions.
    """

    profile_id: ProfileId
    metric: MetricIdentifier
    unit: MeasurementUnit
    sample_count: int
    mean: float
    median: float
    minimum: int | float
    maximum: int | float
    population_standard_deviation: float
    first_observed_at: datetime
    last_observed_at: datetime
    time_range: TimeRange | None

    def __post_init__(self) -> None:
        """Validate direct type, canonical-unit, and mathematical consistency."""
        _require_type(self.profile_id, ProfileId, field_name="profile_id")
        _require_type(self.metric, MetricIdentifier, field_name="metric")
        _require_canonical_unit(self.metric, self.unit)
        if type(self.sample_count) is not int or self.sample_count < 1:
            raise AnalyticsValidationError(
                f"sample_count must be a positive plain integer; got {self.sample_count!r}"
            )

        mean = _require_finite_float(self.mean, field_name="mean")
        median = _require_finite_float(self.median, field_name="median")
        minimum = _require_finite_number(self.minimum, field_name="minimum")
        maximum = _require_finite_number(self.maximum, field_name="maximum")
        standard_deviation = _require_finite_float(
            self.population_standard_deviation,
            field_name="population_standard_deviation",
        )
        if minimum > maximum:
            raise AnalyticsValidationError(
                f"minimum must not exceed maximum; got {minimum!r} and {maximum!r}"
            )
        if not minimum <= mean <= maximum:
            raise AnalyticsValidationError(
                f"mean must be between minimum and maximum; got {mean!r}"
            )
        if not minimum <= median <= maximum:
            raise AnalyticsValidationError(
                f"median must be between minimum and maximum; got {median!r}"
            )
        if standard_deviation < 0:
            raise AnalyticsValidationError(
                f"population_standard_deviation must be non-negative; got {standard_deviation!r}"
            )
        if self.sample_count == 1 and standard_deviation != 0.0:
            raise AnalyticsValidationError(
                "population_standard_deviation must be 0.0 for one sample; "
                f"got {standard_deviation!r}"
            )

        first = _require_aware_datetime(self.first_observed_at, field_name="first_observed_at")
        last = _require_aware_datetime(self.last_observed_at, field_name="last_observed_at")
        if first > last:
            raise AnalyticsValidationError(
                f"first_observed_at must not follow last_observed_at; got {first!r} and {last!r}"
            )
        if self.sample_count == 1 and first != last:
            raise AnalyticsValidationError(
                "first_observed_at and last_observed_at must match for one sample"
            )
        if self.time_range is not None and not isinstance(self.time_range, TimeRange):
            raise AnalyticsValidationError(
                f"time_range must be a TimeRange or None; got {self.time_range!r}"
            )

    @property
    def has_multiple_samples(self) -> bool:
        """Return whether the descriptive baseline contains multiple samples."""
        return self.sample_count > 1

    @property
    def observation_span(self) -> timedelta:
        """Return the exact elapsed duration between first and last observations."""
        return self.last_observed_at - self.first_observed_at
