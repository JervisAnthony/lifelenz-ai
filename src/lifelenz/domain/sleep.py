"""Immutable domain types for completed sleep sessions."""

from dataclasses import dataclass
from enum import StrEnum, unique
from math import isclose

from lifelenz.domain.exceptions import (
    DomainValidationError,
    InvalidNumericValueError,
    InvalidTimeRangeError,
)
from lifelenz.domain.primitives import RecordMetadata, TimeRange
from lifelenz.domain.validation import require_non_negative, require_positive

_DURATION_TOLERANCE_MINUTES = 1e-9


@unique
class SleepQuality(StrEnum):
    """A subjective, non-clinical rating of a completed sleep session."""

    VERY_POOR = "very_poor"
    POOR = "poor"
    FAIR = "fair"
    GOOD = "good"
    VERY_GOOD = "very_good"


@dataclass(frozen=True, slots=True)
class SleepStageDurations:
    """Optional, potentially partial sleep-stage totals stored in minutes.

    Values must be finite and non-negative. Missing stages remain zero and are
    never inferred or interpreted as health classifications.

    Raises:
        InvalidNumericValueError: If any stage duration is invalid.
    """

    awake_minutes: int | float = 0.0
    light_minutes: int | float = 0.0
    deep_minutes: int | float = 0.0
    rem_minutes: int | float = 0.0

    def __post_init__(self) -> None:
        """Validate each supplied duration without converting its numeric type."""
        require_non_negative(self.awake_minutes, field_name="awake_minutes")
        require_non_negative(self.light_minutes, field_name="light_minutes")
        require_non_negative(self.deep_minutes, field_name="deep_minutes")
        require_non_negative(self.rem_minutes, field_name="rem_minutes")

    @property
    def total_minutes(self) -> int | float:
        """Return the sum of all supplied awake and asleep stage minutes."""
        return self.awake_minutes + self.light_minutes + self.deep_minutes + self.rem_minutes


@dataclass(frozen=True, slots=True)
class SleepRecord:
    """A validated, completed sleep session with durations stored in minutes.

    ``period`` is the start-inclusive, end-exclusive time spent in bed. Sleep
    and awake totals may leave unclassified time. Optional stage data may be
    partial, but it cannot exceed its corresponding parent duration.

    Raises:
        DomainValidationError: If a supplied object or controlled type is invalid.
        InvalidTimeRangeError: If the time-in-bed period has zero duration.
        InvalidNumericValueError: If a duration, total, or interruption count
            violates a sleep-session invariant.
    """

    metadata: RecordMetadata
    period: TimeRange
    sleep_minutes: int | float
    awake_minutes: int | float
    quality: SleepQuality | None = None
    stages: SleepStageDurations | None = None
    interruption_count: int | None = None

    def __post_init__(self) -> None:
        """Validate the session and all cross-field duration relationships."""
        if not isinstance(self.metadata, RecordMetadata):
            raise DomainValidationError(f"metadata must be a RecordMetadata; got {self.metadata!r}")
        if not isinstance(self.period, TimeRange):
            raise DomainValidationError(f"period must be a TimeRange; got {self.period!r}")
        if self.period.duration.total_seconds() == 0:
            raise InvalidTimeRangeError("period must have a duration greater than zero")

        require_positive(self.sleep_minutes, field_name="sleep_minutes")
        require_non_negative(self.awake_minutes, field_name="awake_minutes")

        if self.sleep_minutes > self.time_in_bed_minutes:
            raise InvalidNumericValueError(
                f"sleep_minutes cannot exceed time in bed; got {self.sleep_minutes!r} "
                f"for {self.time_in_bed_minutes!r} minutes"
            )
        if self.awake_minutes > self.time_in_bed_minutes:
            raise InvalidNumericValueError(
                f"awake_minutes cannot exceed time in bed; got {self.awake_minutes!r} "
                f"for {self.time_in_bed_minutes!r} minutes"
            )

        self._validate_quality()
        self._validate_interruption_count()
        self._validate_stages()

        accounted_minutes = self.sleep_minutes + self.awake_minutes
        if _materially_exceeds(accounted_minutes, self.time_in_bed_minutes):
            raise InvalidNumericValueError(
                "sleep_minutes plus awake_minutes cannot exceed time in bed; "
                f"got {accounted_minutes!r} for {self.time_in_bed_minutes!r} minutes"
            )

    def _validate_quality(self) -> None:
        """Require an existing SleepQuality member when quality is known."""
        if self.quality is not None and not isinstance(self.quality, SleepQuality):
            raise DomainValidationError(
                f"quality must be a SleepQuality or None; got {self.quality!r}"
            )

    def _validate_interruption_count(self) -> None:
        """Require a non-negative integer when interruptions are known."""
        if self.interruption_count is None:
            return
        if isinstance(self.interruption_count, bool) or not isinstance(
            self.interruption_count, int
        ):
            raise InvalidNumericValueError(
                "interruption_count must be a non-negative integer or None; "
                f"got {self.interruption_count!r}"
            )
        if self.interruption_count < 0:
            raise InvalidNumericValueError(
                "interruption_count must be a non-negative integer or None; "
                f"got {self.interruption_count!r}"
            )

    def _validate_stages(self) -> None:
        """Validate optional partial stages against their parent durations."""
        if self.stages is None:
            return
        if not isinstance(self.stages, SleepStageDurations):
            raise DomainValidationError(
                f"stages must be SleepStageDurations or None; got {self.stages!r}"
            )

        staged_sleep_minutes = (
            self.stages.light_minutes + self.stages.deep_minutes + self.stages.rem_minutes
        )
        if _materially_exceeds(staged_sleep_minutes, self.sleep_minutes):
            raise InvalidNumericValueError(
                "sleep stage sleep minutes cannot exceed sleep_minutes; "
                f"got {staged_sleep_minutes!r} for {self.sleep_minutes!r} minutes"
            )
        if self.stages.awake_minutes > self.awake_minutes:
            raise InvalidNumericValueError(
                "stages.awake_minutes cannot exceed awake_minutes; "
                f"got {self.stages.awake_minutes!r} for {self.awake_minutes!r} minutes"
            )
        if _materially_exceeds(self.stages.total_minutes, self.time_in_bed_minutes):
            raise InvalidNumericValueError(
                "total staged minutes cannot exceed time in bed; "
                f"got {self.stages.total_minutes!r} for "
                f"{self.time_in_bed_minutes!r} minutes"
            )

    @property
    def time_in_bed_minutes(self) -> float:
        """Return the complete time-in-bed period in minutes."""
        return self.period.duration_minutes

    @property
    def time_in_bed_hours(self) -> float:
        """Return the complete time-in-bed period in hours without rounding."""
        return self.time_in_bed_minutes / 60

    @property
    def sleep_duration_hours(self) -> float:
        """Return actual sleep duration in hours without rounding."""
        return self.sleep_minutes / 60

    @property
    def awake_duration_hours(self) -> float:
        """Return awake duration in hours without rounding."""
        return self.awake_minutes / 60

    @property
    def sleep_efficiency_percent(self) -> float:
        """Return sleep as a percentage of time in bed without classification."""
        return self.sleep_minutes / self.time_in_bed_minutes * 100


def _materially_exceeds(value: int | float, limit: int | float) -> bool:
    """Return whether value exceeds limit beyond arithmetic noise."""
    return value > limit and not isclose(
        value,
        limit,
        rel_tol=0.0,
        abs_tol=_DURATION_TOLERANCE_MINUTES,
    )
